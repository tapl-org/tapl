# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""BANF: block-based ANF; SSA with block parameters instead of phi nodes, as in MLIR and Cranelift."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from oymo.oymomo import banf_prim, printer, terms

Location = terms.Location


@dataclass
class Var:
    name: str
    location: Location | None = field(default=None, compare=False)


@dataclass
class Const:
    value: bytes
    form: terms.Term
    location: Location | None = field(default=None, compare=False)


type Atom = Var | Const


@dataclass
class PrimCall:
    op: str
    args: list[Atom]
    location: Location | None = field(default=None, compare=False)


@dataclass
class Call:
    function: str
    args: list[Atom]
    location: Location | None = field(default=None, compare=False)


@dataclass
class MakeStruct:
    fields: list[tuple[str, Atom]]
    location: Location | None = field(default=None, compare=False)


@dataclass
class GetField:
    struct: Atom
    label: str
    location: Location | None = field(default=None, compare=False)


@dataclass
class GetData:
    name: str
    location: Location | None = field(default=None, compare=False)


type Op = PrimCall | Call | MakeStruct | GetField | GetData


@dataclass
class Let:
    name: str
    value: Op
    location: Location | None = field(default=None, compare=False)


@dataclass
class Jump:
    target: str
    args: list[Atom]
    location: Location | None = field(default=None, compare=False)


@dataclass
class Branch:
    condition: Atom
    then_target: str
    then_args: list[Atom]
    else_target: str
    else_args: list[Atom]
    location: Location | None = field(default=None, compare=False)


@dataclass
class Return:
    value: Atom
    location: Location | None = field(default=None, compare=False)


type Terminator = Jump | Branch | Return


@dataclass
class Block:
    label: str
    params: list[tuple[str, terms.Term]]
    lets: list[Let]
    terminator: Terminator
    location: Location | None = field(default=None, compare=False)


@dataclass
class Function:
    name: str
    return_form: terms.Term
    blocks: list[Block]
    location: Location | None = field(default=None, compare=False)

    @property
    def params(self) -> list[tuple[str, terms.Term]]:
        return self.blocks[0].params


@dataclass
class Signature:
    name: str
    params: list[tuple[str, terms.Term]]
    return_form: terms.Term
    location: Location | None = field(default=None, compare=False)


@dataclass
class Data:
    name: str
    form: terms.Term
    location: Location | None = field(default=None, compare=False)


type Binding = Function | Signature | Data


@dataclass
class Module:
    bindings: list[Binding]

    def lookup(self, name: str) -> Binding | None:
        return next((b for b in self.bindings if b.name == name), None)


class FormError(Exception):
    def __init__(self, message: str, location: Location | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


def atom_form(atom: Atom, forms: Mapping[str, terms.Term]) -> terms.Term:
    match atom:
        case Const(form=form):
            return form
        case Var(name=name):
            if name not in forms:
                raise FormError(f'Unknown name {name!r}.', atom.location)
            return forms[name]
    raise AssertionError(atom)


def callee(op: Call, module: Module) -> Function | Signature:
    binding = module.lookup(op.function)
    if not isinstance(binding, Function | Signature):
        raise FormError(f'{op.function!r} is not a function.', op.location)
    return binding


def form_of(op: Op, forms: Mapping[str, terms.Term], module: Module) -> terms.Term:
    """The result form of `op`, given the forms of the names in scope."""
    match op:
        case PrimCall(op=name):
            if name not in banf_prim.PRIMS:
                raise FormError(f'Unknown prim op {name!r}.', op.location)
            return banf_prim.PRIMS[name].result
        case Call():
            return callee(op, module).return_form
        case MakeStruct(fields=fields):
            return terms.struct_form([(label, atom_form(atom, forms)) for label, atom in fields])
        case GetField(struct=struct, label=label):
            struct_form = atom_form(struct, forms)
            for field_label, field_form in terms.struct_fields(struct_form) or []:
                if field_label == label:
                    return field_form
            raise FormError(f'Form {show_form(struct_form)} has no field {label!r}.', op.location)
        case GetData(name=name):
            binding = module.lookup(name)
            if not isinstance(binding, Data):
                raise FormError(f'{name!r} is not imported data.', op.location)
            return binding.form
    raise AssertionError(op)


def field_index(form: terms.Term, label: str) -> int:
    for index, (field_label, _) in enumerate(terms.struct_fields(form) or []):
        if field_label == label:
            return index
    raise FormError(f'Form {show_form(form)} has no field {label!r}.')


# Verifier


def _check_args(what, params, args, forms, location):
    if len(args) != len(params):
        raise FormError(f'{what} takes {len(params)} arguments, got {len(args)}.', location)
    for (label, param_form), arg in zip(params, args, strict=True):
        arg_form = atom_form(arg, forms)
        if arg_form != param_form:
            raise FormError(
                f'{what} expects {label}: {show_form(param_form)}, got {show_form(arg_form)}.',
                arg.location or location,
            )


def _check_op(op, forms, module):
    match op:
        case PrimCall(op=name, args=args):
            form_of(op, forms, module)
            _check_args(f'prim.{name}', banf_prim.PRIMS[name].params, args, forms, op.location)
        case Call(function=name, args=args):
            _check_args(name, callee(op, module).params, args, forms, op.location)
        case _:
            form_of(op, forms, module)


def _check_jump(function, target, args, forms, location):
    blocks = {block.label: block for block in function.blocks}
    if target not in blocks:
        raise FormError(f'Unknown block {target!r}.', location)
    if target == function.blocks[0].label:
        raise FormError('Cannot jump to the entry block.', location)
    _check_args(f'Block {target}', blocks[target].params, args, forms, location)


def _verify_function(function, module):
    if not function.blocks:
        raise FormError(f'Function {function.name!r} has no blocks.', function.location)
    labels = [block.label for block in function.blocks]
    if len(set(labels)) != len(labels):
        raise FormError(f'Function {function.name!r} has duplicate block labels.', function.location)
    for block in function.blocks:
        forms = {}
        for name, form in block.params:
            if name in forms:
                raise FormError(f'Duplicate name {name!r}.', block.location)
            forms[name] = form
        for let in block.lets:
            if let.name in forms:
                raise FormError(f'Duplicate name {let.name!r}.', let.location)
            _check_op(let.value, forms, module)
            forms[let.name] = form_of(let.value, forms, module)
        match block.terminator:
            case Jump(target=target, args=args) as jump:
                _check_jump(function, target, args, forms, jump.location)
            case Branch() as branch:
                condition_form = atom_form(branch.condition, forms)
                if condition_form != terms.name_form('i1'):
                    raise FormError(f'Branch condition must be i1, got {show_form(condition_form)}.', branch.location)
                _check_jump(function, branch.then_target, branch.then_args, forms, branch.location)
                _check_jump(function, branch.else_target, branch.else_args, forms, branch.location)
            case Return(value=value) as ret:
                value_form = atom_form(value, forms)
                if value_form != function.return_form:
                    raise FormError(
                        f'Function {function.name!r} returns {show_form(function.return_form)}, '
                        f'got {show_form(value_form)}.',
                        value.location or ret.location,
                    )


def verify(module: Module) -> None:
    """Raises FormError if the module is ill-formed."""
    names = [binding.name for binding in module.bindings]
    for name in names:
        if names.count(name) > 1:
            raise FormError(f'Duplicate binding {name!r}.')
    for binding in module.bindings:
        if isinstance(binding, Function):
            _verify_function(binding, module)


# Printer

_PLAIN_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_RESERVED = frozenset({'if', 'then', 'else', 'fix'})


def show_name(name: str) -> str:
    if _PLAIN_NAME.fullmatch(name) and name not in _RESERVED:
        return name
    escaped = name.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def show_form(form: terms.Term) -> str:
    """BANF's own form syntax: `i32`, `{a: i32}`, `(A => B)`. `unknown` for an omitted form,
    and oymomo syntax in parentheses for any other term."""
    if (name := terms.form_name(form)) is not None:
        return show_name(name)
    if isinstance(form, terms.FunctionForm):
        return f'({_show_field_form(form)})'
    if (fields := terms.struct_fields(form)) is not None:
        return '{' + ', '.join(f'{show_name(label)}: {_show_field_form(f)}' for label, f in fields) + '}'
    if form is terms.Empty:
        return 'unknown'
    return f'({printer.show(form)})'


def _show_field_form(form):
    if isinstance(form, terms.FunctionForm):
        return f'{show_form(form.param)} => {_show_field_form(form.result)}'
    return show_form(form)


def show_atom(atom: Atom) -> str:
    match atom:
        case Var(name=name):
            return show_name(name)
        case Const(value=value, form=form):
            return f'[{value.hex()}]:{show_form(form)}'
    raise AssertionError(atom)


def _show_args(args):
    return '(' + ', '.join(show_atom(arg) for arg in args) + ')'


def show_op(op: Op) -> str:
    match op:
        case PrimCall(op=name, args=args):
            return f'prim.{show_name(name)}{_show_args(args)}'
        case Call(function=name, args=args):
            return f'{show_name(name)}{_show_args(args)}'
        case MakeStruct(fields=fields):
            return '{' + ', '.join(f'{show_name(label)} = {show_atom(atom)}' for label, atom in fields) + '}'
        case GetField(struct=struct, label=label):
            return f'{show_atom(struct)}.{show_name(label)}'
        case GetData(name=name):
            return show_name(name)
    raise AssertionError(op)


def show_terminator(terminator: Terminator) -> str:
    match terminator:
        case Jump(target=target, args=args):
            return f'jump {show_name(target)}{_show_args(args)}'
        case Branch() as branch:
            return (
                f'branch {show_atom(branch.condition)}, '
                f'{show_name(branch.then_target)}{_show_args(branch.then_args)}, '
                f'{show_name(branch.else_target)}{_show_args(branch.else_args)}'
            )
        case Return(value=value):
            return f'return {show_atom(value)}'
    raise AssertionError(terminator)


def _show_params(params):
    return '(' + ', '.join(f'{show_name(name)}: {show_form(form)}' for name, form in params) + ')'


def _show_function(function):
    lines = [f'{show_name(function.name)}: {show_form(function.return_form)}']
    for block in function.blocks:
        lines.append(f'  {show_name(block.label)}{_show_params(block.params)}:')
        lines.extend(f'    {show_name(let.name)} = {show_op(let.value)}' for let in block.lets)
        lines.append(f'    {show_terminator(block.terminator)}')
    return '\n'.join(lines)


def show(module: Module) -> str:
    parts = []
    for binding in module.bindings:
        match binding:
            case Signature(name=name, params=params, return_form=return_form):
                parts.append(f'{show_name(name)}{_show_params(params)}: {show_form(return_form)}')
            case Data(name=name, form=form):
                parts.append(f'{show_name(name)}: {show_form(form)}')
            case Function():
                if parts:
                    parts.append('')
                parts.append(_show_function(binding))
    return '\n'.join(parts) + '\n'
