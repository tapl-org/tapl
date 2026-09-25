# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from oymo.core import parser, syntax
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
    return print_term(parse_term(text))


def test_integer() -> None:
    assert to_pretty('123:i32') == '123:i32'


def test_string() -> None:
    assert to_pretty('"hello":str') == '"hello":str'


def test_variable() -> None:
    assert to_pretty('x') == 'x'
