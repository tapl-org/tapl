# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, cast, override

from tapl_lang.core import syntax, tapl_error
from tapl_lang.lib import untyped_terms


@dataclass
class ModeTerm(syntax.Term):
    name: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: self)

    def __repr__(self) -> str:
        return self.name


MODE_EVALUATE = ModeTerm(name='MODE_EVALUATE')
MODE_TYPECHECK = ModeTerm(name='MODE_TYPECHECK')
MODE_SAFE = syntax.Layers(layers=[MODE_EVALUATE, MODE_TYPECHECK])
SAFE_LAYER_COUNT = len(MODE_SAFE.layers)


# FIXME: Find different names fro typed terms to distinguish from untyped terms
@dataclass
class Name(syntax.Term):
    location: syntax.Location
    id: str
    ctx: str
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Name(location=self.location, id=self.id, ctx=self.ctx, mode=layer(self.mode)))

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.Name(location=self.location, id=self.id, ctx=self.ctx)
        if self.mode is MODE_TYPECHECK:
            return untyped_terms.Attribute(
                location=self.location,
                value=untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                attr=self.id,
                ctx=self.ctx,
            )
        raise tapl_error.UnhandledError


@dataclass
class Attribute(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    attr: str
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Attribute(location=self.location, value=layer(self.value), attr=self.attr, ctx=self.ctx)
        )

    # TODO: Attribute must have a type layer to check attribute exists or not. find a test case first. should have? maybe scope should support this.
    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Attribute(location=self.location, value=self.value, attr=self.attr, ctx=self.ctx)


