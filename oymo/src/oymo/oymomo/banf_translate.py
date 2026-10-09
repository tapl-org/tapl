# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Translates oymomo terms into BANF.

`shape` resolves names, reduces the term to BANF's shape (`banf_reduce`) and renames its binders
(`banf_rename`). `convert` then reads the shaped term into BANF; it does no normalization.
"""

from dataclasses import dataclass

from oymo.core import syntax
from oymo.oymomo import banf_prim, banf_reduce, banf_rename, bruijn, terms
from oymo.oymomo import banf_terms as banf
from oymo.oymomo.banf_rename import ARGS, BLOCKS, DECLS, DEFS, PRIM


class TranslationError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


def _location(term):
    return getattr(term, 'location', None)


def _check_data_form(form, location, what):
    """A data form is a named form or a struct of data forms: no void parts, no function forms,
    and no other terms."""
    if isinstance(form, terms.FunctionForm):
        raise TranslationError(f'{what}: function forms nested inside other forms are not supported.', location)
    if isinstance(form, terms.Struct):
        labels = [f.label for f in form.fields]
        if len(set(labels)) != len(labels):
            raise TranslationError(f'{what}: duplicate field labels in {banf.show_form(form)}.', location)
        for f in form.fields:
            _check_data_form(f.value, location, what)
    elif form is terms.Void:
        raise TranslationError(f'{what}: form must be known.', location)
    elif terms.form_to_name(form) is None:
        raise TranslationError(f'{what}: form must be a literal, got {banf.show_form(form)}.', location)


@dataclass
class _Program:
    imports: dict[str, banf.Signature | banf.Data]
    functions: dict[str, banf.Function]


@dataclass
class _Block:
    """What the body matcher knows about the block it is in."""

    function: banf.Function
    params: list[tuple[str, terms.Term]]
    lets: list[banf.Let]

    def binder(self, term):
        """For a BruijnIndex in the block body: ('let', name), or one of ARGS, BLOCKS, DEFS, DECLS, PRIM.

        Above the body, from the inside out, are the lets so far, then args, blocks, defs, decls, prim.
        None for anything else.
        """
        if not isinstance(term, terms.BruijnIndex):
            return None
        k = len(self.lets)
        if term.index < k:
            return ('let', self.lets[k - 1 - term.index].name)
        fixed = (ARGS, BLOCKS, DEFS, DECLS, PRIM)
        if term.index - k < len(fixed):
            return fixed[term.index - k]
        return None


def _unwrap(term):
    match term:
        case syntax.ErrorTerm(message=message):
            raise TranslationError(message, term.location)
        case terms.Lambda(
            param_name=prim_name,
            body=terms.Lambda(
                param_name=decls_name,
                param_form=decls_form,
                body=terms.Lambda(param_name=defs_name, body=terms.Struct() as defs_struct),
            ) as decls_lambda,
        ) if (prim_name, decls_name, defs_name) == (PRIM, DECLS, DEFS):
            if not isinstance(decls_form, terms.Struct):
                raise TranslationError(
                    'The decls binder needs a struct form, such as decls: {}.', decls_lambda.location
                )
            return decls_form, decls_lambda.location, defs_struct
    raise TranslationError('Expected a program of the shape prim -> decls: {...} -> defs -> {...}.', _location(term))


def _imports(decls_form, location):
    imports = {}
    for decl in decls_form.fields:
        label, form = decl.label, decl.value
        if label in imports:
            raise TranslationError(f'Duplicate import {label!r}.', location)
        what = f'Import {label!r}'
        if isinstance(form, terms.FunctionForm):
            param, result = form.param, form.result
            if not isinstance(param, terms.Struct):
                raise TranslationError(f'{what}: a function form needs a struct form as its param.', location)
            params = [(f.label, f.value) for f in param.fields]
            _check_data_form(param, location, what)
            _check_data_form(result, location, what)
            imports[label] = banf.Signature(label, params, result, location)
        else:
            _check_data_form(form, location, what)
            imports[label] = banf.Data(label, form, location)
    return imports


def _function_header(field, imports):
    """Builds a Function whose blocks have params but no bodies yet."""
    name = field.label
    if name in imports:
        raise TranslationError(f'{name!r} is in both decls and defs.', field.location)
    match field.value:
        case terms.Lambda(param_name=binder, body=terms.Struct(fields=block_fields)) if (
            binder == BLOCKS and block_fields
        ):
            pass
        case _:
            raise TranslationError(
                f'Definition {name!r} must be a struct of blocks, such as blocks -> {{entry = args: {{}} -> ...}}.',
                _location(field.value),
            )
    blocks = []
    for block_field in block_fields:
        match block_field.value:
            case terms.Lambda(param_name=binder, param_form=terms.Struct() as form) if binder == ARGS:
                params = [(f.label, f.value) for f in form.fields]
                _check_data_form(form, block_field.location, f'Block {block_field.label!r}')
            case _:
                raise TranslationError(
                    f"Block {block_field.label!r} must be a lambda taking a struct, such as args: {{n = 'i32'}} -> ...",
                    _location(block_field.value),
                )
        if any(block.label == block_field.label for block in blocks):
            raise TranslationError(f'Duplicate block {block_field.label!r}.', block_field.location)
        blocks.append(banf.Block(block_field.label, params, [], banf.Return(banf.Var('')), block_field.location))
    return banf.Function(name, terms.Void, blocks, field.location), block_fields


def _not_a_value(name, location):
    return TranslationError(f'{name!r} cannot be used as a value.', location)


class _Translator:
    def __init__(self, program: _Program) -> None:
        self.program = program
        self.written_forms: list[tuple[banf.Let, terms.Term]] = []

    def atom(self, term, block):
        location = _location(term)
        match term:
            case terms.ByteArray(value=value, form=form):
                _check_data_form(form, location, 'Byte array')
                return banf.Const(value, form, location)
            case terms.Formed(term=terms.ByteArray(value=value, form=terms.Void), form=form):
                _check_data_form(form, location, 'Byte array')
                return banf.Const(value, form, location)
            case terms.Formed():
                raise TranslationError('Only a byte array without a form can be given a form.', location)
            case terms.BruijnIndex():
                match block.binder(term):
                    case ('let', name):
                        return banf.Var(name, location)
                    case str() as name:
                        raise _not_a_value(name, location)
            case terms.Project(struct=struct, label=label) if block.binder(struct) == ARGS:
                if any(param == label for param, _ in block.params):
                    return banf.Var(label, location)
                raise TranslationError(f'Block has no param {label!r}.', location)
        raise TranslationError('Expected an atom: a byte array, a let name, or args.label.', location)

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
                atoms = [banf.Var(label, location) for label in got]
            case terms.Struct(fields=fields):
                got = [f.label for f in fields]
                atoms = [self.atom(f.value, block) for f in fields]
            case _:
                raise TranslationError(f'The argument to {what} must be a struct literal or the block param.', location)
        if got != expected:
            raise TranslationError(f'{what} takes {{{", ".join(expected)}}}, got {{{", ".join(got)}}}.', location)
        return atoms

    def op(self, term, block):
        location = _location(term)
        program = self.program
        match term:
            case terms.Apply(function=terms.Project(struct=struct, label=name), argument=arg):
                base = block.binder(struct)
                if base == PRIM:
                    if name not in banf_prim.PRIMS:
                        raise TranslationError(f'Unknown prim op {name!r}.', location)
                    params = banf_prim.PRIMS[name].params
                    return banf.PrimCall(name, self.args(arg, params, f'prim.{name}', block), location)
                if base == DEFS:
                    if name not in program.functions:
                        raise TranslationError(f'Unknown definition {name!r}.', location)
                    params = program.functions[name].params
                    return banf.Call(name, self.args(arg, params, f'defs.{name}', block), location)
                if base == DECLS:
                    binding = program.imports.get(name)
                    if binding is None:
                        raise TranslationError(f'Unknown import {name!r}.', location)
                    if isinstance(binding, banf.Data):
                        raise TranslationError(f'Imported data {name!r} cannot be applied.', location)
                    return banf.Call(name, self.args(arg, binding.params, f'decls.{name}', block), location)
                if base == BLOCKS:
                    raise TranslationError('A jump must be in tail position.', location)
            case terms.Struct(fields=fields):
                labels = [f.label for f in fields]
                if len(set(labels)) != len(labels):
                    raise TranslationError('Duplicate field labels.', location)
                return banf.MakeStruct([(f.label, self.atom(f.value, block)) for f in fields], location)
            case terms.Project(struct=struct, label=name) if block.binder(struct) == DECLS:
                binding = program.imports.get(name)
                if binding is None:
                    raise TranslationError(f'Unknown import {name!r}.', location)
                if isinstance(binding, banf.Signature):
                    raise TranslationError(f'Imported function {name!r} must be applied.', location)
                return banf.GetData(name, location)
            case terms.Project(struct=struct, label=name) if block.binder(struct) in (DEFS, PRIM):
                raise TranslationError(f'{block.binder(struct)}.{name} must be applied.', location)
            case terms.Project(struct=struct) if block.binder(struct) == ARGS:
                self.atom(term, block)
            case terms.Project(struct=struct, label=label):
                return banf.GetField(self.atom(struct, block), label, location)
            case terms.BruijnIndex() if isinstance(name := block.binder(term), str):
                raise _not_a_value(name, location)
            case terms.If():
                raise TranslationError('An if must be in tail position.', location)
        if self.is_atom(term, block):
            raise TranslationError("A let's value must be an op, not an atom.", location)
        raise TranslationError(
            'Expected an op: prim.op {...}, defs.f {...}, decls.f {...}, a struct or a projection.', location
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
                    let = banf.Let(name, self.op(value, block), location)
                    if form is not terms.Void:
                        self.written_forms.append((let, form))
                    block.lets.append(let)
                    term = rest
                    continue
                case terms.If(condition=condition, then_clause=then_clause, else_clause=else_clause):
                    atom = self.atom(condition, block)
                    then_jump = self.jump(then_clause, block)
                    else_jump = self.jump(else_clause, block)
                    if then_jump is None or else_jump is None:
                        raise TranslationError(
                            'Both branches of an if must be jumps, such as blocks.then0 {}.', location
                        )
                    if then_jump[0] == else_jump[0]:
                        raise TranslationError('Both branches of an if jump to the same block.', location)
                    return banf.Branch(atom, *then_jump, *else_jump, location)
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


def _known_return_form(block, module):
    """The form of the block's returned atom, or None if it depends on a return form not inferred yet."""
    if not isinstance(block.terminator, banf.Return):
        return None
    forms = dict(block.params)
    for let in block.lets:
        try:
            form = banf.form_of(let.value, forms, module)
        except banf.FormError:
            continue
        if form is not terms.Void:
            forms[let.name] = form
    try:
        return banf.atom_form(block.terminator.value, forms)
    except banf.FormError:
        return None


