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
    term = parse_expr(text, rn.START)
    assert isinstance(term, terms.Variable)
    assert term.name == 'x'
