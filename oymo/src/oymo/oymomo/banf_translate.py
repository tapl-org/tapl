# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Translates oymomo terms into BANF.

`shape` resolves names, reduces the term to BANF's shape (`banf_shape`) and renames its binders
(`banf_rename`). `convert` then reads the shaped term into BANF; it does no normalization.
"""

from dataclasses import dataclass, replace

from oymo.core import syntax
from oymo.oymomo import banf_rename, banf_shape, opcodes, reduction, terms
from oymo.oymomo import banf_terms as banf
from oymo.oymomo.banf_rename import ARGS, BLOCKS, MODULE

# `$seq {d1, ..., dn, x}`: `x`, once `d1` to `dn` are done. A stuck one is the atom of `x`.
SEQ = 'seq'


class TranslationError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


# For a reduction-only built-in left in the term: what its argument must reduce to for it to
# reduce away. Used only in the error message.
_MUST_REDUCE_TO = {
    'fix': 'a lambda',
    'struct_to_fields': 'a struct',
    'fields_to_struct': 'a list of fields',
}


def _location(term):
    return getattr(term, 'location', None)


def _has_duplicate_labels(fields):
    """Whether two fields share a label. Unlabeled fields (`''`) are not duplicates of each other."""
    labels = [f.label for f in fields if f.label]
    return len(set(labels)) != len(labels)


def _check_labeled(fields, location, what):
    """Where a label names something (a param, a declaration, a block), every field needs one."""
    if any(not f.label for f in fields):
        raise TranslationError(f'{what} needs a label on every field.', location)


def _check_data_form(form, location, what):
    """A data form is a named form or a struct of data forms: no Empty parts, no function forms,
    and no other terms. Its fields may be unlabeled."""
    if isinstance(form, terms.FunctionForm):
        raise TranslationError(f'{what}: function forms nested inside other forms are not supported.', location)
    if isinstance(form, terms.Struct):
        if _has_duplicate_labels(form.fields):
            raise TranslationError(f'{what}: duplicate field labels in {banf.show_form(form)}.', location)
        for f in form.fields:
            _check_data_form(f.value, location, what)
    elif form is terms.Empty:
        raise TranslationError(f'{what}: form must be written.', location)
    elif not isinstance(form, terms.ByteArray) or form.as_str is None:
        raise TranslationError(f'{what}: form must be a literal, got {banf.show_form(form)}.', location)


@dataclass
class _Program:
    """Every declared symbol, by name. A function declared as `=> R` is a `banf.Function`."""

    bindings: dict[str, banf.Binding]


@dataclass
class _Block:
    """What the body matcher knows about the block it is in."""

    function: banf.Function
    params: list[tuple[str, terms.Term]]
    lets: list[banf.Let]

    def binder(self, term):
        """For a BruijnIndex in the block body: ('let', name), or one of ARGS, BLOCKS, MODULE.

        Above the body, from the inside out, are the lets so far, then args, blocks, module.
        None for anything else.
        """
        if not isinstance(term, terms.BruijnIndex):
            return None
        k = len(self.lets)
        if term.index < k:
            return ('let', self.lets[k - 1 - term.index].name)
        fixed = (ARGS, BLOCKS, MODULE)
        if term.index - k < len(fixed):
            return fixed[term.index - k]
        return None


def _unwrap(term):
    match term:
        case syntax.ErrorTerm(message=message):
            raise TranslationError(message, term.location)
        case (
            terms.Lambda(param_name=module_name, param_form=module_form, body=terms.Struct() as body) as module_lambda
        ) if module_name == MODULE:
            if not isinstance(module_form, terms.Struct):
                raise TranslationError(
                    'The module binder needs a struct form, such as module~{}.', module_lambda.location
                )
            return module_form, module_lambda.location, body
    raise TranslationError('Expected a program of the shape module~{...} -> {...}.', _location(term))


def _declarations(module_form, location):
    """One binding per declared symbol, in declaration order. A function declared as `=> R` is a
    `banf.Function` without blocks yet; its definition gives them."""
    declarations = {}
    _check_labeled(module_form.fields, location, 'The module form')
    for decl in module_form.fields:
        label, form = decl.label, decl.value
        decl_location = decl.location or location
        if label in declarations:
            raise TranslationError(f'Duplicate declaration {label!r}.', decl_location)
        what = f'Declaration {label!r}'
        if isinstance(form, terms.FunctionForm):
            param, result = form.param, form.result
            _check_data_form(result, decl_location, what)
            if param is terms.Empty:
                declarations[label] = banf.Function(label, result, [], decl_location)
                continue
            if not isinstance(param, terms.Struct):
                raise TranslationError(f'{what}: a function form needs a struct form as its param.', decl_location)
            _check_labeled(param.fields, decl_location, f'{what}: the param form')
            _check_data_form(param, decl_location, what)
            params = [(f.label, f.value) for f in param.fields]
            declarations[label] = banf.Signature(label, params, result, decl_location)
        else:
            _check_data_form(form, decl_location, what)
            declarations[label] = banf.Data(label, form, location=decl_location)
    return declarations


def _check_definition(field, declarations):
    """The declaration a body field defines: a function declared as `=> R`, or data."""
    name = field.label
    declaration = declarations.get(name)
    match declaration:
        case None:
            raise TranslationError(f'{name!r} is defined but not declared.', field.location)
        case banf.Signature():
            raise TranslationError(
                f'{name!r} declares its params; a definition takes them from its entry block.', field.location
            )
    return declaration


def _data_value(field):
    """The bytes of a data definition. Its form is the declared one, so a form written here is dropped."""
    match field.value:
        case terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)):
            return value
    raise TranslationError(
        f'{field.label!r} is declared as data, so its definition must be a byte array.', _location(field.value)
    )


def _blocks(field):
    """The blocks of a function definition, with params but no bodies yet, and their fields."""
    name = field.label
    match field.value:
        case terms.Lambda(param_name=binder, body=terms.Struct(fields=block_fields)) if (
            binder == BLOCKS and block_fields
        ):
            pass
        case _:
            raise TranslationError(
                f'Definition {name!r} must be a struct of blocks, such as blocks -> {{entry = args~{{}} -> ...}}.',
                _location(field.value),
            )
    _check_labeled(block_fields, _location(field.value), f'Definition {name!r}')
    blocks = []
    for block_field in block_fields:
        match block_field.value:
            case terms.Lambda(param_name=binder, param_form=terms.Struct() as form) if binder == ARGS:
                params = [(f.label, f.value) for f in form.fields]
                what = f'Block {block_field.label!r}'
                _check_labeled(form.fields, block_field.location, f'{what}: the param form')
                _check_data_form(form, block_field.location, what)
            case _:
                raise TranslationError(
                    f"Block {block_field.label!r} must be a lambda taking a struct, such as args~{{n = 'i32'}} -> ...",
                    _location(block_field.value),
                )
        if any(block.label == block_field.label for block in blocks):
            raise TranslationError(f'Duplicate block {block_field.label!r}.', block_field.location)
        blocks.append(banf.Block(block_field.label, params, [], banf.Return(banf.Var('')), block_field.location))
    return blocks, block_fields


def _not_a_value(name, location):
    return TranslationError(f'{name!r} cannot be used as a value.', location)


class _Translator:
    def __init__(self, program: _Program) -> None:
        self.program = program

    def atom(self, term, block):
        location = _location(term)
        match term:
            case terms.ByteArray():
                raise TranslationError('Byte array: form must be written.', location)
            case terms.Formed(term=terms.ByteArray(value=value), form=form):
                _check_data_form(form, location, 'Byte array')
                return banf.Const(value, form, location)
            case terms.Formed(term=inner, form=form):
                # The written form replaces the inner atom's form, which may itself be written.
                _check_data_form(form, location, 'Formed atom')
                return replace(self.atom(inner, block), form=form, location=location)
            case terms.BruijnIndex():
                match block.binder(term):
                    case ('let', name):
                        return banf.Var(name, location=location)
                    case str() as name:
                        raise _not_a_value(name, location)
            case terms.Apply(function=terms.Builtin(name=name), argument=argument) if name == SEQ:
                return self.seq(argument, block, location)
            case terms.Builtin(name=name):
                raise TranslationError(f'${name} must be applied.', location)
            case terms.Project(struct=struct, label=label) if block.binder(struct) == ARGS:
                if any(param == label for param, _ in block.params):
                    return banf.Var(label, location=location)
                raise TranslationError(f'Block has no param {label!r}.', location)
        raise TranslationError('Expected an atom: a byte array, a let name, or args.label.', location)

    def seq(self, argument, block, location):
        """A stuck `$seq {d1, ..., dn, x}` is the atom of `x`. Each `di` must be an atom, and is
        dropped: its let is already in the block, and BANF keeps let order. Labels are ignored."""
        if not isinstance(argument, terms.Struct):
            raise TranslationError('The argument to $seq must be a struct literal.', _location(argument))
        if not argument.fields:
            raise TranslationError('$seq needs a value.', location)
        for f in argument.fields:
            if not self.is_atom(f.value, block):
                raise TranslationError('$seq: every field must be an atom.', _location(f.value) or location)
        return self.atom(argument.fields[-1].value, block)

    def is_atom(self, term, block):
        try:
            self.atom(term, block)
        except TranslationError:
            return False
        return True

    def args(self, argument, params, what, block):
        """Expands a struct argument into a list of atoms in param order."""
        expected = [label for label, _ in params]
        location = _location(argument)
        match argument:
            case terms.BruijnIndex() if block.binder(argument) == ARGS:
                got = [label for label, _ in block.params]
                atoms = [banf.Var(label, location=location) for label in got]
            case terms.Struct(fields=fields):
                _check_labeled(fields, location, f'The argument to {what}')
                got = [f.label for f in fields]
                atoms = [self.atom(f.value, block) for f in fields]
            case _:
                raise TranslationError(f'The argument to {what} must be a struct literal or the block param.', location)
        if got != expected:
            raise TranslationError(f'{what} takes {{{", ".join(expected)}}}, got {{{", ".join(got)}}}.', location)
        return atoms

    def symbol(self, name, location):
        binding = self.program.bindings.get(name)
        if binding is None:
            raise TranslationError(f'{name!r} is not declared.', location)
        return binding

    def opcode_call(self, name, argument, block, location):
        """`'add' {'i32', a, b}`. Fields are positional and their labels are ignored. Each
        field becomes an atom; a bare byte array (a form such as `'i32'`, or an operand)
        becomes a `Const` with no form, read by the opcode. The opcode must tell the
        result's form from the fields."""
        opcode = opcodes.lookup(name)
        if opcode is None:
            shown = repr(name.as_str) if name.as_str is not None else f'[{name.value.hex()}]'
            raise TranslationError(f'Unknown opcode {shown}.', location)
        if not isinstance(argument, terms.Struct):
            raise TranslationError(f'The argument to {opcode.name!r} must be a struct literal.', _location(argument))
        values = [f.value for f in argument.fields]
        form = opcode.form_of(values)
        if form is None:
            raise TranslationError(f'{opcode.name!r} cannot tell its result form from its fields.', location)
        fields = [
            banf.Const(value.value, terms.Empty, _location(value))
            if isinstance(value, terms.ByteArray)
            else self.atom(value, block)
            for value in values
        ]
        return banf.OpcodeCall(opcode.name, fields, form, location)

    def op(self, term, block):
        location = _location(term)
        match term:
            case terms.Apply(function=terms.Builtin(name=name)) if name == SEQ:
                # A stuck `$seq` is an atom, not an op: `banf_shape` substitutes a let on it.
                # Reading it here reports a malformed one.
                self.atom(term, block)
            case terms.Apply(function=function, argument=index) if self.is_atom(function, block):
                # A value struct applied to an index reads that field, as a struct literal does in `reduce`.
                position = reduction.index_value(index)
                if position is None:
                    raise TranslationError('An index must be a byte array literal, such as [01].', _location(index))
                return banf.GetIndex(self.atom(function, block), position, location)
            case terms.Apply(function=terms.ByteArray() as name, argument=arg):
                return self.opcode_call(name, arg, block, location)
            case terms.Apply(function=terms.Builtin(name=name)):
                # A built-in is reduction-only: it should have reduced away, and is left only
                # when its rule couldn't fire.
                if name in reduction.BUILTINS:
                    must = _MUST_REDUCE_TO.get(name)
                    needs = f': its argument must reduce to {must}' if must else ''
                    raise TranslationError(f'${name} has no opcode, so it must reduce away{needs}.', location)
                raise TranslationError(f"Unknown built-in '${name}'.", location)
            case terms.Apply(function=terms.Project(struct=struct, label=name), argument=arg):
                base = block.binder(struct)
                if base == MODULE:
                    # An imported function's params are declared; a defined one's come from its entry block.
                    binding = self.symbol(name, location)
                    if isinstance(binding, banf.Data):
                        raise TranslationError(f'module.{name} is data, so it cannot be applied.', location)
                    return banf.Call(name, self.args(arg, binding.params, f'module.{name}', block), location)
                if base == BLOCKS:
                    raise TranslationError('A jump must be in tail position.', location)
            case terms.Struct(fields=fields):
                if _has_duplicate_labels(fields):
                    raise TranslationError('Duplicate field labels.', location)
                return banf.MakeStruct([(f.label, self.atom(f.value, block)) for f in fields], location)
            case terms.Project(struct=struct, label=name) if block.binder(struct) == MODULE:
                if isinstance(self.symbol(name, location), banf.Data):
                    return banf.GetData(name, location)
                raise TranslationError(f'module.{name} must be applied.', location)
            case terms.Builtin(name=name):
                raise TranslationError(f'${name} must be applied.', location)
            case terms.Project(struct=struct) if block.binder(struct) == ARGS:
                self.atom(term, block)
            case terms.Project(struct=struct, label=label):
                return banf.GetField(self.atom(struct, block), label, location)
            case terms.BruijnIndex() if isinstance(name := block.binder(term), str):
                raise _not_a_value(name, location)
            case terms.Apply(function=terms.Struct()):
                raise TranslationError('An if must be in tail position.', location)
        if self.is_atom(term, block):
            raise TranslationError("A let's value must be an op, not an atom.", location)
        raise TranslationError(
            "Expected an op: 'opcode' {...}, module.f {...}, module.data, a struct or a projection.", location
        )

    def jump(self, term, block):
        location = _location(term)
        match term:
            case terms.Apply(function=terms.Project(struct=struct, label=label), argument=arg) if (
                block.binder(struct) == BLOCKS
            ):
                targets = {b.label: b for b in block.function.blocks}
                if label not in targets:
                    raise TranslationError(f'Unknown block {label!r}.', location)
                if label == block.function.blocks[0].label:
                    raise TranslationError('Cannot jump to the entry block.', location)
                return label, self.args(arg, targets[label].params, f'Block {label!r}', block)
        return None

    def body(self, term, block):
        while True:
            location = _location(term)
            match term:
                case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=rest), argument=value):
                    if form is not terms.Empty:
                        _check_data_form(form, location, f'Let {name!r}')
                    let = banf.Let(name, self.op(value, block), form, location=location)
                    block.lets.append(let)
                    term = rest
                    continue
                case terms.Apply(function=terms.Struct(fields=[else_field, then_field]), argument=condition):
                    # `{e, t} c`, which is also `if c then t else e`: `[00]` picks field 0, so
                    # field 0 is else and field 1 is then. Labels are ignored, as struct apply ignores them.
                    atom = self.atom(condition, block)
                    else_jump = self.jump(else_field.value, block)
                    then_jump = self.jump(then_field.value, block)
                    if then_jump is None or else_jump is None:
                        raise TranslationError(
                            'Both branches of an if must be jumps, such as blocks.then0 {}.', location
                        )
                    # Both arms may jump to the same block: Cranelift allows it, and
                    # llvm_translate rejects it, since an LLVM phi can't tell the edges apart.
                    return banf.Branch(atom, *then_jump, *else_jump, location)
                case terms.Apply(function=terms.Struct(fields=[])):
                    raise TranslationError('A switch needs two or more fields.', location)
                case terms.Apply(function=terms.Struct(fields=[_])):
                    raise TranslationError('A switch needs two or more fields; one is a jump.', location)
                case terms.Apply(function=terms.Struct(fields=fields), argument=selector):
                    # `{a0, ..., an} k` with three or more fields: field `k` is taken, or the
                    # last one if `k` is past it. Labels are ignored, as for a branch.
                    atom = self.atom(selector, block)
                    targets = []
                    for f in fields:
                        if (target := self.jump(f.value, block)) is None:
                            raise TranslationError(
                                'Every field of a switch must be a jump, such as blocks.a {}.', location
                            )
                        targets.append(target)
                    return banf.Switch(atom, targets, location)
            if (jump := self.jump(term, block)) is not None:
                return banf.Jump(*jump, location)
            if self.is_atom(term, block):
                return banf.Return(self.atom(term, block), location)
            if isinstance(term, terms.Apply | terms.Struct | terms.Project):
                self.op(term, block)
                raise TranslationError(
                    'An op in tail position must be bound by a let, as in let t = op in t.', location
                )
            self.atom(term, block)
            raise AssertionError(term)

    def function(self, function, block_fields):
        for banf_block, block_field in zip(function.blocks, block_fields, strict=True):
            block = _Block(function, banf_block.params, banf_block.lets)
            banf_block.terminator = self.body(block_field.value.body, block)


