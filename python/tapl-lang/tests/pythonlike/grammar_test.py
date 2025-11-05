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


def test_simple_stmt__pass():
    actual = parse_expr('pass', rn.PASS_STMT)
    expected = terms.Pass(location=create_loc(1, 0, 1, 4))
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


def test_atom__tuple():
    # 1, "two", None
    actual = parse_expr('()', rn.ATOM)
    expected = terms.Tuple(
        location=create_loc(1, 0, 1, 2),
        elements=[
            # terms.IntegerLiteral(location=create_loc(1, 1, 1, 2), value=1),
            # terms.StringLiteral(location=create_loc(1, 4, 1, 9), value='two'),
            # terms.NoneLiteral(location=create_loc(1, 11, 1, 15)),
        ],
        ctx='load',
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
    actual = parse_expr('a', rn.EXPRESSION, mode=terms.MODE_SAFE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='a', ctx='load', mode=terms.MODE_SAFE)
    assert actual == expected


def test_disjunction__or_chain():
    actual = parse_expr('a or b or c', rn.EXPRESSION, mode=terms.MODE_EVALUATE)
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
    actual = parse_expr('x and y and z', rn.EXPRESSION, mode=terms.MODE_EVALUATE)
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
    actual = parse_expr('x', rn.EXPRESSION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 1), id='x', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected


def test_inversion__not():
    actual = parse_expr('not flag', rn.EXPRESSION, mode=terms.MODE_EVALUATE)
    expected = terms.BoolNot(
        location=create_loc(1, 0, 1, 8),
        operand=terms.TypedName(location=create_loc(1, 4, 1, 8), id='flag', ctx='load', mode=terms.MODE_EVALUATE),
        mode=terms.MODE_EVALUATE,
    )
    assert actual == expected


def test_inversion__single():
    actual = parse_expr('flag', rn.EXPRESSION, mode=terms.MODE_EVALUATE)
    expected = terms.TypedName(location=create_loc(1, 0, 1, 4), id='flag', ctx='load', mode=terms.MODE_EVALUATE)
    assert actual == expected
