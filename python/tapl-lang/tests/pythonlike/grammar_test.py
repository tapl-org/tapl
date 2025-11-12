# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.core import parser, syntax
from tapl_lang.lib import terms
from tapl_lang.pythonlike import grammar
from tapl_lang.pythonlike import rule_names as rn


def parse_expr(text: str, start_rule: str, *, mode: syntax.Term = terms.MODE_SAFE, debug=False) -> syntax.Term:
    return parser.parse_text(
        text,
        grammar=parser.Grammar(grammar.get_grammar().rule_map, start_rule),
        debug=debug,
        context=parser.Context(mode=mode),
    )


def create_loc(start_line: int, start_col: int, end_line: int, end_col: int) -> syntax.Location:
    return syntax.Location(
        start=syntax.Position(line=start_line, column=start_col), end=syntax.Position(line=end_line, column=end_col)
    )


def test_compound_stmt__function_def():
    actual = parse_expr('def add(x: int, y: int) -> int:', rn.COMPOUND_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedFunctionDef(
        location=create_loc(1, 0, 1, 31),
        name='add',
        parameters=[
            terms.Parameter(
                location=create_loc(1, 8, 1, 14),
                name='x',
                type_=syntax.Layers(
                    layers=[
                        syntax.Empty,
                        terms.TypedName(
                            location=create_loc(1, 11, 1, 14), id='int', ctx='load', mode=terms.MODE_TYPECHECK
                        ),
                    ]
                ),
                mode=terms.MODE_EVALUATE,
            ),
            terms.Parameter(
                location=create_loc(1, 15, 1, 22),
                name='y',
                type_=syntax.Layers(
                    layers=[
                        syntax.Empty,
                        terms.TypedName(
                            location=create_loc(1, 19, 1, 22), id='int', ctx='load', mode=terms.MODE_TYPECHECK
                        ),
                    ]
                ),
                mode=terms.MODE_EVALUATE,
            ),
        ],
        return_type=terms.TypedName(location=create_loc(1, 27, 1, 30), id='int', ctx='load', mode=terms.MODE_TYPECHECK),
        body=syntax.TermList(terms=[], is_placeholder=True),
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_assignment__annotated():
    actual = parse_expr('x: int = 42', rn.ASSIGNMENT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedAssign(
        location=create_loc(1, 0, 1, 11),
        target_name=terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='store', mode=terms.MODE_EVALUATE),
        target_type=terms.TypedName(location=create_loc(1, 3, 1, 6), id='int', ctx='load', mode=terms.MODE_TYPECHECK),
        value=terms.IntegerLiteral(location=create_loc(1, 9, 1, 11), value=42),
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_assignment__multi_targets():
    actual = parse_expr('a = b = c = 1', rn.ASSIGNMENT, mode=terms.MODE_EVALUATE)
    expected = terms.Assign(
        location=create_loc(1, 0, 1, 13),
        targets=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='store', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='store', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='store', mode=terms.MODE_EVALUATE),
        ],
        value=terms.IntegerLiteral(location=create_loc(1, 12, 1, 13), value=1),
    )
    assert actual == expected


def test_assignment__no_annotation():
    actual = parse_expr('x = 42', rn.ASSIGNMENT, mode=terms.MODE_EVALUATE)
    expected = terms.Assign(
        location=create_loc(1, 0, 1, 6),
        targets=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='store', mode=terms.MODE_EVALUATE),
        ],
        value=terms.IntegerLiteral(location=create_loc(1, 4, 1, 6), value=42),
    )
    assert actual == expected


def test_simple_stmt__assignment():
    actual = parse_expr('x = 10', rn.SIMPLE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.Assign(
        location=create_loc(1, 0, 1, 6),
        targets=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='store', mode=terms.MODE_EVALUATE),
        ],
        value=terms.IntegerLiteral(location=create_loc(1, 4, 1, 6), value=10),
    )
    assert actual == expected


