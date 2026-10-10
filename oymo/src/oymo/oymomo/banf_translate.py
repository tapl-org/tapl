# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Translates oymomo terms into BANF.

`shape` resolves names, reduces the term to BANF's shape (`banf_reduce`) and renames its binders
(`banf_rename`). `convert` then reads the shaped term into BANF; it does no normalization.
"""

from dataclasses import dataclass, replace

from oymo.core import syntax
from oymo.oymomo import banf_prim, banf_reduce, banf_rename, bruijn, terms
from oymo.oymomo import banf_terms as banf
from oymo.oymomo.banf_rename import ARGS, BLOCKS, MODULE, PRIM


class TranslationError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


def _location(term):
    return getattr(term, 'location', None)


def _check_data_form(form, location, what):
    """A data form is a named form or a struct of data forms: no Empty parts, no function forms,
    and no other terms."""
    if isinstance(form, terms.FunctionForm):
        raise TranslationError(f'{what}: function forms nested inside other forms are not supported.', location)
    if isinstance(form, terms.Struct):
        labels = [f.label for f in form.fields]
        if len(set(labels)) != len(labels):
            raise TranslationError(f'{what}: duplicate field labels in {banf.show_form(form)}.', location)
        for f in form.fields:
            _check_data_form(f.value, location, what)
    elif form is terms.Empty:
        raise TranslationError(f'{what}: form must be written.', location)
    elif terms.form_to_name(form) is None:
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
        """For a BruijnIndex in the block body: ('let', name), or one of ARGS, BLOCKS, MODULE, PRIM.

        Above the body, from the inside out, are the lets so far, then args, blocks, module, prim.
        None for anything else.
        """
        if not isinstance(term, terms.BruijnIndex):
            return None
        k = len(self.lets)
        if term.index < k:
            return ('let', self.lets[k - 1 - term.index].name)
        fixed = (ARGS, BLOCKS, MODULE, PRIM)
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
                param_name=module_name, param_form=module_form, body=terms.Struct() as body
            ) as module_lambda,
        ) if (prim_name, module_name) == (PRIM, MODULE):
            if not isinstance(module_form, terms.Struct):
                raise TranslationError(
                    'The module binder needs a struct form, such as module: {}.', module_lambda.location
                )
            return module_form, module_lambda.location, body
    raise TranslationError('Expected a program of the shape prim -> module: {...} -> {...}.', _location(term))


def _declarations(module_form, location):
    """One binding per declared symbol, in declaration order. A function declared as `=> R` is a
    `banf.Function` without blocks yet; its definition gives them."""
    declarations = {}
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
            _check_data_form(param, decl_location, what)
            params = [(f.label, f.value) for f in param.fields]
            declarations[label] = banf.Signature(label, params, result, decl_location)
        else:
            _check_data_form(form, decl_location, what)
            declarations[label] = banf.Data(label, form, decl_location)
    return declarations


def _check_definition(field, declarations):
    """The declaration a body field defines; it must be a function declared as `=> R`."""
    name = field.label
    declaration = declarations.get(name)
    match declaration:
        case None:
            raise TranslationError(f'{name!r} is defined but not declared.', field.location)
        case banf.Signature():
            raise TranslationError(
                f'{name!r} declares its params; a definition takes them from its entry block.', field.location
            )
        case banf.Data():
            raise TranslationError(f'{name!r} is declared as data; data cannot be defined yet.', field.location)
    return declaration


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
            case terms.Project(struct=struct, label=label) if block.binder(struct) == ARGS:
                if any(param == label for param, _ in block.params):
                    return banf.Var(label, location=location)
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
                atoms = [banf.Var(label, location=location) for label in got]
            case terms.Struct(fields=fields):
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

    def op(self, term, block):
        location = _location(term)
        match term:
            case terms.Apply(function=terms.Project(struct=struct, label=name), argument=arg):
                base = block.binder(struct)
                if base == PRIM:
                    if name not in banf_prim.PRIMS:
                        raise TranslationError(f'Unknown prim op {name!r}.', location)
                    params = banf_prim.PRIMS[name].params
                    return banf.PrimCall(name, self.args(arg, params, f'prim.{name}', block), location)
                if base == MODULE:
                    # An imported function's params are declared; a defined one's come from its entry block.
                    binding = self.symbol(name, location)
                    if isinstance(binding, banf.Data):
                        raise TranslationError(f'module.{name} is data, so it cannot be applied.', location)
                    return banf.Call(name, self.args(arg, binding.params, f'module.{name}', block), location)
                if base == BLOCKS:
                    raise TranslationError('A jump must be in tail position.', location)
            case terms.Struct(fields=fields):
                labels = [f.label for f in fields]
                if len(set(labels)) != len(labels):
                    raise TranslationError('Duplicate field labels.', location)
                return banf.MakeStruct([(f.label, self.atom(f.value, block)) for f in fields], location)
            case terms.Project(struct=struct, label=name) if block.binder(struct) == MODULE:
                if isinstance(self.symbol(name, location), banf.Data):
                    return banf.GetData(name, location)
                raise TranslationError(f'module.{name} must be applied.', location)
            case terms.Project(struct=struct, label=name) if block.binder(struct) == PRIM:
                raise TranslationError(f'prim.{name} must be applied.', location)
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
            'Expected an op: prim.op {...}, module.f {...}, module.data, a struct or a projection.', location
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


def shape(term: syntax.Term) -> syntax.Term:
    """Resolves names, reduces to BANF's shape and renames binders."""
    try:
        return banf_rename.rename(banf_reduce.shape(bruijn.resolve(term)))
    except bruijn.BruijnError as error:
        raise TranslationError(error.message, error.location) from error


def convert(term: syntax.Term) -> banf.Module:
    """Reads a shaped term into BANF."""
    module_form, module_location, body = _unwrap(term)
    declarations = _declarations(module_form, module_location)
    definitions = []
    for field in body.fields:
        if any(function.name == field.label for function, _ in definitions):
            raise TranslationError(f'Duplicate definition {field.label!r}.', field.location)
        function = _check_definition(field, declarations)
        function.blocks, block_fields = _blocks(field)
        function.location = field.location
        definitions.append((function, block_fields))
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
