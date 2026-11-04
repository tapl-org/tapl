# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: the shape a translation to SSA reads.

An ingot is a namespace: a struct `{lᵢ = Eᵢ}` whose every field is an entry or a
namespace again. A struct with a `type` field is an entry; any other struct is a
namespace. An entry has a `type`, at most one of `body` (a definition), `init` (a global
variable) or `value` (a constant), and an optional `link`, the symbol's name for the
linker; an entry with only `type` and `link` is a declaration, and one with only `type`
is a hole, which is rejected. Anything else left in a namespace is rejected too.

Each symbol is named by its path, its labels from the top (`('math', 'gcd')`). A
definition's body is `λg. λp. R` in ANF. `read_ingot` checks the grammar
(`anf.region_error`), then every variable's kind: `g.l₁ ⋯ lₙ` is a path through the
namespaces to a symbol and `g []` only heads a region; `p.l` names a parameter; `r.l` names a block of the region `r` and
only heads a jump, with one operand per parameter; a value has no fields.

It gives the body as regions and blocks, every variable resolved (`Use` of a `Var`, `Arg`,
`Address`, data) and every bound name made distinct: a repeated name takes the
smallest free number (`c`, `c1`).

`ingot_of` runs the whole way from a parsed program: resolve, normalize,
reject a stuck normal form, and read the ingot. `ingots_of` first separates a program with
two layers, and gives each layer's ingot.
"""

from dataclasses import dataclass, field

from oymo.core import syntax
from oymo.oymomo import anf, layers, meta, printer, reduction, strategy, terms
from oymo.oymomo.meta import NO_TAG, Tag


class IngotError(Exception):
    def __init__(self, message: str, tag: Tag) -> None:
        super().__init__(message)
        self.message = message
        self.tag = tag


# Operands, resolved.


@dataclass(eq=False)
class Var:
    """A value: bound by a `let` or a block's `λ`. `name` is unique in its definition."""

    name: str
    tag: Tag = field(default=NO_TAG, compare=False)


@dataclass(eq=False)
class Use:
    """A value used as an operand, where it is used."""

    var: Var
    tag: Tag = NO_TAG


@dataclass
class Arg:
    """`p.l`: the argument for the parameter `l`."""

    label: str
    tag: Tag = field(default=NO_TAG, compare=False)


@dataclass
class Address:
    """`g.l₁ ⋯ lₙ` as an operand: the address of the symbol at the path `l₁ ⋯ lₙ`."""

    path: tuple[str, ...]
    tag: Tag = field(default=NO_TAG, compare=False)


# A data operand stays the term it is (a byte array or a struct of data), so an opcode
# reads its type fields as terms.
type Operand = Use | Arg | Address | syntax.Term


@dataclass(eq=False)
class Instruction:
    """`let result = O {lᵢ = Qᵢ}`: an opcode call (`opcode`) or a call (`callee`, the
    function's path)."""

    result: Var
    opcode: str | None
    callee: tuple[str, ...] | None
    fields: list[tuple[str, Operand]]
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Jump:
    target: 'Block'
    operands: list[Operand]
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Return:
    value: Operand
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Branch:
    """`{Jᵢ} P`: arm `i` when the condition is `i`, the last arm otherwise."""

    arms: list[Jump]
    condition: Use | Arg
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Block:
    """A field of a region. `name` is `r.l`, or `r.0` for an unlabeled field 0."""

    name: str
    label: str
    arity: int
    params: list[Var] = field(default_factory=list)
    lets: list[Instruction] = field(default_factory=list)
    terminal: 'Terminal | None' = None
    jumped: bool = False
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Region:
    """`g [] (λr. {lᵢ = Kᵢ})`; `blocks[0]` is field 0."""

    binder: str
    blocks: list[Block]
    tag: Tag = NO_TAG


type Terminal = Return | Jump | Branch | Region


@dataclass(eq=False)
class FunctionType:
    """`{'function', {xᵢ = tᵢ}, t}`."""

    params: list[tuple[str, syntax.Term]]
    result: syntax.Term


class _Named:
    """A symbol's `path` (its labels from the top) and `link` (its linker name, or None
    for an internal symbol)."""

    path: tuple[str, ...]
    link: str | None

    @property
    def name(self) -> str:
        """The path, dotted: how messages name the symbol."""
        return '.'.join(self.path)


