# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""BANF: block-based ANF; SSA with block parameters instead of phi nodes, as in MLIR and Cranelift."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from oymo.oymomo import opcodes, printer, terms

Location = terms.Location

# An OpcodeCall prints its name bare (`add i32 a, b`), so an opcode named like a BANF
# keyword would read like a call or a terminator.
_BANF_KEYWORDS = frozenset({'call', 'jump', 'branch', 'switch', 'return'})
if _BANF_KEYWORDS & opcodes.OPCODES.keys():
    raise AssertionError('Opcode names must not shadow BANF keywords.')


@dataclass
class Var:
    """A name. A written `form` replaces the name's form; `Empty` means the name's own form."""

    name: str
    form: terms.Term = terms.Empty
    location: Location | None = field(default=None, compare=False)


@dataclass
class Const:
    value: bytes
    form: terms.Term
    location: Location | None = field(default=None, compare=False)


type Atom = Var | Const


@dataclass
class FormField:
    """A struct form passed to an opcode, such as `alloca`'s `{x: i32, y: i64}`. A named form
    (`'i32'`) is a `Const` with no form, as every bare byte array is."""

    form: terms.Term
    location: Location | None = field(default=None, compare=False)


@dataclass
class OpcodeCall:
    """`'add' {'i32', a, b}`: `fields` are the call's fields as atoms, by position; a bare
    byte array, such as the form `'i32'` or an operand `[01000000]`, is a `Const` with no
    form, and a struct form is a `FormField`. `form` is the result's form, as the opcode
    tells it. Printed positionally: `add 'i32', a, b`."""

    opcode: str
    fields: list[Atom | FormField]
    form: terms.Term
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
class GetIndex:
    """`s [01]`: the field at a position, labeled or not. Printed `s.1`."""

    struct: Atom
    index: int
    location: Location | None = field(default=None, compare=False)


@dataclass
class GetData:
    name: str
    location: Location | None = field(default=None, compare=False)


type Op = OpcodeCall | Call | MakeStruct | GetField | GetIndex | GetData


@dataclass
class Let:
    """`name = value`. A written `form` replaces the op's form; `Empty` means the op's form."""

    name: str
    value: Op
    form: terms.Term = terms.Empty
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
class Switch:
    """Jumps to target `k` when `selector`, read as unsigned, is `k`, and to the last target
    when it is past the last one, as a struct applied to an index selects its last field."""

    selector: Atom
    targets: list[tuple[str, list[Atom]]]
    location: Location | None = field(default=None, compare=False)


@dataclass
class Return:
    value: Atom
    location: Location | None = field(default=None, compare=False)


type Terminator = Jump | Branch | Switch | Return


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
    """Module data. `value` is its initial bytes if the module defines it, or `None` if it's imported."""

    name: str
    form: terms.Term
    value: bytes | None = None
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
        case Const(form=form) if form == opcodes.PTR:
            # A byte array has no address to name (plan_memory.md decision 6).
            raise FormError("A pointer can't be a literal.", atom.location)
        case Const(form=form):
            return form
        case Var(name=name, form=form):
            if name not in forms:
                raise FormError(f'Unknown name {name!r}.', atom.location)
            # A written form replaces the name's form; the two are not compared.
            return forms[name] if form is terms.Empty else form
    raise AssertionError(atom)


def callee(op: Call, module: Module) -> Function | Signature:
    binding = module.lookup(op.function)
    if not isinstance(binding, Function | Signature):
        raise FormError(f'{op.function!r} is not a function.', op.location)
    return binding


def form_of(op: Op, forms: Mapping[str, terms.Term], module: Module) -> terms.Term:
    """The result form of `op`, given the forms of the names in scope."""
    match op:
        case OpcodeCall(form=form):
            return form
        case Call():
            return callee(op, module).return_form
        case MakeStruct(fields=fields):
            return terms.Struct([terms.Field(label, atom_form(atom, forms)) for label, atom in fields])
        case GetField(struct=struct, label=label):
            struct_form = atom_form(struct, forms)
            if isinstance(struct_form, terms.Struct):
                for f in struct_form.fields:
                    if f.label == label:
                        return f.value
            raise FormError(f'Form {show_form(struct_form)} has no field {label!r}.', op.location)
        case GetIndex(struct=struct, index=index):
            return indexed_field(atom_form(struct, forms), index, op.location)[1]
        case GetData(name=name):
            binding = module.lookup(name)
            if not isinstance(binding, Data):
                raise FormError(f'{name!r} is not data.', op.location)
            return binding.form
    raise AssertionError(op)


def let_form(let: Let, forms: Mapping[str, terms.Term], module: Module) -> terms.Term:
    """The form of the name `let` binds: its written form, or else its op's form. The written
    form replaces the op's; the two are not compared."""
    if let.form is not terms.Empty:
        return let.form
    return form_of(let.value, forms, module)


