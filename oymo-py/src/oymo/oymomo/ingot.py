# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: the shape a translation to SSA reads.

An ingot is a namespace: a struct `{lᵢ = Eᵢ}` whose every field is an entry or a
namespace again. A struct with a `type` field is an entry; any other struct is a
namespace. An entry has a `type`, at most one of `body` (a definition), `init` (a global
variable) or `value` (a constant), and an optional `link`, the symbol's name for the
linker. A type is a predef with no path (byte arrays and structs of them); an `init` or
`value` is one too, or `λg. C` with `C` a predef: its paths are symbol addresses
`g.l₁ ⋯ lₙ`; an entry with only `type` and `link` is a declaration, and one with only `type`
is a hole, which is rejected. Anything else left in a namespace is rejected too.

Each symbol is named by its path, its labels from the top (`('math', 'gcd')`). A
definition's body is `λg. λp. R` in ANF. `read_ingot` checks the grammar
(`anf.region_error`), then every variable's kind: `g.l₁ ⋯ lₙ` is a path through the
namespaces to a symbol; a region is `'R' (λr. {…})`; `p.l` names a parameter; `r.l` names a block of the region `r` and
only heads a jump, with one operand per parameter; a value has no fields; a struct operand
is a predef, so its only paths are symbol addresses `g.l₁ ⋯ lₙ`. A call is direct, headed by
`g.l₁ ⋯ lₙ`, or indirect, headed by `p.l` or a value whose type is a function type; it gives
one operand per parameter, in order, and a written label is the parameter's at its position
(`call_error`).

A predef is kept as `C` of `λg. C`: an address in it is the path `g.l₁ ⋯ lₙ` from the
index 0 (`address_path`), wherever it was written.

It gives the body as regions and blocks, every variable resolved (`Use` of a `Var`, `Arg`,
`Address`, a predef) and every bound name made distinct: a repeated name takes the
smallest free number (`c`, `c1`).

`ingot_of` runs the whole way from a parsed program: resolve, normalize,
reject a stuck normal form, and read the ingot. `ingots_of` first separates a program with
two layers, and gives each layer's ingot.
"""

from dataclasses import dataclass, field, replace

from oymo.core import syntax
from oymo.oymomo import anf, layers, meta, opcodes, printer, reduction, strategy, terms
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


# A predef operand stays the term it is (a byte array, or a struct of predefs whose paths
# are addresses from the index 0), so an opcode reads its type fields as terms.
type Operand = Use | Arg | Address | syntax.Term


def address_path(term: syntax.Term) -> tuple[str, ...] | None:
    """`(l₁, …, lₙ)` for an address `g.l₁ ⋯ lₙ` in a predef (`g` the index 0, `n ≥ 1`),
    else None."""
    labels = []
    while isinstance(term, terms.Project):
        labels.append(term.label)
        term = term.struct
    if labels and isinstance(term, terms.BruijnIndex) and term.index == 0:
        return tuple(labels[::-1])
    return None


def addresses(term: syntax.Term) -> list[syntax.Term]:
    """Every address in the predef `term`, in order."""
    if address_path(term) is not None:
        return [term]
    if isinstance(term, terms.Struct):
        return [a for f in term.fields for a in addresses(f.value)]
    return []


ADDRESS = 'An address in a predef is a path g.l₁ ⋯ lₙ to a symbol of the ingot.'
STRUCT_OPERAND = "A struct operand is a predef: build a struct of run-time values with 'insertvalue'."


@dataclass(eq=False)
class Instruction:
    """`let result = O {Qᵢ}`: an opcode call (`opcode`), a direct call (`callee`, the
    function's path), or an indirect call (`via`, the argument or value holding the
    function's address, whose type is a function type)."""

    result: Var
    opcode: str | None
    callee: tuple[str, ...] | None
    fields: list[tuple[str, Operand]]
    tag: Tag = NO_TAG
    via: Use | Arg | None = None


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
    tag: Tag = NO_TAG


@dataclass(eq=False)
class Region:
    """`'R' (λr. {lᵢ = Kᵢ})`; `blocks[0]` is field 0."""

    binder: str
    blocks: list[Block]
    tag: Tag = NO_TAG


type Terminal = Return | Jump | Branch | Region


@dataclass(eq=False)
class FunctionType:
    """`{'function', {xᵢ = tᵢ}, t}`."""

    params: list[tuple[str, syntax.Term]]
    result: syntax.Term

    def term(self) -> syntax.Term:
        """The type as the term `{'function', {xᵢ = tᵢ}, t}`."""
        params = terms.Struct([terms.Field(label, t) for label, t in self.params])
        return terms.Struct(
            [
                terms.Field('', terms.ByteArray.from_str('function')),
                terms.Field('', params),
                terms.Field('', self.result),
            ]
        )


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


def is_function_type(term: syntax.Term | None) -> bool:
    """`term` is tagged `'function'`: `{'function', …}`."""
    if not isinstance(term, terms.Struct) or not term.fields:
        return False
    tag = term.fields[0].value
    return isinstance(tag, terms.ByteArray) and tag.as_str == 'function'


def as_function_type(term: syntax.Term | None) -> FunctionType | None:
    """`{'function', {xᵢ = tᵢ}, t}` read as a `FunctionType`, or None for any other term."""
    if not isinstance(term, terms.Struct) or not is_function_type(term) or len(term.fields) != 3:  # noqa: PLR2004
        return None
    _, params, result = (f.value for f in term.fields)
    if not isinstance(params, terms.Struct) or any(not f.label for f in params.fields):
        return None
    return FunctionType([(f.label, f.value) for f in params.fields], result)


def call_error(name: str, params: list[tuple[str, syntax.Term]], given: list[str]) -> str | None:
    """Why a call to `name` with operands labeled `given` does not fit `params`, or None: a
    call gives one operand per parameter, in order; a written label is the parameter's at
    its position."""
    names = [label for label, _ in params]
    if len(given) != len(names):
        return f'The call to {name!r} gives {len(given)} operands; it takes {len(names)}, {names}.'
    for i, (label, param) in enumerate(zip(given, names, strict=True)):
        if label and label != param:
            return f'Operand {i} of the call to {name!r} is labeled {label!r}, but parameter {i} is {param!r}.'
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
    for symbol in ingot.symbols:
        if isinstance(symbol, Global | Constant):
            for address in addresses(symbol.init if isinstance(symbol, Global) else symbol.value):
                if ingot.lookup(address_path(address) or ()) is None:
                    raise IngotError(ADDRESS, _tag(address))
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
    type_term = _type(parts['type'])
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
            return Global(path, type_term, _initializer(parts['init'], 'init'), link, _tag(term)), None
        case ['value']:
            return Constant(path, type_term, _initializer(parts['value'], 'value'), link, _tag(term)), None
    if link is None:
        raise IngotError(f'{name!r} is a hole: give it a body or a link.', _tag(term))
    return Declaration(path, fn if fn is not None else type_term, link, _tag(term)), None


def _link(term):
    """A `link`: the symbol's name for the linker, a nonempty text byte array."""
    text = term.as_str if isinstance(term, terms.ByteArray) else None
    if not text:
        raise IngotError("A link is the symbol's name for the linker: a nonempty text byte array.", _tag(term))
    return text


def _type(term):
    """A type: a predef with no path."""
    if not reduction.is_data(term):
        raise IngotError('A type holds no address: it is byte arrays and structs of them.', _tag(term))
    return term


def _initializer(term, what):
    """An `init` or `value`: a predef with no path, or `λg. C` with `C` a predef whose paths
    are addresses; gives `C`. Whether each address names a symbol is checked once every
    symbol is read."""
    if reduction.is_data(term):
        return term
    if not isinstance(term, terms.Lambda):
        raise IngotError(
            f'An {what} is a predef: byte arrays and structs of them, or λg. C to hold symbol addresses g.l₁ ⋯ lₙ.',
            _tag(term),
        )
    _predef_shape(term.body)
    return term.body


def _predef_shape(term):
    """Checks that `term`, under its `λg`, is a predef: byte arrays, addresses `g.l₁ ⋯ lₙ`,
    and structs of them."""
    match term:
        case terms.ByteArray():
            return
        case terms.Struct(fields=fields):
            for f in fields:
                _predef_shape(f.value)
            return
    if anf.is_path(term):
        if address_path(term) is None:
            raise IngotError(ADDRESS, _tag(term))
        return
    raise IngotError('A predef holds byte arrays, addresses g.l₁ ⋯ lₙ and structs of them.', _tag(term))


def _function_type(term):
    """`{'function', params, result}` read as a `FunctionType`, or None for another type."""
    if not is_function_type(term):
        return None
    if (fn := as_function_type(term)) is None:
        raise IngotError(
            "A function type is {'function', {x = t, ...}, t}: labeled parameters, then the result.", _tag(term)
        )
    return fn


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
            raise IngotError(f"The body of {name!r} must be λg. λp. 'R' (λr. {{blocks}}).", _tag(body))
        region = body.body.body
        if anf.region_parts(region) is None:
            raise IngotError(f"The body of {name!r} must be λg. λp. 'R' (λr. {{blocks}}).", _tag(region))
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
        blocks_lambda = anf.region_parts(term)
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
            _check_opcode_name(operator)
            fields = [(f.label, self.operand(f.value)) for f in struct.fields]
            return Instruction(Var(''), operator.as_str or '', None, fields, _tag(term))
        binder, labels = self.binder(operator)
        given = [f.label for f in struct.fields]
        match binder.kind:
            case 'module':
                symbol = self.ingot.lookup(tuple(labels))
                fn = function_type(symbol)
                if fn is None:
                    raise IngotError(
                        'An instruction calls a function, g.l₁ ⋯ lₙ {...}, a path to a function of the ingot.',
                        _tag(operator),
                    )
                self._check_call(symbol.name, fn, given, struct)
                fields = [(f.label, self.operand(f.value)) for f in struct.fields]
                return Instruction(Var(''), None, symbol.path, fields, _tag(term))
            case 'region':
                raise IngotError('r.l is a block: it only heads a jump.', _tag(operator))
        via = self.operand(operator)
        if isinstance(via, Arg):
            type_term = dict(self.definition.type.params)[via.label]
            fn = as_function_type(type_term)
            if fn is None:
                raise IngotError(
                    f'p.{via.label} heads a call, so its type must be a function type; it is {_show(type_term)}.',
                    _tag(operator),
                )
            self._check_call(f'p.{via.label}', fn, given, struct)
        # A value's type is known only to the translation, which checks the call against it.
        fields = [(f.label, self.operand(f.value)) for f in struct.fields]
        return Instruction(Var(''), None, None, fields, _tag(term), via)

    def _check_call(self, name, fn, given, struct):
        if (error := call_error(name, fn.params, given)) is not None:
            raise IngotError(error, _tag(struct))

    # Operands

    def operand(self, term):
        if reduction.is_data(term):
            return term
        if isinstance(term, terms.Struct):
            return self.predef(term)
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

    def predef(self, term):
        """A struct operand, a predef: its paths are addresses `g.l₁ ⋯ lₙ`, kept as paths from
        the index 0."""
        match term:
            case terms.ByteArray():
                return term
            case terms.Struct(fields=fields):
                return replace(term, fields=[replace(f, value=self.predef(f.value)) for f in fields])
        binder, labels = self.binder(term)
        if binder.kind != 'module':
            raise IngotError(STRUCT_OPERAND, _tag(term))
        if not labels or self.ingot.lookup(tuple(labels)) is None:
            raise IngotError(ADDRESS, _tag(term))
        address: syntax.Term = terms.BruijnIndex(0, _tag(term))
        root = term
        projects = []
        while isinstance(root, terms.Project):
            projects.append(root)
            root = root.struct
        for project in reversed(projects):
            address = replace(project, struct=address)
        return address

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
        if isinstance(term, terms.ByteArray | terms.Struct):
            return Return(self.operand(term), _tag(term))
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
        if target is region.blocks[0]:
            raise IngotError(
                'A jump never goes to field 0, so the translation adds no block: give the loop head '
                'a block of its own (entry = r.loop, loop = …).',
                _tag(head),
            )
        if len(operands) != target.arity:
            raise IngotError(
                f'{target.name} takes {target.arity} operands, one per parameter; the jump gives {len(operands)}.',
                _tag(term),
            )
        return Jump(target, [self.operand(q) for q in operands], _tag(term))


def _collections() -> dict[str, list[str]]:
    """The opcode collections, each with its opcodes: a dotted name `c.o` is `o` of `c`."""
    found: dict[str, list[str]] = {}
    for name in opcodes.OPCODES:
        if '.' in name:
            collection, op = name.split('.', 1)
            found.setdefault(collection, []).append(op)
    return found


def _check_opcode_name(operator: terms.ByteArray) -> None:
    """A dotted opcode name `c.o` must name a known collection `c` and one of its opcodes; a
    name with no dot is an LLVM instruction's, checked by the translation."""
    name = operator.as_str or ''
    if '.' not in name:
        return
    collection, op = name.split('.', 1)
    known = _collections()
    if collection not in known:
        raise IngotError(f'No opcode collection {collection!r}: the collections are {sorted(known)}.', _tag(operator))
    if op not in known[collection]:
        raise IngotError(
            f'The collection {collection!r} has no opcode {op!r}; it has {sorted(known[collection])}.', _tag(operator)
        )
