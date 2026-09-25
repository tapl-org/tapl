# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from oymo.core import parser, syntax, util
from oymo.oymomo import grammar
from oymo.oymomo import rule_names as rn
from oymo.oymomo.pretty import print_term


def parse_term(
    text: str, *, start_rule: str = rn.START, mode: syntax.Term = syntax.MODE_SAFE, debug=False
) -> syntax.Term:
    return parser.parse_text(
        text,
        grammar=parser.Grammar(grammar.get_grammar().rule_map, start_rule),
        debug=debug,
        config=parser.Config(mode=mode),
    )


def to_pretty(text: str) -> str:
    term = parse_term(text)
    errors = util.gather_errors(term)
    if errors:
        raise ValueError(f'Errors: {errors}')
    return print_term(term)


def test_integer() -> None:
    assert to_pretty('123:i32') == '123:i32'


def test_string() -> None:
    assert to_pretty('"hello":str') == '"hello":str'


def test_variable() -> None:
    assert to_pretty('x') == 'x'


def test_lambda() -> None:
    assert to_pretty('a:i32 -> a') == 'λa:i32.a'
    assert to_pretty('a:i32 -> b:i32 -> a') == 'λa:i32.λb:i32.a'


def tst_apply() -> None:
    assert to_pretty('f x') == 'f x'