def test_simple_stmt__star_expressions():
    actual = parse_expr('a, b, c', rn.SIMPLE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.Expr(
        location=create_loc(1, 0, 1, 7),
        value=terms.Tuple(
            location=create_loc(1, 0, 1, 7),
            elements=[
                terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
                terms.TypedName(location=create_loc(1, 3, 1, 4), id='b', ctx='load', mode=terms.MODE_EVALUATE),
                terms.TypedName(location=create_loc(1, 6, 1, 7), id='c', ctx='load', mode=terms.MODE_EVALUATE),
            ],
            ctx='load',
        ),
    )
    assert actual == expected


def test_simple_stmt__return():
    actual = parse_expr('return x + 1', rn.SIMPLE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedReturn(
        location=create_loc(1, 0, 1, 12),
        value=terms.BinOp(
            location=create_loc(1, 6, 1, 12),
            left=terms.TypedName(location=create_loc(1, 7, 1, 8), id='x', ctx='load', mode=terms.MODE_EVALUATE),
            op='+',
            right=terms.IntegerLiteral(location=create_loc(1, 11, 1, 12), value=1),
        ),
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_simple_stmt__import_name():
    actual = parse_expr('import math, sys as system', rn.SIMPLE_STMT)
    expected = terms.Import(
        location=create_loc(1, 0, 1, 26),
        names=[
            terms.Alias(name='math', asname=None),
            terms.Alias(name='sys', asname='system'),
        ],
    )
    assert actual == expected


def test_simple_stmt__raise():
    actual = parse_expr("raise ValueError('Invalid value')", rn.SIMPLE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.Raise(
        location=create_loc(1, 0, 1, 33),
        exception=terms.Call(
            location=create_loc(1, 5, 1, 33),
            func=terms.TypedName(
                location=create_loc(1, 6, 1, 16), id='ValueError', ctx='load', mode=terms.MODE_EVALUATE
            ),
            args=[
                terms.StringLiteral(location=create_loc(1, 17, 1, 32), value='Invalid value'),
            ],
            keywords=[],
        ),
        cause=syntax.Empty,
    )
    assert actual == expected


def test_simple_stmt__pass():
    actual = parse_expr('pass', rn.SIMPLE_STMT)
    expected = terms.Pass(location=create_loc(1, 0, 1, 4))
    assert actual == expected


def test_import_name__single():
    actual = parse_expr('import module_name', rn.IMPORT_NAME)
    expected = terms.Import(
        location=create_loc(1, 0, 1, 18),
        names=[terms.Alias(name='module_name', asname=None)],
    )
    assert actual == expected


def test_import_name__multiple():
    actual = parse_expr('import mod1, mod2 as m2, mod3', rn.IMPORT_NAME)
    expected = terms.Import(
        location=create_loc(1, 0, 1, 29),
        names=[
            terms.Alias(name='mod1', asname=None),
            terms.Alias(name='mod2', asname='m2'),
            terms.Alias(name='mod3', asname=None),
        ],
    )
    assert actual == expected


def test_import_from__path():
    actual = parse_expr('import a.b.c', rn.IMPORT_NAME)
    expected = terms.Import(
        location=create_loc(1, 0, 1, 12),
        names=[terms.Alias(name='a.b.c', asname=None)],
    )
    assert actual == expected


def test_import_from__path_multiple():
    actual = parse_expr('import a.b.c as k, d.e', rn.IMPORT_NAME)
    expected = terms.Import(
        location=create_loc(1, 0, 1, 22),
        names=[
            terms.Alias(name='a.b.c', asname='k'),
            terms.Alias(name='d.e', asname=None),
        ],
    )
    assert actual == expected


def test_raise__expression():
    actual = parse_expr('raise 42', rn.RAISE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.Raise(
        location=create_loc(1, 0, 1, 8),
        exception=terms.IntegerLiteral(location=create_loc(1, 6, 1, 8), value=42),
        cause=syntax.Empty,
    )
    assert actual == expected


def test_raise__no_expression():
    actual = parse_expr('raise', rn.RAISE_STMT)
    expected = terms.Raise(
        location=create_loc(1, 0, 1, 5),
        exception=syntax.Empty,
        cause=syntax.Empty,
    )
    assert actual == expected


def test_star_targets__single():
    actual = parse_expr('variable', rn.STAR_TARGETS, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 8), id='variable', ctx='store', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_star_targets__multi():
    actual = parse_expr('var1, var2, var3', rn.STAR_TARGETS, mode=terms.MODE_EVALUATE)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 16),
        elements=[
            terms.TypedName(location=create_loc(1, 0, 1, 4), id='var1', ctx='store', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 6, 1, 10), id='var2', ctx='store', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 12, 1, 16), id='var3', ctx='store', mode=terms.MODE_EVALUATE),
        ],
        ctx='store',
    )
    assert actual == expected


def tetst_star_target__targt_with_star_atom():
    actual = parse_expr('variable', rn.STAR_TARGET, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 8), id='variable', ctx='store', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_t_lookahead():
    punct = ['(', '[', '.']
    for p in punct:
        actual = parse_expr(p, rn.T_LOOKAHEAD)
        expected = grammar.TokenPunct(location=create_loc(1, 0, 1, 1), value=p)
        assert actual == expected


def test_t_primary__atom_failed():
    actual = parse_expr('variable', rn.T_PRIMARY, mode=terms.MODE_EVALUATE)
    expected = parser.ParseFailed
    assert actual == expected


def test_target_with_star_atom__name():
    actual = parse_expr('my_var', rn.TARGET_WITH_STAR_ATOM, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 6), id='my_var', ctx='store', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_target_with_star_atom__attribute():
    actual = parse_expr('obj.attr', rn.TARGET_WITH_STAR_ATOM, mode=terms.MODE_EVALUATE)
    expected = terms.Attribute(
        location=create_loc(1, 0, 1, 8),
        value=terms.TypedName(location=create_loc(1, 0, 1, 3), id='obj', ctx='load', mode=terms.MODE_EVALUATE),
        attr='attr',
        ctx='store',
    )
    assert actual == expected


def test_target_with_star_atom__attribute_nested():
    actual = parse_expr('obj.sub.attr', rn.TARGET_WITH_STAR_ATOM, mode=terms.MODE_EVALUATE)
    expected = terms.Attribute(
        location=create_loc(1, 0, 1, 12),
        value=terms.Attribute(
            location=create_loc(1, 0, 1, 7),
            value=terms.TypedName(location=create_loc(1, 0, 1, 3), id='obj', ctx='load', mode=terms.MODE_EVALUATE),
            attr='sub',
            ctx='load',
        ),
        attr='attr',
        ctx='store',
    )
    assert actual == expected


def test_target_with_star_atom__subscript():
    actual = parse_expr('d[:-1]', rn.TARGET_WITH_STAR_ATOM, mode=terms.MODE_EVALUATE, debug=True)
    expected = terms.Subscript(
        location=create_loc(1, 0, 1, 6),
        value=terms.TypedName(location=create_loc(1, 0, 1, 1), id='d', ctx='load', mode=terms.MODE_EVALUATE),
        slice=terms.Slice(
            location=create_loc(1, 2, 1, 5),
            lower=syntax.Empty,
            upper=terms.UnaryOp(
                location=create_loc(1, 3, 1, 5),
                op='-',
                operand=terms.IntegerLiteral(location=create_loc(1, 4, 1, 5), value=1),
            ),
            step=syntax.Empty,
        ),
        ctx='load',
    )
    assert actual == expected


def test_target_with_star_atom__subscript_nested():
    actual = parse_expr('matrix[0][1:5]', rn.TARGET_WITH_STAR_ATOM, mode=terms.MODE_EVALUATE)
    expected = terms.Subscript(
        location=create_loc(1, 0, 1, 14),
        value=terms.Subscript(
            location=create_loc(1, 0, 1, 9),
            value=terms.TypedName(location=create_loc(1, 0, 1, 6), id='matrix', ctx='load', mode=terms.MODE_EVALUATE),
            slice=terms.IntegerLiteral(location=create_loc(1, 7, 1, 8), value=0),
            ctx='load',
        ),
        slice=terms.Slice(
            location=create_loc(1, 10, 1, 13),
            lower=terms.IntegerLiteral(location=create_loc(1, 10, 1, 11), value=1),
            upper=terms.IntegerLiteral(location=create_loc(1, 12, 1, 13), value=5),
            step=syntax.Empty,
        ),
        ctx='load',
    )
    assert actual == expected


def test_slices__single():
    actual = parse_expr('a:b', rn.SLICES, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 3),
        lower=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
        upper=terms.TypedName(location=create_loc(1, 2, 1, 3), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        step=syntax.Empty,
    )
    assert actual == expected


def test_slices__single_as_tuple():
    actual = parse_expr('a,', rn.SLICES, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)]
    )
    assert actual == expected


def test_slices__multi():
    actual = parse_expr('x:y, 1:10, ::2', rn.SLICES, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            terms.Slice(
                location=create_loc(1, 0, 1, 3),
                lower=terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='load', mode=terms.MODE_EVALUATE),
                upper=terms.TypedName(location=create_loc(1, 2, 1, 3), id='y', ctx='load', mode=terms.MODE_EVALUATE),
                step=syntax.Empty,
            ),
            terms.Slice(
                location=create_loc(1, 4, 1, 9),
                lower=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
                upper=terms.IntegerLiteral(location=create_loc(1, 7, 1, 9), value=10),
                step=syntax.Empty,
            ),
            terms.Slice(
                location=create_loc(1, 10, 1, 14),
                lower=syntax.Empty,
                upper=syntax.Empty,
                step=terms.IntegerLiteral(location=create_loc(1, 13, 1, 14), value=2),
            ),
        ],
    )
    assert actual == expected


def test_slices__multi_trailing_comma():
    actual = parse_expr('x:y, ::2,', rn.SLICES, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            terms.Slice(
                location=create_loc(1, 0, 1, 3),
                lower=terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='load', mode=terms.MODE_EVALUATE),
                upper=terms.TypedName(location=create_loc(1, 2, 1, 3), id='y', ctx='load', mode=terms.MODE_EVALUATE),
                step=syntax.Empty,
            ),
            terms.Slice(
                location=create_loc(1, 4, 1, 8),
                lower=syntax.Empty,
                upper=syntax.Empty,
                step=terms.IntegerLiteral(location=create_loc(1, 7, 1, 8), value=2),
            ),
        ],
    )
    assert actual == expected


def test_slice__named_expression():
    actual = parse_expr('x := 5', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.NamedExpr(
        location=create_loc(1, 0, 1, 6),
        target=terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='store', mode=terms.MODE_EVALUATE),
        value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=5),
    )
    assert actual == expected


def test_slice__single_expression():
    actual = parse_expr('y + 2', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 5),
        left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='y', ctx='load', mode=terms.MODE_EVALUATE),
        op='+',
        right=terms.IntegerLiteral(location=create_loc(1, 4, 1, 5), value=2),
    )
    assert actual == expected


def test_slice__range_single():
    actual = parse_expr('1:10', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 4),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=terms.IntegerLiteral(location=create_loc(1, 2, 1, 4), value=10),
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_single_no_upper():
    actual = parse_expr('1:', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 2),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=syntax.Empty,
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_single_no_lower():
    actual = parse_expr(':10', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 3),
        lower=syntax.Empty,
        upper=terms.IntegerLiteral(location=create_loc(1, 1, 1, 3), value=10),
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_full():
    actual = parse_expr('1:10:2', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 6),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=terms.IntegerLiteral(location=create_loc(1, 2, 1, 4), value=10),
        step=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=2),
    )
    assert actual == expected


def test_slice__range_no_lower():
    actual = parse_expr(':10:2', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 5),
        lower=syntax.Empty,
        upper=terms.IntegerLiteral(location=create_loc(1, 1, 1, 3), value=10),
        step=terms.IntegerLiteral(location=create_loc(1, 4, 1, 5), value=2),
    )
    assert actual == expected


def test_slice__range_no_upper():
    actual = parse_expr('1::2', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 4),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=syntax.Empty,
        step=terms.IntegerLiteral(location=create_loc(1, 3, 1, 4), value=2),
    )
    assert actual == expected


def test_slice__range_no_step():
    actual = parse_expr('1:10:', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 5),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=terms.IntegerLiteral(location=create_loc(1, 2, 1, 4), value=10),
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_no_lower_upper_step():
    actual = parse_expr('::', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 2),
        lower=syntax.Empty,
        upper=syntax.Empty,
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_no_upper_step():
    actual = parse_expr('1::', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 3),
        lower=terms.IntegerLiteral(location=create_loc(1, 0, 1, 1), value=1),
        upper=syntax.Empty,
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_no_lower_step():
    actual = parse_expr(':10:', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 4),
        lower=syntax.Empty,
        upper=terms.IntegerLiteral(location=create_loc(1, 1, 1, 3), value=10),
        step=syntax.Empty,
    )
    assert actual == expected


def test_slice__range_no_lower_upper():
    actual = parse_expr('::2', rn.SLICE, mode=terms.MODE_EVALUATE)
    expected = terms.Slice(
        location=create_loc(1, 0, 1, 3),
        lower=syntax.Empty,
        upper=syntax.Empty,
        step=terms.IntegerLiteral(location=create_loc(1, 2, 1, 3), value=2),
    )
    assert actual == expected


def test_atom__name():
    actual = parse_expr('variable_name', rn.ATOM, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(
        location=create_loc(1, 0, 1, 13), id='variable_name', ctx='load', mode=terms.MODE_EVALUATE
    )
    assert actual == expected


# TODO: Literal values should take a mode to be used in type layer as a value.
def test_atom__true():
    actual = parse_expr('True', rn.ATOM)
    expected = terms.BooleanLiteral(location=create_loc(1, 0, 1, 4), value=True)
    assert actual == expected


def test_atom__false():
    actual = parse_expr('False', rn.ATOM)
    expected = terms.BooleanLiteral(location=create_loc(1, 0, 1, 5), value=False)
    assert actual == expected


def test_atom__none():
    actual = parse_expr('None', rn.ATOM)
    expected = terms.NoneLiteral(location=create_loc(1, 0, 1, 4))
    assert actual == expected


# TODO: String literal should support double quotes and multi-line strings.
def test_atom__string():
    actual = parse_expr("'hello, world!'", rn.ATOM)
    expected = terms.StringLiteral(location=create_loc(1, 0, 1, 15), value='hello, world!')
    assert actual == expected


def test_atom__number_integer():
    actual = parse_expr('42', rn.ATOM)
    expected = terms.IntegerLiteral(location=create_loc(1, 0, 1, 2), value=42)
    assert actual == expected


def test_atom__number_float():
    actual = parse_expr('3.14', rn.ATOM)
    expected = terms.FloatLiteral(location=create_loc(1, 0, 1, 4), value=3.14)
    assert actual == expected


def test_group__expression():
    actual = parse_expr('(x + 1)', rn.GROUP, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 1, 1, 6),
        left=terms.TypedName(location=create_loc(1, 1, 1, 2), id='x', ctx='load', mode=terms.MODE_EVALUATE),
        op='+',
        right=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
    )
    assert actual == expected


def test_group__named_expression():
    actual = parse_expr('(y := 10)', rn.GROUP, mode=terms.MODE_EVALUATE)
    expected = terms.NamedExpr(
        location=create_loc(1, 1, 1, 8),
        target=terms.TypedName(location=create_loc(1, 1, 1, 2), id='y', ctx='store', mode=terms.MODE_EVALUATE),
        value=terms.IntegerLiteral(location=create_loc(1, 6, 1, 8), value=10),
    )
    assert actual == expected


def test_tuple__empty():
    actual = parse_expr('()', rn.ATOM)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 2),
        elements=[],
        ctx='load',
    )
    assert actual == expected


def test_tuple__single():
    actual = parse_expr('(42,)', rn.ATOM)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 5),
        elements=[
            terms.IntegerLiteral(location=create_loc(1, 1, 1, 3), value=42),
        ],
        ctx='load',
    )
    assert actual == expected


def test_tuple__multi():
    actual = parse_expr("(1, 'two', None)", rn.ATOM)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 16),
        elements=[
            terms.IntegerLiteral(location=create_loc(1, 1, 1, 2), value=1),
            terms.StringLiteral(location=create_loc(1, 4, 1, 9), value='two'),
            terms.NoneLiteral(location=create_loc(1, 11, 1, 15)),
        ],
        ctx='load',
    )
    assert actual == expected


def test_list__empty():
    actual = parse_expr('[]', rn.LIST, mode=terms.MODE_EVALUATE)
    expected = terms.TypedList(
        location=create_loc(1, 0, 1, 2),
        elements=[],
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_list__single():
    actual = parse_expr('[item]', rn.LIST, mode=terms.MODE_EVALUATE)
    expected = terms.TypedList(
        location=create_loc(1, 0, 1, 6),
        elements=[
            terms.TypedName(location=create_loc(1, 1, 1, 5), id='item', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_list__multi():
    actual = parse_expr('[a, b, c]', rn.LIST, mode=terms.MODE_EVALUATE)
    expected = terms.TypedList(
        location=create_loc(1, 0, 1, 9),
        elements=[
            terms.TypedName(location=create_loc(1, 1, 1, 2), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 7, 1, 8), id='c', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_set():
    actual = parse_expr('{x, y, z}', rn.SET, mode=terms.MODE_EVALUATE)
    expected = terms.Set(
        location=create_loc(1, 0, 1, 9),
        elements=[
            terms.TypedName(location=create_loc(1, 1, 1, 2), id='x', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 4, 1, 5), id='y', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 7, 1, 8), id='z', ctx='load', mode=terms.MODE_EVALUATE),
        ],
    )
    assert actual == expected


def test_kvpair():
    actual = parse_expr("'a': 1", rn.KVPAIR, mode=terms.MODE_EVALUATE)
    expected = grammar.KeyValuePair(
        key=terms.StringLiteral(location=create_loc(1, 0, 1, 3), value='a'),
        value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
    )
    assert actual == expected


def test_double_starred_kvpair():
    actual = parse_expr("'a': 1", rn.DOUBLE_STARRED_KVPAIR, mode=terms.MODE_EVALUATE)
    expected = grammar.KeyValuePair(
        key=terms.StringLiteral(location=create_loc(1, 0, 1, 3), value='a'),
        value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
    )
    assert actual == expected


def test_double_starred_kvpair__single():
    actual = parse_expr("'a': 1", rn.DOUBLE_STARRED_KVPAIRS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            grammar.KeyValuePair(
                key=terms.StringLiteral(location=create_loc(1, 0, 1, 3), value='a'),
                value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
            ),
        ],
    )
    assert actual == expected


def test_double_starred_kvpairs__multi():
    actual = parse_expr("'a': 1, 'b': 2", rn.DOUBLE_STARRED_KVPAIRS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            grammar.KeyValuePair(
                key=terms.StringLiteral(location=create_loc(1, 0, 1, 3), value='a'),
                value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
            ),
            grammar.KeyValuePair(
                key=terms.StringLiteral(location=create_loc(1, 8, 1, 11), value='b'),
                value=terms.IntegerLiteral(location=create_loc(1, 13, 1, 14), value=2),
            ),
        ],
    )
    assert actual == expected


def test_double_starred_kvpairs__trailing_comma():
    actual = parse_expr("'a': 1, 'b': 2,", rn.DOUBLE_STARRED_KVPAIRS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            grammar.KeyValuePair(
                key=terms.StringLiteral(location=create_loc(1, 0, 1, 3), value='a'),
                value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 6), value=1),
            ),
            grammar.KeyValuePair(
                key=terms.StringLiteral(location=create_loc(1, 8, 1, 11), value='b'),
                value=terms.IntegerLiteral(location=create_loc(1, 13, 1, 14), value=2),
            ),
        ],
    )
    assert actual == expected


def test_dict__empty():
    actual = parse_expr('{}', rn.DICT, mode=terms.MODE_EVALUATE)
    expected = terms.Dict(
        location=create_loc(1, 0, 1, 2),
        keys=[],
        values=[],
    )
    assert actual == expected


def test_dict__single():
    actual = parse_expr("{'a': 1}", rn.DICT, mode=terms.MODE_EVALUATE)
    expected = terms.Dict(
        location=create_loc(1, 0, 1, 8),
        keys=[terms.StringLiteral(location=create_loc(1, 1, 1, 4), value='a')],
        values=[terms.IntegerLiteral(location=create_loc(1, 6, 1, 7), value=1)],
    )
    assert actual == expected


def test_dict__traling_comma():
    actual = parse_expr("{'a': 1,}", rn.DICT, mode=terms.MODE_EVALUATE)
    expected = terms.Dict(
        location=create_loc(1, 0, 1, 9),
        keys=[terms.StringLiteral(location=create_loc(1, 1, 1, 4), value='a')],
        values=[terms.IntegerLiteral(location=create_loc(1, 6, 1, 7), value=1)],
    )
    assert actual == expected


def test_dict__multi():
    actual = parse_expr("{'a': 1, 'b': 2}", rn.DICT, mode=terms.MODE_EVALUATE)
    expected = terms.Dict(
        location=create_loc(1, 0, 1, 16),
        keys=[
            terms.StringLiteral(location=create_loc(1, 1, 1, 4), value='a'),
            terms.StringLiteral(location=create_loc(1, 9, 1, 12), value='b'),
        ],
        values=[
            terms.IntegerLiteral(location=create_loc(1, 6, 1, 7), value=1),
            terms.IntegerLiteral(location=create_loc(1, 14, 1, 15), value=2),
        ],
    )
    assert actual == expected


def test_expression__disjunction():
    actual = parse_expr('a or b', rn.EXPRESSION, mode=terms.MODE_SAFE)
    expected = terms.TypedBoolOp(
        location=create_loc(1, 0, 1, 6),
        # TODO: rename op to operator #mvp
        op='or',
        values=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_SAFE),
            terms.TypedName(location=create_loc(1, 5, 1, 6), id='b', ctx='load', mode=terms.MODE_SAFE),
        ],
        mode=terms.MODE_SAFE,
    )
    assert actual == expected


def test_disjunction__single():
    actual = parse_expr('a', rn.DISJUNCTION, mode=terms.MODE_SAFE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_SAFE)
    assert actual == expected


def test_disjunction__or_chain():
    actual = parse_expr('a or b or c', rn.DISJUNCTION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedBoolOp(
        location=create_loc(1, 0, 1, 11),
        op='or',
        values=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 5, 1, 6), id='b', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 10, 1, 11), id='c', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_conjunction__and_chain():
    actual = parse_expr('x and y and z', rn.CONJUNCTION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedBoolOp(
        location=create_loc(1, 0, 1, 13),
        op='and',
        values=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 6, 1, 7), id='y', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 12, 1, 13), id='z', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_conjunction__single():
    actual = parse_expr('x', rn.CONJUNCTION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_inversion__not():
    actual = parse_expr('not flag', rn.INVERSION, mode=terms.MODE_EVALUATE)
    expected = terms.BoolNot(
        location=create_loc(1, 0, 1, 8),
        operand=terms.TypedName(location=create_loc(1, 4, 1, 8), id='flag', ctx='load', mode=terms.MODE_EVALUATE),
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_inversion__single():
    actual = parse_expr('flag', rn.INVERSION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 4), id='flag', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_comparison__single():
    actual = parse_expr('a', rn.COMPARISON, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_comparison__chain():
    actual = parse_expr('a < b <= c', rn.COMPARISON, mode=terms.MODE_EVALUATE)
    expected = terms.Compare(
        location=create_loc(1, 0, 1, 10),
        left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
        ops=['<', '<='],
        comparators=[
            terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 9, 1, 10), id='c', ctx='load', mode=terms.MODE_EVALUATE),
        ],
    )
    assert actual == expected


def test_comparison__operators():
    operators = [
        '==',
        '!=',
        '<=',
        '<',
        '>=',
        '>',
        'not in',
        'in',
        'is not',
        'is',
    ]
    for op in operators:
        op_length = len(op)
        expr = f'a {op} b'
        actual = parse_expr(expr, rn.COMPARISON, mode=terms.MODE_EVALUATE)
        expected = terms.Compare(
            location=create_loc(1, 0, 1, 4 + op_length),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            ops=[op],
            comparators=[
                terms.TypedName(
                    location=create_loc(1, 3 + op_length, 1, 4 + op_length),
                    id='b',
                    ctx='load',
                    mode=terms.MODE_EVALUATE,
                ),
            ],
        )
        assert actual == expected, f'Failed for operator: {expr}'


def test_bitwise_or__chain():
    actual = parse_expr('a | b | c', rn.BITWISE_OR, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 9),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 5),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='|',
            right=terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='|',
        right=terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_bitwise_or__single():
    actual = parse_expr('a', rn.BITWISE_OR, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_bitwise_xor__chain():
    actual = parse_expr('a ^ b ^ c', rn.BITWISE_XOR, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 9),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 5),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='^',
            right=terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='^',
        right=terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_bitwise_xor__single():
    actual = parse_expr('a', rn.BITWISE_XOR, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_bitwise_and__chain():
    actual = parse_expr('a & b & c', rn.BITWISE_AND, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 9),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 5),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='&',
            right=terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='&',
        right=terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_bitwise_and__single():
    actual = parse_expr('a', rn.BITWISE_AND, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_bitwise_shift__chain():
    actual = parse_expr('a << b >> c', rn.SHIFT_EXPR, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 11),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 6),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='<<',
            right=terms.TypedName(location=create_loc(1, 5, 1, 6), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='>>',
        right=terms.TypedName(location=create_loc(1, 10, 1, 11), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_bitwise_shift__single():
    actual = parse_expr('a', rn.SHIFT_EXPR, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_sum__invalid_arithmetic():
    actual = parse_expr('a + not b', rn.SUM, mode=terms.MODE_EVALUATE)
    expected = syntax.ErrorTerm(
        message="'not' after an operator must be parenthesized", location=create_loc(1, 0, 1, 9)
    )
    assert actual == expected


def test_sum__chain():
    actual = parse_expr('a + b - c', rn.SUM, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 9),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 5),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='+',
            right=terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='-',
        right=terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_sum__single():
    actual = parse_expr('a', rn.SUM, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_term__chain():
    actual = parse_expr('a * b / c', rn.TERM, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 9),
        left=terms.BinOp(
            location=create_loc(1, 0, 1, 5),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op='*',
            right=terms.TypedName(location=create_loc(1, 4, 1, 5), id='b', ctx='load', mode=terms.MODE_EVALUATE),
        ),
        op='/',
        right=terms.TypedName(location=create_loc(1, 8, 1, 9), id='c', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_term__operators():
    operators = [
        '*',
        '/',
        '//',
        '%',
        '@',
    ]
    for op in operators:
        expr = f'a {op} b'
        actual = parse_expr(expr, rn.TERM, mode=terms.MODE_EVALUATE)
        expected = terms.BinOp(
            location=create_loc(1, 0, 1, 4 + len(op)),
            left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            op=op,
            right=terms.TypedName(
                location=create_loc(1, 3 + len(op), 1, 4 + len(op)),
                id='b',
                ctx='load',
                mode=terms.MODE_EVALUATE,
            ),
        )
        assert actual == expected, f'Failed for operator: {expr}'


def test_term__single():
    actual = parse_expr('a', rn.TERM, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_factor__invalid_factor():
    actual = parse_expr('+ not b', rn.FACTOR, mode=terms.MODE_EVALUATE)
    expected = syntax.ErrorTerm(
        message="'not' after an operator must be parenthesized", location=create_loc(1, 0, 1, 7)
    )
    assert actual == expected


def test_factor__operators():
    operators = [
        '+',
        '-',
        '~',
    ]
    for op in operators:
        expr = f'{op}b'
        actual = parse_expr(expr, rn.FACTOR, mode=terms.MODE_EVALUATE)
        expected = terms.UnaryOp(
            location=create_loc(1, 0, 1, 2 + len(op) - 1),
            op=op,
            operand=terms.TypedName(
                location=create_loc(1, 1 + len(op) - 1, 1, 2 + len(op) - 1),
                id='b',
                ctx='load',
                mode=terms.MODE_EVALUATE,
            ),
        )
        assert actual == expected, f'Failed for operator: {expr}'


def test_power__binary():
    actual = parse_expr('a ** b', rn.POWER, mode=terms.MODE_EVALUATE)
    expected = terms.BinOp(
        location=create_loc(1, 0, 1, 6),
        left=terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
        op='**',
        right=terms.TypedName(location=create_loc(1, 5, 1, 6), id='b', ctx='load', mode=terms.MODE_EVALUATE),
    )
    assert actual == expected


def test_power__single():
    actual = parse_expr('a', rn.POWER, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_primary__attribute():
    actual = parse_expr('obj.attr', rn.PRIMARY, mode=terms.MODE_EVALUATE)
    expected = terms.Attribute(
        location=create_loc(1, 0, 1, 8),
        value=terms.TypedName(location=create_loc(1, 0, 1, 3), id='obj', ctx='load', mode=terms.MODE_EVALUATE),
        attr='attr',
        ctx='load',
    )
    assert actual == expected


def test_primary__call():
    actual = parse_expr('func(arg1, arg2)', rn.PRIMARY, mode=terms.MODE_EVALUATE)
    expected = terms.Call(
        location=create_loc(1, 0, 1, 16),
        func=terms.TypedName(location=create_loc(1, 0, 1, 4), id='func', ctx='load', mode=terms.MODE_EVALUATE),
        args=[
            terms.TypedName(location=create_loc(1, 5, 1, 9), id='arg1', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 11, 1, 15), id='arg2', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        keywords=[],
    )
    assert actual == expected


def test_primary__slice():
    actual = parse_expr('arr[10]', rn.PRIMARY, mode=terms.MODE_EVALUATE)
    expected = terms.Subscript(
        location=create_loc(1, 0, 1, 7),
        value=terms.TypedName(location=create_loc(1, 0, 1, 3), id='arr', ctx='load', mode=terms.MODE_EVALUATE),
        slice=terms.IntegerLiteral(location=create_loc(1, 4, 1, 6), value=10),
        ctx='load',
    )
    assert actual == expected


def test_primary__atom():
    actual = parse_expr('variable', rn.PRIMARY, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 8), id='variable', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_star_expressions__single():
    actual = parse_expr('a', rn.STAR_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_star_expressions__multiple():
    actual = parse_expr('a, b, c', rn.STAR_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 7),
        elements=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 3, 1, 4), id='b', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 6, 1, 7), id='c', ctx='load', mode=terms.MODE_EVALUATE),
        ],
        ctx='load',
    )
    assert actual == expected


def test_star_named_epxressions__empty():
    actual = parse_expr(' ', rn.STAR_NAMED_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = syntax.ErrorTerm(message='chunk[line:1] Not all text consumed: indices 0:0/1:0.')
    assert actual == expected


def test_star_named_expressions__single():
    actual = parse_expr('a', rn.STAR_NAMED_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)],
    )
    assert actual == expected


def test_star_named_expressions__trailing_comma():
    actual = parse_expr('a,', rn.STAR_NAMED_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE)],
    )
    assert actual == expected


def test_star_named_expressions__multiple():
    actual = parse_expr('a, b, c', rn.STAR_NAMED_EXPRESSIONS, mode=terms.MODE_EVALUATE)
    expected = syntax.TermList(
        terms=[
            terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 3, 1, 4), id='b', ctx='load', mode=terms.MODE_EVALUATE),
            terms.TypedName(location=create_loc(1, 6, 1, 7), id='c', ctx='load', mode=terms.MODE_EVALUATE),
        ],
    )
    assert actual == expected


def test_assignment_expression__simple():
    actual = parse_expr('x := 42', rn.ASSIGNMENT_EXPRESSION, mode=terms.MODE_EVALUATE)
    expected = terms.NamedExpr(
        location=create_loc(1, 0, 1, 7),
        target=terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='store', mode=terms.MODE_EVALUATE),
        value=terms.IntegerLiteral(location=create_loc(1, 5, 1, 7), value=42),
    )
    assert actual == expected


def test_assignment_expression__expect_expression():
    actual = parse_expr('y := ', rn.ASSIGNMENT_EXPRESSION, mode=terms.MODE_EVALUATE)
    expected = syntax.ErrorTerm(message='Expected expression after ":="', location=create_loc(1, 0, 1, 4))
    assert actual == expected


def test_if_stmt__simple():
    actual = parse_expr('if x > 0:', rn.IF_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedIf(
        location=create_loc(1, 0, 1, 9),
        test=terms.Compare(
            location=create_loc(1, 2, 1, 8),
            left=terms.TypedName(location=create_loc(1, 3, 1, 4), id='x', ctx='load', mode=terms.MODE_EVALUATE),
            ops=['>'],
            comparators=[terms.IntegerLiteral(location=create_loc(1, 7, 1, 8), value=0)],
        ),
        body=syntax.TermList(terms=[], is_placeholder=True),
        elifs=[],
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_if_stmt__named():
    actual = parse_expr('if (a := 42):', rn.IF_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedIf(
        location=create_loc(1, 0, 1, 13),
        test=terms.NamedExpr(
            location=create_loc(1, 4, 1, 11),
            target=terms.TypedName(location=create_loc(1, 4, 1, 5), id='a', ctx='store', mode=terms.MODE_EVALUATE),
            value=terms.IntegerLiteral(location=create_loc(1, 9, 1, 11), value=42),
        ),
        body=syntax.TermList(terms=[], is_placeholder=True),
        elifs=[],
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_elif_stmt__simple():
    actual = parse_expr('elif y < 10:', rn.ELIF_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.ElifSibling(
        location=create_loc(1, 0, 1, 12),
        test=terms.Compare(
            location=create_loc(1, 4, 1, 11),
            left=terms.TypedName(location=create_loc(1, 5, 1, 6), id='y', ctx='load', mode=terms.MODE_EVALUATE),
            ops=['<'],
            comparators=[terms.IntegerLiteral(location=create_loc(1, 9, 1, 11), value=10)],
        ),
        body=syntax.TermList(terms=[], is_placeholder=True),
    )
    assert actual == expected


def test_else_stmt__simple():
    actual = parse_expr('else:', rn.ELSE_BLOCK, mode=terms.MODE_EVALUATE)
    expected = terms.ElseSibling(
        location=create_loc(1, 0, 1, 5),
        body=syntax.TermList(terms=[], is_placeholder=True),
    )
    assert actual == expected


def test_for_stmt__simple():
    actual = parse_expr('for item in collection:', rn.FOR_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedFor(
        location=create_loc(1, 0, 1, 23),
        target=terms.TypedName(location=create_loc(1, 4, 1, 8), id='item', ctx='store', mode=terms.MODE_EVALUATE),
        iter=terms.TypedName(location=create_loc(1, 12, 1, 22), id='collection', ctx='load', mode=terms.MODE_EVALUATE),
        body=syntax.TermList(terms=[], is_placeholder=True),
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_for_stmt__tuple_target():
    actual = parse_expr('for a, b in pairs:', rn.FOR_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedFor(
        location=create_loc(1, 0, 1, 18),
        target=terms.Tuple(
            location=create_loc(1, 3, 1, 8),
            elements=[
                terms.TypedName(location=create_loc(1, 4, 1, 5), id='a', ctx='store', mode=terms.MODE_EVALUATE),
                terms.TypedName(location=create_loc(1, 7, 1, 8), id='b', ctx='store', mode=terms.MODE_EVALUATE),
            ],
            ctx='store',
        ),
        iter=terms.TypedName(location=create_loc(1, 12, 1, 17), id='pairs', ctx='load', mode=terms.MODE_EVALUATE),
        body=syntax.TermList(terms=[], is_placeholder=True),
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_while_stmt__simple():
    actual = parse_expr('while condition:', rn.WHILE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedWhile(
        location=create_loc(1, 0, 1, 16),
        test=terms.TypedName(location=create_loc(1, 6, 1, 15), id='condition', ctx='load', mode=terms.MODE_EVALUATE),
        body=syntax.TermList(terms=[], is_placeholder=True),
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_while_stmt__named():
    actual = parse_expr('while x := 42:', rn.WHILE_STMT, mode=terms.MODE_EVALUATE)
    expected = terms.TypedWhile(
        location=create_loc(1, 0, 1, 14),
        test=terms.NamedExpr(
            location=create_loc(1, 5, 1, 13),
            target=terms.TypedName(location=create_loc(1, 6, 1, 7), id='x', ctx='store', mode=terms.MODE_EVALUATE),
            value=terms.IntegerLiteral(location=create_loc(1, 11, 1, 13), value=42),
        ),
        body=syntax.TermList(terms=[], is_placeholder=True),
        orelse=syntax.Empty,
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected
