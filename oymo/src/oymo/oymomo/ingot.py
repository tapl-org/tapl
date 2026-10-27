# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: the shape a translation to SSA reads.

An ingot is `{version = '0', symbols = {lᵢ = eᵢ}, target = t}`; each entry `eᵢ` is a struct
with a `type` and at most one of `body` (a definition), `init` (a global variable) or
`value` (a constant); an entry with only `type` is a declaration.

A definition's body is `λm. λp. R` in ANF. `read_ingot` checks the grammar
(`anf.region_error`), then every variable's kind: `m.l` names a symbol and `m []`
only heads a region; `p.l` names a parameter; `r.l` names a block of the region `r` and
only heads a jump, with one operand per parameter; a value has no fields.

It gives the body as regions and blocks, every variable resolved (`Use` of a `Var`, `Arg`,
`Address`, data) and every bound name made distinct: a repeated name takes the
smallest free number (`c`, `c1`).

`ingot_of` runs the whole way from a parsed program: resolve, normalize,
reject a stuck normal form, and read the ingot.
"""

from dataclasses import dataclass, field

from oymo.core import syntax
from oymo.oymomo import anf, printer, reduction, strategy, terms

VERSION = '0'


class IngotError(Exception):
    def __init__(self, message: str, span: int) -> None:
        super().__init__(message)
        self.message = message
        self.span = span


# Operands, resolved.


@dataclass(eq=False)
class Var:
    """A value: bound by a `let` or a block's `λ`. `name` is unique in its definition."""

    name: str
    span: int = field(default=0, compare=False)


@dataclass(eq=False)
class Use:
    """A value used as an operand, where it is used."""

    var: Var
    span: int = 0


@dataclass
class Arg:
    """`p.l`: the argument for the parameter `l`."""

    label: str
    span: int = field(default=0, compare=False)


@dataclass
class Address:
    """`m.l` as an operand: the address of the symbol `l`."""

    name: str
    span: int = field(default=0, compare=False)


# A data operand stays the term it is (a byte array or a struct of data), so an opcode
# reads its type fields as terms.
type Operand = Use | Arg | Address | syntax.Term


@dataclass(eq=False)
class Instruction:
    """`let result = O {lᵢ = Qᵢ}`: an opcode call (`opcode`) or a call (`callee`)."""

    result: Var
    opcode: str | None
    callee: str | None
    fields: list[tuple[str, Operand]]
    span: int = 0


@dataclass(eq=False)
class Jump:
    target: 'Block'
    operands: list[Operand]
    span: int = 0


@dataclass(eq=False)
class Return:
    value: Operand
    span: int = 0


@dataclass(eq=False)
class Branch:
    """`{Jᵢ} P`: arm `i` when the condition is `i`, the last arm otherwise."""

    arms: list[Jump]
    condition: Use | Arg
    span: int = 0


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
    span: int = 0


@dataclass(eq=False)
class Region:
    """`m [] (λr. {lᵢ = Kᵢ})`; `blocks[0]` is field 0."""

    binder: str
    blocks: list[Block]
    span: int = 0


type Terminal = Return | Jump | Branch | Region


@dataclass(eq=False)
class FunctionType:
    """`{'function', {xᵢ = tᵢ}, t}`."""

    params: list[tuple[str, syntax.Term]]
    result: syntax.Term


@dataclass(eq=False)
class Definition:
    name: str
    type: FunctionType
    args: str
    region: Region
    span: int = 0


@dataclass(eq=False)
class Declaration:
    """An entry with only a `type`: a function, or a variable, of another module."""

    name: str
    type: FunctionType | syntax.Term
    span: int = 0


@dataclass(eq=False)
class Constant:
    name: str
    type: syntax.Term
    value: syntax.Term
    span: int = 0


@dataclass(eq=False)
class Global:
    name: str
    type: syntax.Term
    init: syntax.Term
    span: int = 0


type Symbol = Definition | Declaration | Constant | Global


@dataclass(eq=False)
class Ingot:
    version: str
    symbols: list[Symbol]
    target: syntax.Term | None = None

    def lookup(self, name: str) -> Symbol | None:
        return next((s for s in self.symbols if s.name == name), None)


def function_type(symbol: Symbol | None) -> FunctionType | None:
    """The function type of a definition or a declared function, else None."""
    if isinstance(symbol, Definition | Declaration) and isinstance(symbol.type, FunctionType):
        return symbol.type
    return None


def ingot_of(term: syntax.Term, max_steps: int = strategy.MAX_STEPS) -> Ingot:
    """The ingot a parsed program reduces to. Raises `ReductionError` or `IngotError`."""
    normal = strategy.normalize(reduction.resolve(term), max_steps)
    if (stuck := reduction.stuck_part(normal)) is not None:
        raise IngotError('The program is stuck here: no rule can ever reduce this part.', _span(stuck))
    return read_ingot(normal)


def _span(term):
    return getattr(term, 'span', 0)


def _fields(struct):
    return {f.label: f.value for f in struct.fields}


_INGOT_FIELDS = ('version', 'symbols', 'target')


def read_ingot(term: syntax.Term) -> Ingot:
    """`term`, a resolved normal form, read as an ingot."""
    if not isinstance(term, terms.Struct):
        raise IngotError('Not an ingot: an ingot is a struct {version, symbols, target}.', _span(term))
    for f in term.fields:
        if f.label not in _INGOT_FIELDS:
            raise IngotError(f'Not an ingot: unknown field {f.label!r}; an ingot has {list(_INGOT_FIELDS)}.', f.span)
    parts = _fields(term)
    for required in ('version', 'symbols'):
        if required not in parts:
            raise IngotError(f'Not an ingot: it has no {required!r}.', _span(term))
    version = parts['version']
    if not isinstance(version, terms.ByteArray) or version.as_str != VERSION:
        raise IngotError(f'Unknown ingot version {_show(version)}; this oymo reads {VERSION!r}.', _span(version))
    symbols_term = parts['symbols']
    if not isinstance(symbols_term, terms.Struct):
        raise IngotError('Not an ingot: symbols must be a struct of entries.', _span(symbols_term))
    ingot = Ingot(VERSION, [], parts.get('target'))
    bodies = []
    for f in symbols_term.fields:
        if not f.label:
            raise IngotError("An entry needs a label: its symbol's name.", f.span or _span(f.value))
        symbol, body = _entry(f.label, f.value)
        ingot.symbols.append(symbol)
        if body is not None:
            bodies.append((symbol, body))
    for symbol, body in bodies:
        symbol.region, symbol.args = _Body(ingot, symbol).read(body)
    return ingot


def _show(term):
    return printer.show(term)


_KINDS = ('body', 'init', 'value')


def _entry(name, term):
    """The symbol of the entry `name = term`, and the body to read later, if any."""
    if not isinstance(term, terms.Struct):
        raise IngotError(f'Entry {name!r} must be a struct {{type, ...}}.', _span(term))
    parts = _fields(term)
    for label in parts:
        if label != 'type' and label not in _KINDS:
            raise IngotError(
                f'Entry {name!r} has an unknown field {label!r}; it may have type, body, init, value.', _span(term)
            )
    if 'type' not in parts:
        raise IngotError(f'Entry {name!r} needs a type.', _span(term))
    kinds = [label for label in _KINDS if label in parts]
    if len(kinds) > 1:
        raise IngotError(
            f'Entry {name!r} has {kinds[0]} and {kinds[1]}; it may have at most one of {list(_KINDS)}.', _span(term)
        )
    type_term = _data(parts['type'], 'type')
    fn = _function_type(type_term)
    match kinds:
        case ['body']:
            if fn is None:
                raise IngotError(
                    f"Entry {name!r} has a body, so its type must be {{'function', {{x = t, ...}}, t}}.",
                    _span(type_term),
                )
            return Definition(name, fn, '', Region('', []), _span(term)), parts['body']
        case ['init']:
            return Global(name, type_term, _data(parts['init'], 'init'), _span(term)), None
        case ['value']:
            return Constant(name, type_term, _data(parts['value'], 'value'), _span(term)), None
    return Declaration(name, fn if fn is not None else type_term, _span(term)), None


def _data(term, what):
    if not reduction.is_data(term):
        raise IngotError(f'A {what} must be data: byte arrays and structs of them.', _span(term))
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
            "A function type is {'function', {x = t, ...}, t}: labeled parameters, then the result.", _span(term)
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
    """Reads one definition's body `λm. λp. R`."""

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
            raise IngotError(f'The body of {name!r} must be λm. λp. m [] (λr. {{blocks}}).', _span(body))
        region = body.body.body
        if anf.region_parts(region) is None:
            raise IngotError(f'The body of {name!r} must be λm. λp. m [] (λr. {{blocks}}).', _span(region))
        if (error := anf.region_error(region)) is not None:
            raise IngotError(f'{name!r} is not in ANF: {error.message}', error.span)
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
            raise IngotError('Only the module runs a region: m [] (λr. {...}).', _span(head))
        binder = self.fresh(blocks_lambda.param_name)
        region = Region(binder, [], _span(term))
        for i, f in enumerate(blocks_lambda.body.fields):
            if i > 0 and not f.label:
                raise IngotError(
                    'A block after field 0 needs a label, so a jump can name it.', f.span or _span(f.value)
                )
            arity, block = 0, f.value
            while isinstance(block, terms.Lambda):
                arity, block = arity + 1, block.body
            label = f.label or '0'
            region.blocks.append(Block(f'{binder}.{label}', f.label, arity, span=f.span or _span(f.value)))
        self.env.append(_Binder('region', region=region))
        for block, f in zip(region.blocks, blocks_lambda.body.fields, strict=True):
            self.block(block, f.value)
        self.env.pop()
        return region

    def block(self, block, term):
        depth = len(self.env)
        while isinstance(term, terms.Lambda):
            var = Var(self.fresh(term.param_name), _span(term))
            block.params.append(var)
            self.env.append(_Binder('value', value=var))
            term = term.body
        while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
            instruction = self.instruction(term.argument)
            instruction.result = Var(self.fresh(term.function.param_name), _span(term.function))
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
            return Instruction(Var(''), operator.as_str or '', None, fields, _span(term))
        binder, labels = self.binder(operator)
        symbol = self.ingot.lookup(labels[0]) if binder.kind == 'module' and len(labels) == 1 else None
        fn = function_type(symbol)
        if fn is None:
            raise IngotError(
                'An instruction calls a function, m.l {...} with l a function of the module.', _span(operator)
            )
        names = [name for name, _ in fn.params]
        given = [f.label for f in struct.fields]
        if given != names:
            raise IngotError(
                f'The call to {symbol.name!r} must give {names}, in order; it gives {given}.', _span(struct)
            )
        fields = [(f.label, self.operand(f.value)) for f in struct.fields]
        return Instruction(Var(''), None, symbol.name, fields, _span(term))

    # Operands

    def operand(self, term):
        if reduction.is_data(term):
            return term
        binder, labels = self.binder(term)
        span = _span(term)
        match binder.kind:
            case 'module':
                if len(labels) != 1 or self.ingot.lookup(labels[0]) is None:
                    raise IngotError(
                        'm names the symbols: an operand through m is m.l, l a symbol of the module.', span
                    )
                return Address(labels[0], span)
            case 'arguments':
                names = [name for name, _ in self.definition.type.params]
                if not labels:
                    raise IngotError(f'p is never used whole: read an argument as p.l, l one of {names}.', span)
                if labels[0] not in names:
                    raise IngotError(f'{self.definition.name!r} has no parameter {labels[0]!r}; it has {names}.', span)
                if len(labels) > 1:
                    raise IngotError(
                        "An argument has no fields: read a field of a struct value with 'extractvalue'.", span
                    )
                return Arg(labels[0], span)
            case 'region':
                raise IngotError('r.l is a block: it only heads a jump.', span)
        if labels:
            raise IngotError("A value has no fields: read a field of a struct value with 'extractvalue'.", span)
        return Use(binder.value, span)

    def condition(self, term):
        operand = self.operand(term)
        if not isinstance(operand, Use | Arg):
            raise IngotError('A branch condition is a value or an argument p.l.', _span(term))
        return operand

    # Terminals

    def terminal(self, term):
        if anf.region_parts(term) is not None:
            return self.region(term)
        if isinstance(term, terms.Apply) and isinstance(term.function, terms.Struct):
            arms = [self.jump(f.value, arm=True) for f in term.function.fields]
            return Branch(arms, self.condition(term.argument), _span(term))
        if reduction.is_data(term):
            return Return(term, _span(term))
        head, operands = anf.jump_parts(term)
        kind = self.binder(head)[0].kind
        if kind == 'region':
            return self.jump(term, arm=False)
        if operands:
            if kind == 'module':
                raise IngotError(anf.TAIL_CALL, _span(term))
            raise IngotError('Only a block r.l is applied at the end of a block.', _span(term))
        return Return(self.operand(term), _span(term))

    def jump(self, term, *, arm):
        head, operands = anf.jump_parts(term)
        binder, labels = self.binder(head)
        if binder.kind != 'region':
            raise IngotError(
                'An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ, r a region.'
                if arm
                else 'A jump goes to a block r.l of a region.',
                _span(head),
            )
        region = binder.region
        blocks = {block.label: block for block in region.blocks if block.label}
        if len(labels) != 1 or labels[0] not in blocks:
            raise IngotError(f'A jump names a block of {region.binder!r}: one of {list(blocks)}.', _span(head))
        target = blocks[labels[0]]
        if len(operands) != target.arity:
            raise IngotError(
                f'{target.name} takes {target.arity} operands, one per parameter; the jump gives {len(operands)}.',
                _span(term),
            )
        target.jumped = True
        return Jump(target, [self.operand(q) for q in operands], _span(term))