@dataclass
class Select(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    names: list[str]
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Select(
                location=self.location,
                value=layer(self.value),
                names=self.names,
                ctx=self.ctx,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if not self.names:
            return syntax.ErrorTerm(location=self.location, message='At least one name is required to select a path.')
        value = self.value
        for i in range(len(self.names) - 1):
            value = Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


@dataclass
class Path(syntax.Term):
    location: syntax.Location
    names: list[str]
    ctx: str
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Path(location=self.location, names=self.names, ctx=self.ctx, mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if len(self.names) <= 1:
            return syntax.ErrorTerm(location=self.location, message='At least two names are required to create a path.')
        value: syntax.Term = Name(location=self.location, id=self.names[0], ctx='load', mode=self.mode)
        for i in range(1, len(self.names) - 1):
            value = Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


@dataclass
class Literal(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def typeit(self, ls: syntax.LayerSeparator, value: Any, type_id: str) -> list[syntax.Term]:
        if ls.layer_count != SAFE_LAYER_COUNT:
            raise ValueError('NoneLiteral must be separated in 2 layers')
        return [
            untyped_terms.Constant(location=self.location, value=value),
            Name(location=self.location, id=type_id, ctx='load', mode=MODE_TYPECHECK),
        ]


@dataclass
class NoneLiteral(Literal):
    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=None, type_id='NoneType')


@dataclass
class BooleanLiteral(Literal):
    value: bool

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Bool')


@dataclass
class IntegerLiteral(Literal):
    value: int

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Int')


@dataclass
class FloatLiteral(Literal):
    value: float

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Float')


@dataclass
class StringLiteral(Literal):
    value: str

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Str')


@dataclass
class ListIntLiteral(Literal):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: ListIntLiteral(location=self.location))

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.List(location=self.location, elts=[], ctx='load')


@dataclass
class UnaryOp(syntax.Term):
    location: syntax.Location
    op: str
    operand: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: UnaryOp(location=self.location, op=self.op, operand=layer(self.operand)))

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.UnaryOp(location=self.location, op=self.op, operand=self.operand)


@dataclass
class BoolNot(syntax.Term):
    location: syntax.Location
    operand: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolNot(location=self.location, operand=layer(self.operand), mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.UnaryOp(location=self.location, op='not', operand=self.operand)
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            return Name(location=self.location, id='Bool', ctx='load', mode=MODE_TYPECHECK)
        raise tapl_error.UnhandledError


@dataclass
class BoolOp(syntax.Term):
    location: syntax.Location
    op: str
    values: list[syntax.Term]
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolOp(
                location=self.location, op=self.op, values=[layer(v) for v in self.values], mode=layer(self.mode)
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.BoolOp(location=self.location, op=self.op, values=self.values)
        if self.mode is MODE_TYPECHECK:
            return untyped_terms.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_union'], ctx='load', mode=self.mode),
                args=self.values,
                keywords=[],
            )
        raise tapl_error.UnhandledError


@dataclass
class BinOp(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    op: str
    right: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield self.right

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BinOp(location=self.location, left=layer(self.left), op=self.op, right=layer(self.right))
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.BinOp(location=self.location, left=self.left, op=self.op, right=self.right)


@dataclass
class Compare(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    ops: list[str]
    comparators: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield from self.comparators

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Compare(
                location=self.location,
                left=layer(self.left),
                ops=self.ops,
                comparators=[layer(v) for v in self.comparators],
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Compare(location=self.location, left=self.left, ops=self.ops, comparators=self.comparators)


@dataclass
class Call(syntax.Term):
    location: syntax.Location
    func: syntax.Term
    args: list[syntax.Term]
    keywords: list[tuple[str, syntax.Term]]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.func
        yield from self.args
        yield from (v for _, v in self.keywords)

    @override
    def separate(self, ls) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Call(
                location=self.location,
                func=layer(self.func),
                args=[layer(v) for v in self.args],
                keywords=[(k, layer(v)) for k, v in self.keywords],
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Call(location=self.location, func=self.func, args=self.args, keywords=self.keywords)


@dataclass
class Assign(syntax.Term):
    location: syntax.Location
    targets: list[syntax.Term]
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.targets
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Assign(
                location=self.location, targets=[layer(t) for t in self.targets], value=layer(self.value)
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Assign(
            location=self.location,
            targets=self.targets,
            value=self.value,
        )


@dataclass
class Return(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Return(location=self.location, value=layer(self.value), mode=layer(self.mode)))

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.Return(location=self.location, value=self.value)
        if self.mode is MODE_TYPECHECK:
            call = untyped_terms.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'add_return_type'], ctx='load', mode=self.mode),
                args=[
                    untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                    self.value,
                ],
                keywords=[],
            )
            return untyped_terms.Expr(location=self.location, value=call)
        raise tapl_error.UnhandledError


@dataclass
class Expr(syntax.Term):
    location: syntax.Location
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Expr(location=self.location, value=layer(self.value)))

    @override
    def unfold(self):
        return untyped_terms.Expr(location=self.location, value=self.value)


# TODO: Remove Absence, and implement it differently according to ground rules.
@dataclass
class Absence(syntax.Term):
    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Absence())


@dataclass
class Parameter(syntax.Term):
    location: syntax.Location
    name: str
    type_: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.type_
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Parameter(
                location=self.location, name=self.name, type_=layer(self.type_), mode=layer(self.mode)
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_TYPECHECK:
            return self.type_
        raise tapl_error.UnhandledError


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    parameters: list[syntax.Term]
    body: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.parameters
        yield self.body
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                parameters=[layer(p) for p in self.parameters],
                body=layer(self.body),
                mode=layer(self.mode),
            )
        )

    def unfold_evaluate(self) -> syntax.Term:
        if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Absence when generating function in evaluate mode.')

        return untyped_terms.FunctionDef(
            location=self.location,
            name=self.name,
            posonlyargs=[],
            args=[cast(Parameter, p).name for p in self.parameters],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=self.body,
            decorator_list=[],
        )

    def unfold_typecheck_main(self) -> syntax.Term:
        def nested_scope(nested_term: syntax.Term) -> syntax.Term:
            return syntax.BackendSettingTerm(
                backend_setting_changer=syntax.BackendSettingChanger(
                    lambda setting: setting.clone(scope_level=setting.scope_level + 1)
                ),
                term=nested_term,
            )

        param_names = [cast(Parameter, p).name for p in self.parameters]

        keywords: list[tuple[str, syntax.Term]] = []
        keywords.append(
            (
                'parent__tapl',
                untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
            )
        )
        keywords.extend((name, untyped_terms.Name(location=self.location, id=name, ctx='load')) for name in param_names)
        new_scope = Assign(
            location=self.location,
            targets=[
                nested_scope(
                    untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                )
            ],
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_scope'], ctx='load', mode=self.mode),
                args=[],
                keywords=keywords,
            ),
        )

        return_type = untyped_terms.Return(
            location=self.location,
            value=untyped_terms.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'get_return_type'], ctx='load', mode=self.mode),
                args=[untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                keywords=[],
            ),
        )

        return untyped_terms.FunctionDef(
            location=self.location,
            name=self.name,
            posonlyargs=[],
            args=param_names,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=syntax.TermList(terms=[new_scope, nested_scope(self.body), nested_scope(return_type)]),
            decorator_list=[],
        )

    def unfold_typecheck_type(self) -> syntax.Term:
        if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Absence when generating function type in type-check mode.'
            )

        return Assign(
            location=self.location,
            targets=[Name(location=self.location, id=self.name, ctx='store', mode=self.mode)],
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_function'], ctx='load', mode=self.mode),
                args=[
                    untyped_terms.List(
                        location=self.location,
                        elts=[cast(Parameter, p).type_ for p in self.parameters],
                        ctx='load',
                    ),
                    Call(
                        location=self.location,
                        func=untyped_terms.Name(location=self.location, id=self.name, ctx='load'),
                        args=[cast(Parameter, p).type_ for p in self.parameters],
                        keywords=[],
                    ),
                ],
                keywords=[],
            ),
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.unfold_evaluate()
        if self.mode is MODE_TYPECHECK:
            return syntax.TermList(terms=[self.unfold_typecheck_main(), self.unfold_typecheck_type()])
        raise tapl_error.UnhandledError


