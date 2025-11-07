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
