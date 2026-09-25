# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from oymo.core import parser, syntax, util
from oymo.oymomo import grammar, terms
from oymo.oymomo import rule_names as rn


def parse_expr(text: str, start_rule: str, *, mode: syntax.Term = syntax.MODE_SAFE, debug=False) -> syntax.Term:
    return parser.parse_text(
        text,
        grammar=parser.Grammar(grammar.get_grammar().rule_map, start_rule),
        debug=debug,
        config=parser.Config(mode=mode),
    )


def test_variable() -> None:
    text = 'x'
    term = parse_expr(text, rn.VARIABLE)
    assert isinstance(term, terms.Variable)
    assert term.name == 'x'


def test_lambda() -> None:
    text = 'a:i32 -> x'
    term = parse_expr(text, rn.LAMBDA)
    assert isinstance(term, terms.Lambda)
    assert term.param_name == 'a'
    assert term.param_form == 'i32'
    assert isinstance(term.body, terms.Variable)
    assert term.body.name == 'x'


def test_apply() -> None:
    text = 'f x'
    term = parse_expr(text, rn.APPLY)
    assert isinstance(term, terms.Apply)
    assert isinstance(term.function, terms.Variable)
    assert term.function.name == 'f'
    assert isinstance(term.argument, terms.Variable)
    assert term.argument.name == 'x'


def test_group() -> None:
    text = '(x)'
    term = parse_expr(text, rn.GROUP)
    assert isinstance(term, terms.Variable)
    assert term.name == 'x'


def test_record_empty() -> None:
    text = '[]'
    term = parse_expr(text, rn.RECORD)
    assert isinstance(term, terms.Record)
    assert len(term.fields) == 0


def test_record_one_field() -> None:
    text = '[a = x]'
    term = parse_expr(text, rn.RECORD)
    assert isinstance(term, terms.Record)
    assert len(term.fields) == 1
    field = term.fields[0]
    assert field.label == 'a'
    assert isinstance(field.value, terms.Variable)
    assert field.value.name == 'x'


def test_record_two_fields() -> None:
    text = '[a = x, b = y,]'
    term = parse_expr(text, rn.RECORD)
    assert isinstance(term, terms.Record)
    field = term.fields[0]
    assert field.label == 'a'
    assert isinstance(field.value, terms.Variable)
    assert field.value.name == 'x'
    field = term.fields[1]
    assert field.label == 'b'
    assert isinstance(field.value, terms.Variable)
    assert field.value.name == 'y'


def test_select() -> None:
    text = 'r.a'
    term = parse_expr(text, rn.SELECT)
    assert isinstance(term, terms.Select)
    assert isinstance(term.record, terms.Variable)
    assert term.record.name == 'r'
    assert term.label == 'a'


def test_if() -> None:
    text = 'if x then y else z'
    term = parse_expr(text, rn.IF)
    assert isinstance(term, terms.If)
    assert isinstance(term.condition, terms.Variable)
    assert term.condition.name == 'x'
    assert isinstance(term.then_clause, terms.Variable)
    assert term.then_clause.name == 'y'
    assert isinstance(term.else_clause, terms.Variable)
    assert term.else_clause.name == 'z'


def test_fix() -> None:
    text = 'fix f'
    term = parse_expr(text, rn.FIX)
    assert isinstance(term, terms.Fix)
    assert isinstance(term.function, terms.Variable)
    assert term.function.name == 'f'


def test_positive_integer() -> None:
    text = '123:i32'
    term = parse_expr(text, rn.INTEGER)
    assert isinstance(term, terms.Integer)
    assert term.value == 123
    assert term.form == 'i32'


def test_negative_integer() -> None:
    text = '-123:i32'
    term = parse_expr(text, rn.INTEGER)
    assert isinstance(term, terms.Integer)
    assert term.value == -123
    assert term.form == 'i32'


def test_string() -> None:
    text = '"hello":str'
    term = parse_expr(text, rn.STRING)
    assert isinstance(term, terms.String)
    assert term.value == 'hello'
    assert term.form == 'str'


def test_parse_simplest_main() -> None:
    text = 'realm:_ -> module:_ -> [main = a:i32 -> 0:i32]'
    term = parse_expr(text, rn.START)
    errors = util.gather_errors(term)
    assert len(errors) == 0