@dataclass
class Alias:
    name: str
    asname: str | None = None


@dataclass
class Import(syntax.Term):
    location: syntax.Location
    names: list[Alias]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: Import(location=self.location, names=[Alias(name=n.name, asname=n.asname) for n in self.names])
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Import(
            location=self.location, names=[untyped_terms.Alias(name=n.name, asname=n.asname) for n in self.names]
        )


@dataclass
class ImportFrom(syntax.Term):
    location: syntax.Location
    module: str | None
    names: list[Alias]
    level: int

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: ImportFrom(
                location=self.location,
                module=self.module,
                names=[Alias(name=n.name, asname=n.asname) for n in self.names],
                level=self.level,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.ImportFrom(
            location=self.location,
            module=self.module,
            names=[untyped_terms.Alias(name=n.name, asname=n.asname) for n in self.names],
            level=self.level,
        )


@dataclass
class BranchTyping(syntax.Term):
    location: syntax.Location
    branches: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.branches

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: BranchTyping(location=self.location, branches=[layer(b) for b in self.branches]))

    @override
    def unfold(self) -> syntax.Term:
        def nested_scope(inner_term: syntax.Term) -> syntax.Term:
            return syntax.BackendSettingTerm(
                backend_setting_changer=syntax.BackendSettingChanger(
                    lambda setting: setting.clone(scope_level=setting.scope_level + 1)
                ),
                term=inner_term,
            )

        def new_scope() -> syntax.Term:
            return Assign(
                location=self.location,
                targets=[
                    nested_scope(
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='store')
                    )
                ],
                value=untyped_terms.Call(
                    location=self.location,
                    func=Path(
                        location=self.location,
                        names=['api__tapl', 'fork_scope'],
                        ctx='load',
                        mode=MODE_TYPECHECK,
                    ),
                    args=[
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.forker_name, ctx='load')
                    ],
                    keywords=[],
                ),
            )

        body: list[syntax.Term] = []
        for b in self.branches:
            body.append(new_scope())
            body.append(nested_scope(b))

        return untyped_terms.With(
            location=self.location,
            items=[
                untyped_terms.WithItem(
                    context_expr=Call(
                        location=self.location,
                        func=Path(
                            location=self.location,
                            names=['api__tapl', 'scope_forker'],
                            ctx='load',
                            mode=MODE_TYPECHECK,
                        ),
                        args=[
                            untyped_terms.Name(
                                location=self.location, id=lambda setting: setting.scope_name, ctx='load'
                            )
                        ],
                        keywords=[],
                    ),
                    optional_vars=untyped_terms.Name(
                        location=self.location, id=lambda setting: setting.forker_name, ctx='store'
                    ),
                )
            ],
            body=syntax.TermList(terms=body),
        )


@dataclass
class If(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None  # FIXME: Make non none
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        true_side = syntax.TermList(terms=[Expr(location=self.location, value=self.test), self.body])
        false_side = self.orelse if self.orelse is not None else syntax.TermList(terms=[])
        return BranchTyping(location=self.location, branches=[true_side, false_side])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class Else(syntax.SiblingTerm):
    location: syntax.Location
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body

    @override
    def integrate_into(self, previous_siblings: list[syntax.Term]) -> None:
        term = previous_siblings[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, If):
            error = syntax.ErrorTerm('Else can only be integrated into If.' + repr(term), location=self.location)
            previous_siblings.append(error)
        elif term.orelse is not None:
            error = syntax.ErrorTerm('An If statement can only have one Else clause.', location=self.location)
            previous_siblings.append(error)
        else:
            term.orelse = self.body


@dataclass
class While(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None  # FIXME: Make non none
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: While(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.While(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        return If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse,
            mode=self.mode,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class For(syntax.Term):
    location: syntax.Location
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None  # FIXME: Make non none
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.iter
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: For(
                location=self.location,
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.For(
            location=self.location,
            target=self.target,
            iter=self.iter,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        iterator_type = untyped_terms.Call(
            location=self.location,
            func=untyped_terms.Attribute(location=self.location, value=self.iter, attr='__iter__', ctx='load'),
            args=[],
            keywords=[],
        )
        item_type = untyped_terms.Call(
            location=self.location,
            func=untyped_terms.Attribute(location=self.location, value=iterator_type, attr='__next__', ctx='load'),
            args=[],
            keywords=[],
        )
        assign_target = Assign(
            location=self.location,
            targets=[self.target],
            value=item_type,
        )
        for_branch = syntax.TermList(terms=[assign_target, self.body])
        else_branch = self.orelse if self.orelse is not None else syntax.TermList(terms=[])
        return BranchTyping(
            location=self.location,
            branches=[for_branch, else_branch],
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class Pass(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Pass(location=self.location))

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Pass(location=self.location)


@dataclass
class ClassDef(syntax.Term):
    location: syntax.Location
    name: str
    bases: list[syntax.Term]
    body: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ClassDef(
                location=self.location,
                name=self.name,
                bases=[layer(b) for b in self.bases],
                body=layer(self.body),
                mode=layer(self.mode),
            )
        )

    def _class_name(self) -> str:
        return f'{self.name}_'

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.ClassDef(
            location=self.location,
            name=self._class_name(),
            bases=self.bases,
            keywords=[],
            body=[self.body],
            decorator_list=[],
        )

    def codegen_typecheck(self) -> syntax.Term:
        instance_name = self.name
        class_name = self._class_name()
        body = []
        methods: list[FunctionDef] = []
        constructor_args = []
        for item in self.body.children():
            if isinstance(item, FunctionDef):
                if item.name == '__init__':
                    constructor_args = item.parameters[1:]
                else:
                    methods.append(item)
                body.append(item.unfold_typecheck_main())
            else:
                body.append(item)
        class_stmt = untyped_terms.ClassDef(
            location=self.location,
            name=class_name,
            bases=self.bases,
            keywords=[],
            body=body,
            decorator_list=[],
        )

        method_types: list[syntax.Term] = []
        for method in methods:
            # The first parameter is the instance itself, so we can set it to the instance type.
            if not (
                len(method.parameters) >= 1
                and isinstance(method.parameters[0], Parameter)
                and isinstance(method.parameters[0].type_, Absence)
            ):
                raise tapl_error.TaplError(
                    f'First parameter of method {method.name} in class {class_name} must be self with no type annotation.'
                )
            tail_args = method.parameters[1:]
            method_types.append(
                untyped_terms.Tuple(
                    location=self.location,
                    elts=[
                        untyped_terms.Constant(location=self.location, value=method.name),
                        untyped_terms.List(location=self.location, elts=tail_args, ctx='load'),
                    ],
                    ctx='load',
                )
            )

        create_class = untyped_terms.Assign(
            location=self.location,
            targets=[
                untyped_terms.Tuple(
                    location=self.location,
                    elts=[
                        Name(location=self.location, id=instance_name, ctx='store', mode=self.mode),
                        Name(location=self.location, id=class_name, ctx='store', mode=self.mode),
                    ],
                    ctx='store',
                )
            ],
            value=untyped_terms.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_class'], ctx='load', mode=self.mode),
                args=[],
                keywords=[
                    ('cls', untyped_terms.Name(location=self.location, id=class_name, ctx='load')),
                    ('init_args', untyped_terms.List(location=self.location, elts=constructor_args, ctx='load')),
                    ('methods', untyped_terms.List(location=self.location, elts=method_types, ctx='load')),
                ],
            ),
        )

        return syntax.TermList(terms=[class_stmt, create_class])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError
