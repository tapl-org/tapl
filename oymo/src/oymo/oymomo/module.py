# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Modules (semantics.tex, Section 8): the shape LLVM translation reads.

A module is `λm. {lᵢ = tᵢ}`, a struct of symbols:

- a definition `{gives = t, body = λf. {lᵢ = kᵢ}}`, with at least one block `kᵢ`;
- a block `{takes = {xᵢ = tᵢ}, body = λp. e}`, with `e` in ANF (Section 7);
- a declaration `{takes = {xᵢ = tᵢ}, gives = t}`;
- a constant `{type = t, value = v}`, and a global variable `{type = t, init = v}`.

`read_module` reads a normal form (resolved: variables are `BruijnIndex`es) into these
parts and checks what ANF alone does not:

- a call `m.l {xᵢ = aᵢ}` names a definition or a declaration, with its parameters in order;
- a jump `f.l.body {xᵢ = aᵢ}` names a block, with its parameters in order, and ends the
  block's body (it is never bound by a `let`);
- an atom `m.l` names a symbol; `f` is only for jumps; a parameter is read as `p.x`.

An operand (D94) is an atom or a struct of operands: in an opcode call, a call, a jump or a return.

`module_of` runs the whole way from a parsed program: resolve, normalize (Section 6),
reject a stuck normal form (5.5), and read the module.
"""

from dataclasses import dataclass, field

from oymo.core import syntax
from oymo.oymomo import anf, reduction, strategy, terms

type Params = list[tuple[str, syntax.Term]]


class ModuleError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


@dataclass
class Block:
    """`{takes = {xᵢ = tᵢ}, body = λp. e}`. `body` is `e`, under `p`, `f` and `m`."""

    label: str
    takes: Params
    body: syntax.Term
    location: syntax.Location | None = field(default=None, compare=False)


@dataclass
class Definition:
    """`{gives = t, body = λf. {blocks}}`. Its parameters are its first block's."""

    name: str
    gives: syntax.Term
    blocks: list[Block]
    location: syntax.Location | None = field(default=None, compare=False)

    @property
    def takes(self) -> Params:
        return self.blocks[0].takes


@dataclass
class Declaration:
    """`{takes = {xᵢ = tᵢ}, gives = t}`: a function defined outside the module."""

    name: str
    takes: Params
    gives: syntax.Term
    location: syntax.Location | None = field(default=None, compare=False)


@dataclass
class Constant:
    """`{type = t, value = v}`; `m.l` is its address."""

    name: str
    type: syntax.Term
    value: syntax.Term
    location: syntax.Location | None = field(default=None, compare=False)


@dataclass
class Global:
    """`{type = t, init = v}`; `m.l` is its address, read and written with `load` and `store`."""

    name: str
    type: syntax.Term
    init: syntax.Term
    location: syntax.Location | None = field(default=None, compare=False)


type Symbol = Definition | Declaration | Constant | Global


@dataclass
class Module:
    symbols: list[Symbol]

    def lookup(self, name: str) -> Symbol | None:
        return next((s for s in self.symbols if s.name == name), None)


def module_of(term: syntax.Term, max_steps: int = strategy.MAX_STEPS) -> Module:
    """The module a parsed program reduces to. Raises `ReductionError` or `ModuleError`."""
    normal = strategy.normalize(reduction.resolve(term), max_steps)
    if (stuck := reduction.stuck_part(normal)) is not None:
        raise ModuleError('The program is stuck here: no rule can ever reduce this part.', _location(stuck))
    return read_module(normal)


def _location(term):
    return getattr(term, 'location', None)


def _labels(struct):
    return [f.label for f in struct.fields]


def _fields(struct):
    return {f.label: f.value for f in struct.fields}


def read_module(term: syntax.Term) -> Module:
    """`term`, a resolved normal form, read as a module `λm. {lᵢ = tᵢ}`."""
    if not isinstance(term, terms.Lambda) or not isinstance(term.body, terms.Struct):
        raise ModuleError('A module must be λm. {symbols}, with its outer abstractions applied.', _location(term))
    symbols = []
    for f in term.body.fields:
        if not f.label:
            raise ModuleError('A symbol needs a label: its name.', _location(f))
        symbols.append(_symbol(f.label, f.value))
    module = Module(symbols)
    for symbol in symbols:
        if isinstance(symbol, Definition):
            for block in symbol.blocks:
                _check_block(module, symbol, block)
    return module


_SHAPES = {
    ('body', 'gives'): 'definition',
    ('gives', 'takes'): 'declaration',
    ('type', 'value'): 'constant',
    ('init', 'type'): 'global',
}


def _symbol(name, term):
    shape = _SHAPES.get(tuple(sorted(_labels(term)))) if isinstance(term, terms.Struct) else None
    if shape is None:
        raise ModuleError(
            f'Symbol {name!r} must be a definition {{gives, body}}, a declaration {{takes, gives}}, '
            'a constant {type, value} or a global variable {type, init}.',
            _location(term),
        )
    parts = _fields(term)
    match shape:
        case 'definition':
            return Definition(name, _type(parts['gives']), _blocks(name, parts['body']), _location(term))
        case 'declaration':
            return Declaration(name, _params(parts['takes']), _type(parts['gives']), _location(term))
        case 'constant':
            return Constant(name, _type(parts['type']), _data(parts['value'], 'value'), _location(term))
    return Global(name, _type(parts['type']), _data(parts['init'], 'init'), _location(term))


def _type(term):
    """A type is an ordinary term (9.1); it must be data, so LLVM translation can read it."""
    return _data(term, 'type')


def _data(term, what):
    if not reduction.is_data(term):
        raise ModuleError(f'A {what} must be data: byte arrays and structs of them.', _location(term))
    return term


def _params(term):
    if not isinstance(term, terms.Struct) or any(not f.label for f in term.fields):
        raise ModuleError('`takes` must be a struct of labeled types, {x = t, ...}.', _location(term))
    return [(f.label, _type(f.value)) for f in term.fields]


def _blocks(name, term):
    if not isinstance(term, terms.Lambda) or not isinstance(term.body, terms.Struct) or not term.body.fields:
        raise ModuleError(f'The body of {name!r} must be λf. {{blocks}}, with at least one block.', _location(term))
    blocks = []
    for f in term.body.fields:
        if not f.label:
            raise ModuleError('A block needs a label.', _location(f))
        block = f.value
        if not isinstance(block, terms.Struct) or sorted(_labels(block)) != ['body', 'takes']:
            raise ModuleError(f'Block {f.label!r} must be {{takes, body}}.', _location(block))
        parts = _fields(block)
        body = parts['body']
        if not isinstance(body, terms.Lambda):
            raise ModuleError(f'The body of block {f.label!r} must be λp. e.', _location(body))
        blocks.append(Block(f.label, _params(parts['takes']), body.body, _location(block)))
    return blocks


@dataclass
class _Scope:
    """Where a block body is: `lets` let variables inside `p`, `f` and `m`."""

    module: Module
    definition: Definition
    block: Block
    lets: int = 0

    def kind(self, index):
        """'let', 'p', 'f' or 'm' for the variable `index` lambdas out."""
        if index < self.lets:
            return 'let'
        return ('p', 'f', 'm')[min(index - self.lets, 2)]


def _path(term):
    """`(root index, labels)` of a path from a variable."""
    labels = []
    while isinstance(term, terms.Project):
        labels.append(term.label)
        term = term.struct
    return term.index, labels[::-1]


def _check_block(module, definition, block):
    if (error := anf.anf_error(block.body, local=1)) is not None:
        raise ModuleError(f'Block {block.label!r} is not in ANF: {error.message}', error.location)
    scope = _Scope(module, definition, block)
    term = block.body
    while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
        _check_operation(scope, term.argument)
        scope.lets += 1
        term = term.function.body
    _check_terminal(scope, term)


def _check_operation(scope, term):
    if isinstance(term.function, terms.ByteArray):
        _check_operands(scope, term.argument)
    else:
        _check_call(scope, term, at_end=False)


def _check_terminal(scope, term):
    match term:
        case terms.Apply(function=terms.Struct(fields=fields), argument=condition):
            for f in fields:
                _check_return(scope, f.value)
            _check_atom(scope, condition)
        case _:
            _check_return(scope, term)


def _check_return(scope, term):
    if anf.is_operand(term):
        _check_operand(scope, term)
    else:
        _check_call(scope, term, at_end=True)


def _check_operands(scope, struct):
    for f in struct.fields:
        _check_operand(scope, f.value)


def _check_operand(scope, term):
    if isinstance(term, terms.Struct):
        _check_operands(scope, term)
    else:
        _check_atom(scope, term)


def _check_atom(scope, term):
    if isinstance(term, terms.ByteArray):
        return
    index, labels = _path(term)
    match scope.kind(index):
        case 'p':
            names = [name for name, _ in scope.block.takes]
            if not labels or labels[0] not in names:
                raise ModuleError(
                    f'Block {scope.block.label!r} reads its parameters as p.x, x one of {names}.', _location(term)
                )
        case 'f':
            raise ModuleError('f names the blocks; it is only for jumps, f.l.body {...}.', _location(term))
        case 'm':
            if len(labels) != 1 or scope.module.lookup(labels[0]) is None:
                raise ModuleError('An atom through m must be m.l, with l a symbol of the module.', _location(term))


def _check_call(scope, term, *, at_end):
    index, labels = _path(term.function)
    match scope.kind(index):
        case 'f':
            blocks = {block.label: block for block in scope.definition.blocks}
            if len(labels) != 2 or labels[0] not in blocks or labels[1] != 'body':  # noqa: PLR2004
                raise ModuleError(
                    f'A jump is f.l.body {{...}}, l one of the blocks {list(blocks)}.', _location(term.function)
                )
            if not at_end:
                raise ModuleError('A jump through f ends a block: it is never bound by a let.', _location(term))
            _check_arguments(scope, term, f'block {labels[0]!r}', blocks[labels[0]].takes)
        case 'm':
            callee = scope.module.lookup(labels[0]) if len(labels) == 1 else None
            if not isinstance(callee, Definition | Declaration):
                raise ModuleError(
                    'A call through m is m.l {...}, l a definition or a declaration.', _location(term.function)
                )
            _check_arguments(scope, term, f'{labels[0]!r}', callee.takes)


def _check_arguments(scope, term, what, takes):
    names = [name for name, _ in takes]
    given = _labels(term.argument)
    if given != names:
        raise ModuleError(
            f'The call to {what} must give {names}, in order; it gives {given}.', _location(term.argument)
        )
    _check_operands(scope, term.argument)