@dataclass(eq=False)
class Definition(_Named):
    path: tuple[str, ...]
    type: FunctionType
    args: str
    region: Region
    link: str | None = None
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Declaration(_Named):
    """An entry with a `type` and a `link`: a function, or a variable, of another ingot."""

    path: tuple[str, ...]
    type: FunctionType | syntax.Term
    link: str
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Constant(_Named):
    path: tuple[str, ...]
    type: syntax.Term
    value: syntax.Term
    link: str | None = None
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Global(_Named):
    path: tuple[str, ...]
    type: syntax.Term
    init: syntax.Term
    link: str | None = None
    tag: Tag = NO_TAG


type Symbol = Definition | Declaration | Constant | Global


@dataclass(eq=False)
class Ingot:
    """Every symbol of the namespaces, flat, in source order (a namespace's entries where
    the namespace is)."""

    symbols: list[Symbol]

    def lookup(self, path: tuple[str, ...]) -> Symbol | None:
        return next((s for s in self.symbols if s.path == path), None)


def function_type(symbol: Symbol | None) -> FunctionType | None:
    """The function type of a definition or a declared function, else None."""
    if isinstance(symbol, Definition | Declaration) and isinstance(symbol.type, FunctionType):
        return symbol.type
    return None


def ingot_of(term: syntax.Term, max_steps: int = strategy.MAX_STEPS) -> Ingot:
    """The ingot a parsed program reduces to. Raises `ReductionError` or `IngotError`."""
    normal = strategy.normalize(reduction.resolve(term), max_steps)
    if (stuck := reduction.stuck_part(normal)) is not None:
        raise IngotError('The program is stuck here: no rule can ever reduce this part.', _tag(stuck))
    return read_ingot(normal)


def ingots_of(written: syntax.Term, max_steps: int = strategy.MAX_STEPS) -> list[Ingot]:
    """The ingots of a written program: `[low, high]` for two layers, each reduced on its own;
    `[ingot]` for one. Raises `ReductionError` or `IngotError`."""
    separated = layers.separate(written)
    return [ingot_of(layer, max_steps) for layer in (separated or (written,))]


def _tag(term):
    return term.tag


def _fields(struct):
    return {f.label: f.value for f in struct.fields}


def read_ingot(term: syntax.Term) -> Ingot:
    """`term`, a resolved normal form, read as an ingot."""
    if not isinstance(term, terms.Struct):
        raise IngotError('Not an ingot: an ingot is a namespace, a struct of entries and namespaces.', _tag(term))
    if 'type' in _fields(term):
        raise IngotError(
            'Not an ingot: a struct with a type is an entry; an ingot is a namespace of entries and namespaces.',
            _tag(term),
        )
    ingot = Ingot([])
    bodies = []
    _namespace(term, (), ingot, bodies)
    for symbol, body in bodies:
        symbol.region, symbol.args = _Body(ingot, symbol).read(body)
    return ingot


def _namespace(term, path, ingot, bodies):
    """Adds the entries of the namespace `term` at `path`, nested ones included, in order."""
    for f in term.fields:
        if not f.label:
            raise IngotError(
                "A field of a namespace needs a label: its symbol's or namespace's name.",
                meta.placed(f.tag, f.value.tag),
            )
        here = (*path, f.label)
        if not isinstance(f.value, terms.Struct):
            raise IngotError(
                f'{".".join(here)!r} is a reduce-time value left in the ingot: '
                'a namespace holds only entries and namespaces.',
                meta.placed(f.tag, f.value.tag),
            )
        if 'type' not in _fields(f.value):
            _namespace(f.value, here, ingot, bodies)
            continue
        symbol, body = _entry(here, f.value)
        ingot.symbols.append(symbol)
        if body is not None:
            bodies.append((symbol, body))


def _show(term):
    return printer.show(term)


_KINDS = ('body', 'init', 'value')
_ENTRY_FIELDS = ('type', *_KINDS, 'link')


def _entry(path, term):
    """The symbol of the entry `term` at `path`, and the body to read later, if any."""
    name = '.'.join(path)
    parts = _fields(term)
    for label in parts:
        if label not in _ENTRY_FIELDS:
            raise IngotError(
                f'Entry {name!r} has an unknown field {label!r}; it may have {", ".join(_ENTRY_FIELDS)}.', _tag(term)
            )
    kinds = [label for label in _KINDS if label in parts]
    if len(kinds) > 1:
        raise IngotError(
            f'Entry {name!r} has {kinds[0]} and {kinds[1]}; it may have at most one of {list(_KINDS)}.', _tag(term)
        )
    link = _link(parts['link']) if 'link' in parts else None
    type_term = _data(parts['type'], 'type')
    fn = _function_type(type_term)
    match kinds:
        case ['body']:
            if fn is None:
                raise IngotError(
                    f"Entry {name!r} has a body, so its type must be {{'function', {{x = t, ...}}, t}}.",
                    _tag(type_term),
                )
            return Definition(path, fn, '', Region('', []), link, _tag(term)), parts['body']
        case ['init']:
            return Global(path, type_term, _data(parts['init'], 'init'), link, _tag(term)), None
        case ['value']:
            return Constant(path, type_term, _data(parts['value'], 'value'), link, _tag(term)), None
    if link is None:
        raise IngotError(f'{name!r} is a hole: give it a body or a link.', _tag(term))
    return Declaration(path, fn if fn is not None else type_term, link, _tag(term)), None


def _link(term):
    """A `link`: the symbol's name for the linker, a nonempty text byte array."""
    text = term.as_str if isinstance(term, terms.ByteArray) else None
    if not text:
        raise IngotError("A link is the symbol's name for the linker: a nonempty text byte array.", _tag(term))
    return text


def _data(term, what):
    if not reduction.is_data(term):
        raise IngotError(f'A {what} must be data: byte arrays and structs of them.', _tag(term))
    return term


def _function_type(term):
    """`{'function', params, result}` read as a `FunctionType`, or None for another type."""
    if not isinstance(term, terms.Struct) or not term.fields:
        return None
    tag = term.fields[0].value
    if not isinstance(tag, terms.ByteArray) or tag.as_str != 'function':
        return None
    params = term.fields[1].value if len(term.fields) == 3 else None  # noqa: PLR2004
    if not isinstance(params, terms.Struct) or any(not f.label for f in params.fields):
        raise IngotError(
            "A function type is {'function', {x = t, ...}, t}: labeled parameters, then the result.", _tag(term)
        )
    return FunctionType([(f.label, f.value) for f in params.fields], term.fields[2].value)


# What a variable is, innermost binder last.
@dataclass
class _Binder:
    kind: str  # 'module', 'arguments', 'region' or 'value'
    region: Region | None = None
    value: Var | None = None


def _path(term):
    """`(root index, labels)` of a path."""
    labels = []
    while isinstance(term, terms.Project):
        labels.append(term.label)
        term = term.struct
    return term.index, labels[::-1]


class _Body:
    """Reads one definition's body `λg. λp. R`."""

    def __init__(self, ingot: Ingot, definition: Definition) -> None:
        self.ingot = ingot
        self.definition = definition
        self.names: set[str] = set()
        self.env: list[_Binder] = []

    def fresh(self, name):
        """`name`, or with the smallest number that makes it new in this definition."""
        name = name or 'x'
        if name in self.names:
            name = next(f'{name}{n}' for n in range(1, len(self.names) + 2) if f'{name}{n}' not in self.names)
        self.names.add(name)
        return name

    def read(self, body):
        name = self.definition.name
        if not isinstance(body, terms.Lambda) or not isinstance(body.body, terms.Lambda):
            raise IngotError(f'The body of {name!r} must be λg. λp. g [] (λr. {{blocks}}).', _tag(body))
        region = body.body.body
        if anf.region_parts(region) is None:
            raise IngotError(f'The body of {name!r} must be λg. λp. g [] (λr. {{blocks}}).', _tag(region))
        if (error := anf.region_error(region)) is not None:
            raise IngotError(f'{name!r} is not in ANF: {error.message}', error.tag)
        self.fresh(body.param_name)
        args = self.fresh(body.body.param_name)
        self.env = [_Binder('module'), _Binder('arguments')]
        return self.region(region), args

    def binder(self, term):
        index, labels = _path(term)
        return self.env[-1 - index], labels

    # Regions and blocks

    def region(self, term):
        head, blocks_lambda = anf.region_parts(term)
        if self.binder(head)[0].kind != 'module':
            raise IngotError('Only the unit runs a region: g [] (λr. {...}).', _tag(head))
        binder = self.fresh(blocks_lambda.param_name)
        region = Region(binder, [], _tag(term))
        for i, f in enumerate(blocks_lambda.body.fields):
            if i > 0 and not f.label:
                raise IngotError(
                    'A block after field 0 needs a label, so a jump can name it.', meta.placed(f.tag, f.value.tag)
                )
            arity, block = 0, f.value
            while isinstance(block, terms.Lambda):
                arity, block = arity + 1, block.body
            label = f.label or '0'
            region.blocks.append(Block(f'{binder}.{label}', f.label, arity, tag=meta.placed(f.tag, f.value.tag)))
        self.env.append(_Binder('region', region=region))
        for block, f in zip(region.blocks, blocks_lambda.body.fields, strict=True):
            self.block(block, f.value)
        self.env.pop()
        return region

    def block(self, block, term):
        depth = len(self.env)
        while isinstance(term, terms.Lambda):
            var = Var(self.fresh(term.param_name), _tag(term))
            block.params.append(var)
            self.env.append(_Binder('value', value=var))
            term = term.body
        while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
            instruction = self.instruction(term.argument)
            instruction.result = Var(self.fresh(term.function.param_name), _tag(term.function))
            block.lets.append(instruction)
            self.env.append(_Binder('value', value=instruction.result))
            term = term.function.body
        block.terminal = self.terminal(term)
        del self.env[depth:]

    # Lets

    def instruction(self, term):
        operator, struct = term.function, term.argument
        if isinstance(operator, terms.ByteArray):
            fields = [(f.label, self.operand(f.value)) for f in struct.fields]
            return Instruction(Var(''), operator.as_str or '', None, fields, _tag(term))
        binder, labels = self.binder(operator)
        symbol = self.ingot.lookup(tuple(labels)) if binder.kind == 'module' else None
        fn = function_type(symbol)
        if fn is None:
            raise IngotError(
                'An instruction calls a function, g.l₁ ⋯ lₙ {...}, a path to a function of the ingot.', _tag(operator)
            )
        names = [name for name, _ in fn.params]
        given = [f.label for f in struct.fields]
        if given != names:
            raise IngotError(
                f'The call to {symbol.name!r} must give {names}, in order; it gives {given}.', _tag(struct)
            )
        fields = [(f.label, self.operand(f.value)) for f in struct.fields]
        return Instruction(Var(''), None, symbol.path, fields, _tag(term))

    # Operands

    def operand(self, term):
        if reduction.is_data(term):
            return term
        binder, labels = self.binder(term)
        tag = _tag(term)
        match binder.kind:
            case 'module':
                if self.ingot.lookup(tuple(labels)) is None:
                    raise IngotError(
                        'g names the symbols: an operand through g is g.l₁ ⋯ lₙ, a path to a symbol of the ingot.',
                        tag,
                    )
                return Address(tuple(labels), tag)
            case 'arguments':
                names = [name for name, _ in self.definition.type.params]
                if not labels:
                    raise IngotError(f'p is never used whole: read an argument as p.l, l one of {names}.', tag)
                if labels[0] not in names:
                    raise IngotError(f'{self.definition.name!r} has no parameter {labels[0]!r}; it has {names}.', tag)
                if len(labels) > 1:
                    raise IngotError(
                        "An argument has no fields: read a field of a struct value with 'extractvalue'.", tag
                    )
                return Arg(labels[0], tag)
            case 'region':
                raise IngotError('r.l is a block: it only heads a jump.', tag)
        if labels:
            raise IngotError("A value has no fields: read a field of a struct value with 'extractvalue'.", tag)
        return Use(binder.value, tag)

    def condition(self, term):
        operand = self.operand(term)
        if not isinstance(operand, Use | Arg):
            raise IngotError('A branch condition is a value or an argument p.l.', _tag(term))
        return operand

    # Terminals

    def terminal(self, term):
        if anf.region_parts(term) is not None:
            return self.region(term)
        if isinstance(term, terms.Apply) and isinstance(term.function, terms.Struct):
            arms = [self.jump(f.value, arm=True) for f in term.function.fields]
            return Branch(arms, self.condition(term.argument), _tag(term))
        if reduction.is_data(term):
            return Return(term, _tag(term))
        head, operands = anf.jump_parts(term)
        kind = self.binder(head)[0].kind
        if kind == 'region':
            return self.jump(term, arm=False)
        if operands:
            if kind == 'module':
                raise IngotError(anf.TAIL_CALL, _tag(term))
            raise IngotError('Only a block r.l is applied at the end of a block.', _tag(term))
        return Return(self.operand(term), _tag(term))

    def jump(self, term, *, arm):
        head, operands = anf.jump_parts(term)
        binder, labels = self.binder(head)
        if binder.kind != 'region':
            raise IngotError(
                'An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ, r a region.'
                if arm
                else 'A jump goes to a block r.l of a region.',
                _tag(head),
            )
        region = binder.region
        blocks = {block.label: block for block in region.blocks if block.label}
        if len(labels) != 1 or labels[0] not in blocks:
            raise IngotError(f'A jump names a block of {region.binder!r}: one of {list(blocks)}.', _tag(head))
        target = blocks[labels[0]]
        if len(operands) != target.arity:
            raise IngotError(
                f'{target.name} takes {target.arity} operands, one per parameter; the jump gives {len(operands)}.',
                _tag(term),
            )
        target.jumped = True
        return Jump(target, [self.operand(q) for q in operands], _tag(term))