def field_index(form: terms.Term, label: str) -> int:
    if isinstance(form, terms.Struct):
        for index, f in enumerate(form.fields):
            if f.label == label:
                return index
    raise FormError(f'Form {show_form(form)} has no field {label!r}.')


def indexed_field(form: terms.Term, index: int, location: Location | None = None) -> tuple[int, terms.Term]:
    """The position and form of the field `GetIndex` reads: `index`, or the last field if
    `index` is past it, as in reduction."""
    if isinstance(form, terms.Struct) and form.fields:
        position = min(index, len(form.fields) - 1)
        return position, form.fields[position].value
    raise FormError(f'Form {show_form(form)} has no field at index {index}.', location)


# Verifier


def _check_args(what, params, args, forms, location):
    """`args` match `params` in number. A form isn't a type, so an arg's form is not
    compared with its param's."""
    if len(args) != len(params):
        raise FormError(f'{what} takes {len(params)} arguments, got {len(args)}.', location)
    for arg in args:
        atom_form(arg, forms)


def _check_load_store(op, forms):
    """`load {form, ptr}` and `store {value, ptr}`: two fields, `ptr` of form `ptr`, and a
    stored value that brings its own form (plan_memory.md decision 7)."""
    name, fields = op.opcode, op.fields
    if len(fields) != opcodes.LOAD_STORE_FIELDS:
        raise FormError(f'{name!r} takes {opcodes.LOAD_STORE_FIELDS} fields, got {len(fields)}.', op.location)
    if name == 'store':
        value = fields[0]
        if isinstance(value, FormField) or atom_form(value, forms) is terms.Empty:
            raise FormError("'store': value must have a form, such as [01000000]~'i32'.", op.location)
    pointer = fields[1]
    form = terms.Empty if isinstance(pointer, FormField) else atom_form(pointer, forms)
    if form != opcodes.PTR:
        got = show_form(form) or 'a bare byte array'
        raise FormError(f'{name!r} expects ptr: ptr, got {got}.', op.location)


def _check_op(op, forms, module):
    match op:
        case OpcodeCall(opcode=name, fields=fields):
            # The opcode reads its fields itself; here only the names in them must resolve.
            if name not in opcodes.OPCODES:
                raise FormError(f'Unknown opcode {name!r}.', op.location)
            for atom in fields:
                if not isinstance(atom, FormField):
                    atom_form(atom, forms)
            if name in ('load', 'store'):
                _check_load_store(op, forms)
        case Call(function=name, args=args):
            _check_args(name, callee(op, module).params, args, forms, op.location)
        case _:
            form_of(op, forms, module)


def _op_atoms(op):
    match op:
        case OpcodeCall(fields=fields):
            return [f for f in fields if not isinstance(f, FormField)]
        case Call(args=args):
            return args
        case MakeStruct(fields=fields):
            return [atom for _, atom in fields]
        case GetField(struct=struct) | GetIndex(struct=struct):
            return [struct]
    return []


def _terminator_atoms(terminator):
    match terminator:
        case Jump(args=args):
            return args
        case Branch() as branch:
            return [branch.condition, *branch.then_args, *branch.else_args]
        case Switch(selector=selector, targets=targets):
            return [selector, *(arg for _, args in targets for arg in args)]
        case Return(value=value):
            return [value]
    raise AssertionError(terminator)


def _check_no_store_use(atoms, stores, location):
    """A store gives `{}`, which only `$seq` may use, and `$seq` is gone by BANF
    (plan_memory.md decision 11): a store's name is used nowhere."""
    for atom in atoms:
        if isinstance(atom, Var) and atom.name in stores:
            raise FormError(
                f'{atom.name!r} is the result of a store; only $seq can use it.', atom.location or location
            )


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
        stores = set()
        for let in block.lets:
            if let.name in forms:
                raise FormError(f'Duplicate name {let.name!r}.', let.location)
            _check_no_store_use(_op_atoms(let.value), stores, let.location)
            _check_op(let.value, forms, module)
            forms[let.name] = let_form(let, forms, module)
            if isinstance(let.value, OpcodeCall) and let.value.opcode == 'store':
                stores.add(let.name)
        _check_no_store_use(_terminator_atoms(block.terminator), stores, block.terminator.location)
        match block.terminator:
            case Jump(target=target, args=args) as jump:
                _check_jump(function, target, args, forms, jump.location)
            case Branch() as branch:
                # Nothing about the condition's form, as a form isn't a type: which
                # conditions can be lowered is up to the backend.
                atom_form(branch.condition, forms)
                _check_jump(function, branch.then_target, branch.then_args, forms, branch.location)
                _check_jump(function, branch.else_target, branch.else_args, forms, branch.location)
            case Switch() as switch:
                # Nothing about the selector's form, as reduction puts nothing on an index:
                # which selectors can be lowered is up to the backend.
                atom_form(switch.selector, forms)
                if not switch.targets:
                    # As `{} i` is stuck: there is no last target to take.
                    raise FormError('A switch needs a target.', switch.location)
                for target, args in switch.targets:
                    _check_jump(function, target, args, forms, switch.location)
                passed = {}
                for target, args in switch.targets:
                    # An LLVM phi takes one entry per edge, and entries from one block must
                    # agree, so a repeated target must get the same args.
                    if passed.setdefault(target, args) != args:
                        raise FormError(f'A switch passes different args to {target!r}.', switch.location)
            case Return(value=value):
                # Not compared with the function's return form, as a form isn't a type.
                atom_form(value, forms)


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
_RESERVED = frozenset({'if', 'then', 'else'})


def show_name(name: str) -> str:
    if _PLAIN_NAME.fullmatch(name) and name not in _RESERVED:
        return name
    escaped = name.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _show_label(label: str, separator: str) -> str:
    """`label` and `separator` before a field; nothing for an unlabeled field (`''`)."""
    return '' if label == '' else f'{show_name(label)}{separator}'


def show_form(form: terms.Term) -> str:
    """BANF's own form syntax: `i32`, `{a: i32}`, `(A => B)`. Nothing for an omitted form,
    and oymomo syntax in parentheses for any other term."""
    if isinstance(form, terms.ByteArray) and (name := form.as_str) is not None:
        return show_name(name)
    if isinstance(form, terms.FunctionForm):
        return f'({_show_field_form(form)})'
    if isinstance(form, terms.Struct):
        return '{' + ', '.join(_show_label(f.label, ': ') + _show_field_form(f.value) for f in form.fields) + '}'
    if form is terms.Empty:
        return ''
    return f'({printer.show(form)})'


def _show_field_form(form):
    if isinstance(form, terms.FunctionForm):
        result = f'=> {_show_field_form(form.result)}'
        return result if form.param is terms.Empty else f'{show_form(form.param)} {result}'
    return show_form(form)


def show_atom(atom: Atom) -> str:
    match atom:
        case Var(name=name, form=form):
            return show_name(name) if form is terms.Empty else f'{show_name(name)}:{show_form(form)}'
        case Const(value=value, form=form) if form is terms.Empty:
            # A bare byte array, as oymomo writes it: `'i32'` or `[01000000]`.
            return printer.show(terms.ByteArray(value))
        case Const(value=value, form=form):
            return f'[{value.hex()}]:{show_form(form)}'
    raise AssertionError(atom)


def _show_args(args):
    return '(' + ', '.join(show_atom(arg) for arg in args) + ')'


def _show_opcode_call(op: OpcodeCall) -> str:
    """The name and the fields, by position: `add 'i32', a, b`, `zext 'i8', x, 'i32'`. An
    opcode call always has fields, so a bare name (`t0 = errno`) is always a data read."""
    fields = (show_form(f.form) if isinstance(f, FormField) else show_atom(f) for f in op.fields)
    return f'{show_name(op.opcode)} ' + ', '.join(fields)


def show_op(op: Op) -> str:
    match op:
        case OpcodeCall():
            return _show_opcode_call(op)
        case Call(function=name, args=args):
            return f'call {show_name(name)}{_show_args(args)}'
        case MakeStruct(fields=fields):
            return '{' + ', '.join(_show_label(label, ' = ') + show_atom(atom) for label, atom in fields) + '}'
        case GetField(struct=struct, label=label):
            return f'{show_atom(struct)}.{show_name(label)}'
        case GetIndex(struct=struct, index=index):
            # A label written as digits is quoted (`p."1"`), so `p.1` is never a label.
            return f'{show_atom(struct)}.{index}'
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
        case Switch(selector=selector, targets=targets):
            return f'switch {show_atom(selector)}, ' + ', '.join(
                f'{show_name(target)}{_show_args(args)}' for target, args in targets
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
        lines.extend(f'    {_show_let(let)}' for let in block.lets)
        lines.append(f'    {show_terminator(block.terminator)}')
    return '\n'.join(lines)


def _show_let(let):
    form = '' if let.form is terms.Empty else f': {show_form(let.form)}'
    return f'{show_name(let.name)}{form} = {show_op(let.value)}'


def show(module: Module) -> str:
    parts = []
    after_function = False
    for binding in module.bindings:
        is_function = isinstance(binding, Function)
        if parts and (is_function or after_function):
            parts.append('')
        match binding:
            case Signature(name=name, params=params, return_form=return_form):
                parts.append(f'{show_name(name)}{_show_params(params)}: {show_form(return_form)}')
            case Data(name=name, form=form, value=value):
                initializer = '' if value is None else f' = [{value.hex()}]'
                parts.append(f'{show_name(name)}: {show_form(form)}{initializer}')
            case Function():
                parts.append(_show_function(binding))
        after_function = is_function
    return '\n'.join(parts) + '\n'
