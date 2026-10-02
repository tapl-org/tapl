# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Translates oymomo terms that are already in BANF's shape into BANF. Does no normalization."""

from dataclasses import dataclass

from oymo.core import syntax
from oymo.oymomo import banf_prim, terms
from oymo.oymomo import banf_terms as banf
from oymo.oymomo.grammar import UNKNOWN_FORM


class TranslationError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


def _location(term):
    return getattr(term, 'location', None)


def _check_data_form(form, location, what):
    """A data form has no unknown parts and no function forms."""
    match form:
        case terms.FunctionForm():
            raise TranslationError(f'{what}: function forms nested inside other forms are not supported.', location)
        case terms.StructForm(fields=fields):
            labels = [label for label, _ in fields]
            if len(set(labels)) != len(labels):
                raise TranslationError(f'{what}: duplicate field labels in {banf.show_form(form)}.', location)
            for _, field_form in fields:
                _check_data_form(field_form, location, what)
        case str() if form == UNKNOWN_FORM:
            raise TranslationError(f'{what}: form must be known.', location)


@dataclass
class _Program:
    prim: str
    decls: str
    defs: str
    imports: dict[str, banf.Signature | banf.Data]
    functions: dict[str, banf.Function]


@dataclass
class _Block:
    """What the body matcher knows about the block it is in."""

    function: banf.Function
    blocks_binder: str
    args_binder: str
    params: list[tuple[str, terms.Form]]
    lets: set[str]


def _unwrap(term):
    match term:
        case syntax.ErrorTerm(message=message):
            raise TranslationError(message, term.location)
        case terms.Lambda(
            param_name=prim,
            body=terms.Lambda(
                param_name=decls,
                param_form=decls_form,
                body=terms.Lambda(param_name=defs, body=terms.Struct() as defs_struct),
            ) as decls_lambda,
        ):
            if not isinstance(decls_form, terms.StructForm):
                raise TranslationError(
                    'The decls binder needs a struct form, such as decls: {}.', decls_lambda.location
                )
            if len({prim, decls, defs}) != len((prim, decls, defs)):
                raise TranslationError('The prim, decls and defs binders must have different names.', term.location)
            return prim, decls, decls_form, decls_lambda.location, defs, defs_struct
    raise TranslationError('Expected a program of the shape prim -> decls: {...} -> defs -> {...}.', _location(term))


def _imports(decls_form, location):
    imports = {}
    for label, form in decls_form.fields:
        if label in imports:
            raise TranslationError(f'Duplicate import {label!r}.', location)
        what = f'Import {label!r}'
        if isinstance(form, terms.FunctionForm):
            if not isinstance(form.param, terms.StructForm):
                raise TranslationError(f'{what}: a function form needs a struct form as its param.', location)
            _check_data_form(form.param, location, what)
            _check_data_form(form.result, location, what)
            imports[label] = banf.Signature(label, list(form.param.fields), form.result, location)
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
        case terms.Lambda(param_name=blocks_binder, body=terms.Struct(fields=block_fields)) if block_fields:
            pass
        case _:
            raise TranslationError(
                f'Definition {name!r} must be a struct of blocks, such as f -> {{entry = args:{{}} -> ...}}.',
                _location(field.value),
            )
    blocks = []
    for block_field in block_fields:
        match block_field.value:
            case terms.Lambda(param_form=terms.StructForm(fields=params) as form):
                _check_data_form(form, block_field.location, f'Block {block_field.label!r}')
            case _:
                raise TranslationError(
                    f'Block {block_field.label!r} must be a lambda taking a struct, such as args:{{n: i32}} -> ...',
                    _location(block_field.value),
                )
        if any(block.label == block_field.label for block in blocks):
            raise TranslationError(f'Duplicate block {block_field.label!r}.', block_field.location)
        blocks.append(banf.Block(block_field.label, list(params), [], banf.Return(banf.Var('')), block_field.location))
    return banf.Function(name, UNKNOWN_FORM, blocks, field.location), blocks_binder, block_fields


class _Translator:
    def __init__(self, program: _Program) -> None:
        self.program = program
        self.written_forms: list[tuple[banf.Let, terms.Form]] = []

    def binder_error(self, name, block, location):
        reserved = {self.program.prim, self.program.decls, self.program.defs, block.blocks_binder, block.args_binder}
        if name in reserved:
            return TranslationError(f'{name!r} cannot be used as a value.', location)
        return None

    def atom(self, term, block):
        location = _location(term)
        match term:
            case terms.ByteArray(value=value, form=form):
                _check_data_form(form, location, 'Byte array')
                return banf.Const(value, form, location)
            case terms.Variable(name=name):
                if name in block.lets:
                    return banf.Var(name, location)
                if error := self.binder_error(name, block, location):
                    raise error
                raise TranslationError(f'Unknown name {name!r}.', location)
            case terms.FieldAccess(struct=terms.Variable(name=name), label=label) if name == block.args_binder:
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
            case terms.Variable(name=name) if name == block.args_binder:
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
            case terms.Apply(function=terms.FieldAccess(struct=terms.Variable(name=base), label=name), argument=arg):
                if base == program.prim:
                    if name not in banf_prim.PRIMS:
                        raise TranslationError(f'Unknown prim op {name!r}.', location)
                    params = banf_prim.PRIMS[name].params
                    return banf.PrimCall(name, self.args(arg, params, f'prim.{name}', block), location)
                if base == program.defs:
                    if name not in program.functions:
                        raise TranslationError(f'Unknown definition {name!r}.', location)
                    params = program.functions[name].params
                    return banf.Call(name, self.args(arg, params, f'defs.{name}', block), location)
                if base == program.decls:
                    binding = program.imports.get(name)
                    if binding is None:
                        raise TranslationError(f'Unknown import {name!r}.', location)
                    if isinstance(binding, banf.Data):
                        raise TranslationError(f'Imported data {name!r} cannot be applied.', location)
                    return banf.Call(name, self.args(arg, binding.params, f'decls.{name}', block), location)
                if base == block.blocks_binder:
                    raise TranslationError('A jump must be in tail position.', location)
            case terms.Struct(fields=fields):
                labels = [f.label for f in fields]
                if len(set(labels)) != len(labels):
                    raise TranslationError('Duplicate field labels.', location)
                return banf.MakeStruct([(f.label, self.atom(f.value, block)) for f in fields], location)
            case terms.FieldAccess(struct=terms.Variable(name=base), label=name) if base == program.decls:
                binding = program.imports.get(name)
                if binding is None:
                    raise TranslationError(f'Unknown import {name!r}.', location)
                if isinstance(binding, banf.Signature):
                    raise TranslationError(f'Imported function {name!r} must be applied.', location)
                return banf.GetData(name, location)
            case terms.FieldAccess(struct=terms.Variable(name=base), label=name) if base in (
                program.defs,
                program.prim,
            ):
                raise TranslationError(f'{base}.{name} must be applied.', location)
            case terms.FieldAccess(struct=terms.Variable(name=base)) if base == block.args_binder:
                self.atom(term, block)
            case terms.FieldAccess(struct=struct, label=label):
                return banf.GetField(self.atom(struct, block), label, location)
            case terms.Variable(name=name) if error := self.binder_error(name, block, location):
                raise error
            case terms.If():
                raise TranslationError('An if must be in tail position.', location)
            case terms.Fix():
                raise TranslationError('fix is not supported; recursion goes through defs.', location)
            case terms.Lambda():
                raise TranslationError('Only block and let lambdas are supported.', location)
        if self.is_atom(term, block):
            raise TranslationError("A let's value must be an op, not an atom.", location)
        raise TranslationError(
            'Expected an op: prim.op {...}, defs.f {...}, decls.f {...}, a struct or a field access.', location
        )

    def jump(self, term, block):
        location = _location(term)
        match term:
            case terms.Apply(
                function=terms.FieldAccess(struct=terms.Variable(name=base), label=label), argument=arg
            ) if base == block.blocks_binder:
                targets = {b.label: b for b in block.function.blocks}
                if label not in targets:
                    raise TranslationError(f'Unknown block {label!r}.', location)
                if label == block.function.blocks[0].label:
                    raise TranslationError('Cannot jump to the entry block.', location)
                return label, self.args(arg, targets[label].params, f'Block {label!r}', block)
        return None

    def bind_let(self, name, block, location):
        if name in block.lets:
            raise TranslationError(f'Let {name!r} repeats an earlier let.', location)
        if any(name == param for param, _ in block.params):
            raise TranslationError(f'Let {name!r} repeats a block param label.', location)
        if self.binder_error(name, block, location):
            raise TranslationError(f'Let {name!r} repeats a binder name.', location)
        block.lets.add(name)

    def body(self, term, block):
        lets = []
        while True:
            location = _location(term)
            match term:
                case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=rest), argument=value):
                    op = self.op(value, block)
                    self.bind_let(name, block, location)
                    let = banf.Let(name, op, location)
                    if form != UNKNOWN_FORM:
                        self.written_forms.append((let, form))
                    lets.append(let)
                    term = rest
                    continue
                case terms.If(condition=condition, then_clause=then_clause, else_clause=else_clause):
                    atom = self.atom(condition, block)
                    then_jump = self.jump(then_clause, block)
                    else_jump = self.jump(else_clause, block)
                    if then_jump is None or else_jump is None:
                        raise TranslationError('Both branches of an if must be jumps, such as f.then0 {}.', location)
                    if then_jump[0] == else_jump[0]:
                        raise TranslationError('Both branches of an if jump to the same block.', location)
                    return lets, banf.Branch(atom, *then_jump, *else_jump, location)
            if (jump := self.jump(term, block)) is not None:
                return lets, banf.Jump(*jump, location)
            if self.is_atom(term, block):
                return lets, banf.Return(self.atom(term, block), location)
            if isinstance(term, terms.Apply | terms.Struct | terms.FieldAccess):
                self.op(term, block)
                raise TranslationError(
                    'An op in tail position must be bound by a let, as in (t0 -> t0) (op).', location
                )
            self.atom(term, block)
            raise AssertionError(term)

    def function(self, function, blocks_binder, block_fields):
        for banf_block, block_field in zip(function.blocks, block_fields, strict=True):
            args_binder = block_field.value.param_name
            program = self.program
            if args_binder in {blocks_binder, program.prim, program.decls, program.defs}:
                raise TranslationError(
                    f'Block binder {args_binder!r} repeats an outer binder name.', block_field.value.location
                )
            block = _Block(function, blocks_binder, args_binder, banf_block.params, set())
            banf_block.lets, banf_block.terminator = self.body(block_field.value.body, block)


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
        if form != UNKNOWN_FORM:
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
            if function.return_form != UNKNOWN_FORM:
                continue
            for block in function.blocks:
                form = _known_return_form(block, module)
                if form is not None:
                    function.return_form = form
                    changed = True
                    break
    for function in functions:
        if function.return_form == UNKNOWN_FORM:
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


def translate(term: syntax.Term) -> banf.Module:
    prim, decls, decls_form, decls_location, defs, defs_struct = _unwrap(term)
    imports = _imports(decls_form, decls_location)
    headers = []
    for field in defs_struct.fields:
        if any(header[0].name == field.label for header in headers):
            raise TranslationError(f'Duplicate definition {field.label!r}.', field.location)
        headers.append(_function_header(field, imports))
    functions = [header[0] for header in headers]
    program = _Program(prim, decls, defs, imports, {function.name: function for function in functions})
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
