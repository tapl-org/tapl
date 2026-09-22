# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from oymo.core import parser, syntax
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
    assert isinstance(term.param_form, terms.ScalarForm)
    assert term.param_form.name == 'i32'
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


def test_record_empty() -> None:
    text = '{}'
    term = parse_expr(text, rn.RECORD)
    assert isinstance(term, terms.Record)
    assert len(term.fields) == 0