def shape(term: syntax.Term) -> syntax.Term:
    """Resolves names, reduces to BANF's shape and renames binders."""
    try:
        return banf_rename.rename(banf_shape.shape(reduction.resolve(term)))
    except reduction.ReductionError as error:
        raise TranslationError(error.message, error.location) from error


def convert(term: syntax.Term) -> banf.Module:
    """Reads a shaped term into BANF."""
    module_form, module_location, body = _unwrap(term)
    declarations = _declarations(module_form, module_location)
    _check_labeled(body.fields, _location(body), 'The module body')
    definitions = []
    defined = set()
    for field in body.fields:
        if field.label in defined:
            raise TranslationError(f'Duplicate definition {field.label!r}.', field.location)
        defined.add(field.label)
        declaration = _check_definition(field, declarations)
        if isinstance(declaration, banf.Data):
            declaration.value = _data_value(field)
            continue
        declaration.blocks, block_fields = _blocks(field)
        declaration.location = field.location
        definitions.append((declaration, block_fields))
    for binding in declarations.values():
        if isinstance(binding, banf.Function) and not binding.blocks:
            raise TranslationError(f'{binding.name!r} declares no params, so it must be defined.', binding.location)
    translator = _Translator(_Program(declarations))
    for function, block_fields in definitions:
        translator.function(function, block_fields)
    module = banf.Module(list(declarations.values()))
    try:
        banf.verify(module)
    except banf.FormError as error:
        raise TranslationError(error.message, error.location) from error
    return module


def translate(term: syntax.Term) -> banf.Module:
    return convert(shape(term))