def _infer_return_forms(module, functions):
    """Iterates return forms to a fixed point, so a recursive call resolves through another block's return."""
    changed = True
    while changed:
        changed = False
        for function in functions:
            if function.return_form is not terms.Void:
                continue
            for block in function.blocks:
                form = _known_return_form(block, module)
                if form is not None:
                    function.return_form = form
                    changed = True
                    break
    for function in functions:
        if function.return_form is terms.Void:
            raise TranslationError(f'Cannot infer the return form of {function.name!r}.', function.location)


def _check_written_forms(module, written_forms):
    pending = {id(let): (let, form) for let, form in written_forms}
    for function in (b for b in module.bindings if isinstance(b, banf.Function)):
        for block in function.blocks:
            forms = dict(block.params)
            for let in block.lets:
                forms[let.name] = banf.form_of(let.value, forms, module)
                if id(let) in pending and forms[let.name] != pending[id(let)][1]:
                    written = banf.show_form(pending[id(let)][1])
                    raise TranslationError(
                        f'Let {let.name!r} is written as {written}, but its op gives {banf.show_form(forms[let.name])}.',
                        let.location,
                    )


def shape(term: syntax.Term) -> syntax.Term:
    """Resolves names, reduces to BANF's shape and renames binders."""
    try:
        return banf_rename.rename(banf_reduce.shape(bruijn.resolve(term)))
    except bruijn.BruijnError as error:
        raise TranslationError(error.message, error.location) from error


def convert(term: syntax.Term) -> banf.Module:
    """Reads a shaped term into BANF."""
    decls_form, decls_location, defs_struct = _unwrap(term)
    imports = _imports(decls_form, decls_location)
    headers = []
    for field in defs_struct.fields:
        if any(header[0].name == field.label for header in headers):
            raise TranslationError(f'Duplicate definition {field.label!r}.', field.location)
        headers.append(_function_header(field, imports))
    functions = [header[0] for header in headers]
    program = _Program(imports, {function.name: function for function in functions})
    translator = _Translator(program)
    for header in headers:
        translator.function(*header)
    module = banf.Module([*imports.values(), *functions])
    try:
        _infer_return_forms(module, functions)
        _check_written_forms(module, translator.written_forms)
        banf.verify(module)
    except banf.FormError as error:
        raise TranslationError(error.message, error.location) from error
    return module


def translate(term: syntax.Term) -> banf.Module:
    return convert(shape(term))
