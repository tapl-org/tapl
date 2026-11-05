# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Cases of the unit tools, shared by the Python tests and the Lean proofs.

Each case is an operand of `'unit.merge'`, `'unit.rebase'` or `'unit.make_reducible'` and
the result the tool gives (None for no result). `unit_ops_cases_test.py` checks the cases
against `unit_ops`; `lean_file()` writes them as Lean `example`s that `lake build` checks
against the Lean definitions in `proofs/Oymomo/UnitOps.lean`, so both sides agree on every
case. After changing the cases, regenerate the Lean file from `oymo-py`:

    hatch run python -m tests.oymomo.unit_ops_cases
"""

from dataclasses import dataclass
from pathlib import Path

from oymo.core import syntax
from oymo.oymomo import reduction, terms
from oymo.oymomo.grammar import parse

LEAN_PATH = Path(__file__).resolve().parents[2] / 'proofs' / 'Oymomo' / 'UnitOpsCases.lean'

# The Lean function of each tool.
LEAN_NAMES = {'merge': 'merge', 'rebase': 'rebase', 'make_reducible': 'makeReducible'}


@dataclass(frozen=True)
class Case:
    name: str
    tool: str  # 'merge', 'rebase' or 'make_reducible'
    operand: terms.Term
    expected: terms.Term | None


def term(source: str | terms.Term) -> terms.Term:
    """The resolved term of `source` (a term is taken as it is)."""
    if not isinstance(source, str):
        return source
    parsed = parse(source)
    if isinstance(parsed, syntax.ErrorTerm):
        raise ValueError(f'Syntax error in a case: {source}')
    return reduction.resolve(parsed)


def struct(*fields: tuple[str, str | terms.Term]) -> terms.Struct:
    """A struct built field by field, so it may repeat a label (the parser rejects that)."""
    return terms.Struct([terms.Field(label, term(value)) for label, value in fields])


FN = "{'function', {n = 'i32'}, 'i32'}"
OTHER_FN = "{'function', {n = 'i64'}, 'i64'}"
# A body that calls `g.lib.step` and ends in a region.
BODY = "λg. λp. 'R' (λr. {let y = g.lib.step {n = p.n} in y})"
DEFINITION = f"{{type = {FN}, link = 'step', body = {BODY}}}"
DECLARATION = f"{{type = {FN}, link = 'step'}}"


def lib(body: str = BODY, extra: str = '') -> str:
    return f'{{lib = {{step = {{type = {FN}, body = {body}}}{extra}}}}}'


def _merge_cases() -> list[Case]:
    def merge(name: str, parts: str | terms.Term, expected: str | terms.Term | None) -> Case:
        return Case(name, 'merge', term(parts), None if expected is None else term(expected))

    fillers = {
        'definition': (FN, f'{{type = {FN}, body = {BODY}}}'),
        'declaration': (FN, f"{{type = {FN}, link = 'step'}}"),
        'global': ("'i32'", "{type = 'i32', init = [00000000]}"),
    }
    cases = [
        merge(
            'combines namespaces',
            "{{a = {x = {type = 'i32', link = 'x'}}}, {a = {y = {type = 'i8', link = 'y'}}, b = {}}}",
            "{a = {x = {type = 'i32', link = 'x'}, y = {type = 'i8', link = 'y'}}, b = {}}",
        ),
    ]
    for kind, (hole_type, filler) in fillers.items():
        hole = f'{{type = {hole_type}}}'
        cases.append(merge(f'a hole, then a {kind}', f'{{{{f = {hole}}}, {{f = {filler}}}}}', f'{{f = {filler}}}'))
        cases.append(merge(f'a {kind}, then a hole', f'{{{{f = {filler}}}, {{f = {hole}}}}}', f'{{f = {filler}}}'))
    cases += [
        merge('two equal holes', f'{{{{f = {{type = {FN}}}}}, {{f = {{type = {FN}}}}}}}', f'{{f = {{type = {FN}}}}}'),
        merge('two equal declarations', f'{{{{f = {DECLARATION}}}, {{f = {DECLARATION}}}}}', f'{{f = {DECLARATION}}}'),
        merge('two equal byte arrays', '{{v = [01]}, {v = [01]}}', '{v = [01]}'),
        merge(
            'two equal global variables',
            "{{v = {type = 'i32', init = [00]}}, {v = {type = 'i32', init = [00]}}}",
            "{v = {type = 'i32', init = [00]}}",
        ),
        merge(
            'a declaration, then its definition',
            f'{{{{f = {DECLARATION}}}, {{f = {DEFINITION}}}}}',
            f'{{f = {DEFINITION}}}',
        ),
        merge(
            'a definition, then its declaration',
            f'{{{{f = {DEFINITION}}}, {{f = {DECLARATION}}}}}',
            f'{{f = {DEFINITION}}}',
        ),
        merge(
            'a declaration with another link',
            f"{{{{f = {{type = {FN}, link = 'other'}}}}, {{f = {DEFINITION}}}}}",
            None,
        ),
        merge(
            'a declaration of another type',
            f"{{{{f = {{type = {OTHER_FN}, link = 'step'}}}}, {{f = {DEFINITION}}}}}",
            None,
        ),
        merge(
            'two equal definitions',
            f'{{{{f = {{type = {FN}, body = {BODY}}}}}, {{f = {{type = {FN}, body = {BODY}}}}}}}',
            None,
        ),
        merge('two equal lambdas', '{{f = λx. x}, {f = λx. x}}', None),
        merge(
            'entries of different types',
            f"{{{{f = {{type = {FN}, link = 'f'}}}}, {{f = {{type = {OTHER_FN}, link = 'f'}}}}}}",
            None,
        ),
        merge(
            'a hole and a filler of another type',
            f"{{{{f = {{type = {FN}}}}}, {{f = {{type = {OTHER_FN}, link = 'f'}}}}}}",
            None,
        ),
        merge(
            'two different declarations',
            f"{{{{f = {{type = {FN}, link = 'f'}}}}, {{f = {{type = {FN}, link = 'g'}}}}}}",
            None,
        ),
        merge('two different byte arrays', '{{f = [01]}, {f = [02]}}', None),
        merge('a namespace and an entry', f"{{{{f = {{}}}}, {{f = {{type = {FN}, link = 'f'}}}}}}", None),
        merge('a byte array and a namespace', '{{f = [01]}, {f = {}}}', None),
        merge('unlabeled fields are appended', '{{[01], a = [02]}, {[01], a = [02]}}', '{[01], a = [02], [01]}'),
        merge(
            'labels keep the order of their first appearance',
            '{{b = [01], a = {x = [01]}}, {c = [01], a = {y = [01]}, b = [01]}}',
            '{b = [01], a = {x = [01], y = [01]}, c = [01]}',
        ),
        merge('one struct', '{{a = [01]}}', '{a = [01]}'),
        merge('no struct', '{}', '{}'),
        merge('the operand labels are ignored', '{x = {a = [01]}, y = {b = [02]}}', '{a = [01], b = [02]}'),
        merge('a part that is not a struct', '{{}, [01]}', None),
        merge('an operand that is not a struct', '[01]', None),
        merge(
            'a label repeated in one part',
            struct(('', struct(('a', '{x = [01]}'), ('a', '{y = [01]}')))),
            '{a = {x = [01], y = [01]}}',
        ),
        merge(
            'a repeated label merges with its last field',
            struct(('', struct(('n', struct(('a', '[01]'), ('a', '{x = [01]}'))))), ('', '{n = {a = {y = [01]}}}')),
            struct(('n', struct(('a', '[01]'), ('a', '{x = [01], y = [01]}')))),
        ),
    ]
    return cases


def _rebase_cases() -> list[Case]:
    def rebase(name: str, operand: str, expected: str | None) -> Case:
        return Case(name, 'rebase', term(operand), None if expected is None else term(expected))

    header = f"{{lib = {{step = {{type = {FN}, link = 'step'}}}}}}"
    data = ", c = {type = 'i32', value = [01000000]}, h = {type = 'i32'}"
    nested = "λg. λp. 'R' (λr. {e = λx. 'R' (λq. {let y = g.lib.step {n = x} in g.lib.c})})"
    nested_rebased = "λg. λp. 'R' (λr. {e = λx. 'R' (λq. {let y = g.a.b.lib.step {n = x} in g.a.b.lib.c})})"
    return [
        rebase(
            'prefixes the paths and puts the struct under the prefix',
            f"{{{{'dbl'}}, {lib()}}}",
            f'{{dbl = {lib("λg. λp. 'R' (λr. {let y = g.dbl.lib.step {n = p.n} in y})")}}}',
        ),
        rebase(
            'in nested regions and under binders',
            f"{{{{'a', 'b'}}, {lib(nested)}}}",
            f'{{a = {{b = {lib(nested_rebased)}}}}}',
        ),
        rebase(
            'copies data entries',
            f"{{{{'x'}}, {lib(extra=data)}}}",
            f'{{x = {lib("λg. λp. 'R' (λr. {let y = g.x.lib.step {n = p.n} in y})", data)}}}',
        ),
        rebase('mounts a header', f"{{{{'libc'}}, {header}}}", f'{{libc = {header}}}'),
        rebase('an empty prefix changes nothing', f'{{{{}}, {lib()}}}', lib()),
        rebase(
            'a path under a fixed point and in a field',
            f"{{{{'x'}}, {lib('λg. λp. fix (λs. {a = g.k, b = s g.m.n})')}}}",
            f'{{x = {lib("λg. λp. fix (λs. {a = g.x.k, b = s g.x.m.n})")}}}',
        ),
        Case('a text label', 'rebase', term(f"{{{{'ü'}}, {header}}}"), struct(('ü', header))),
        rebase('g used whole', f"{{{{'x'}}, {lib('λg. λp. p g')}}}", None),
        rebase('g applied, then projected', f"{{{{'x'}}, {lib('λg. λp. (g p).x')}}}", None),
        rebase('a body that is not a lambda', f"{{{{'x'}}, {lib('[01]')}}}", None),
        rebase('a lambda outside an entry body', "{{'x'}, {f = λx. x}}", None),
        rebase('a body field outside an entry', "{{'x'}, {ns = {body = λg. g.x}}}", None),
        rebase('a prefix label that is not text', f'{{{{[ff]}}, {lib()}}}', None),
        rebase('a prefix label that is a surrogate', f'{{{{[eda080]}}, {lib()}}}', None),
        rebase('an empty prefix label', f"{{{{''}}, {lib()}}}", None),
        rebase('a prefix that is not a struct', f"{{'x', {lib()}}}", None),
        rebase('one field', "{{'x'}}", None),
        rebase('three fields', "{{'x'}, {}, {}}", None),
        rebase('an X that is not a struct', "{{'x'}, [01]}", None),
    ]


def _make_reducible_cases() -> list[Case]:
    def make_reducible(name: str, operand: str, expected: str | None) -> Case:
        return Case(name, 'make_reducible', term(operand), None if expected is None else term(expected))

    return [
        make_reducible(
            'hoists g and runs regions',
            "{f = {type = 'i32', body = λg. λp. 'R' (λr. {g.k})}, "
            "k = {type = 'i32', value = [07000000]}, d = {type = 'i32', link = 'd'}}",
            "λg. {f = λp. (fix (λr. {g.k})) [00], k = {type = 'i32', value = [07000000]}, d = {type = 'i32', link = 'd'}}",
        ),
        make_reducible(
            'nested regions',
            "{f = {type = 'i32', link = 'f', body = λg. λp. 'R' (λr. {e = λx. 'R' (λq. {x, g.f})})}}",
            'λg. {f = λp. (fix (λr. {e = λx. (fix (λq. {x, g.f})) [00]})) [00]}',
        ),
        make_reducible(
            'only a region marker applied to a lambda is a region',
            "{f = {type = 'i32', body = λg. λp. {'R' [01], 'S' (λr. r), 'R' p}}}",
            "λg. {f = λp. {'R' [01], 'S' (λr. r), 'R' p}}",
        ),
        make_reducible(
            'nested namespaces',
            "{ns = {f = {type = 'i32', body = λg. λp. g.ns.f p}}, v = [01]}",
            'λg. {ns = {f = λp. g.ns.f p}, v = [01]}',
        ),
        make_reducible('an empty ingot', '{}', 'λg. {}'),
        make_reducible('a body not shaped λg. λp. …', "{f = {type = 'i32', body = λg. 'R' (λr. {[00]})}}", None),
        make_reducible('a body that is not a lambda', "{f = {type = 'i32', body = [01]}}", None),
        make_reducible('a lambda outside an entry body', '{f = λx. x}', None),
        make_reducible('a lambda in an entry without a body', "{f = {type = 'i32', init = λx. x}}", None),
        make_reducible('an operand that is not a struct', "'notastruct'", None),
    ]


CASES: list[Case] = [*_merge_cases(), *_rebase_cases(), *_make_reducible_cases()]


def _lean_string(text: str) -> str:
    escaped = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
    return f'"{escaped}"'


def lean_term(t: terms.Term) -> str:
    """`t` as a Lean `Term`."""
    match t:
        case terms.BruijnIndex(index=index):
            return f'var {index}'
        case terms.Lambda(body=body):
            return f'lam ({lean_term(body)})'
        case terms.Apply(function=function, argument=argument):
            return f'app ({lean_term(function)}) ({lean_term(argument)})'
        case terms.Struct(fields=fields):
            result = 'snil'
            for f in reversed(fields):
                result = f'scons {_lean_string(f.label)} ({lean_term(f.value)}) ({result})'
            return result
        case terms.Project(struct=inner, label=label):
            return f'proj ({lean_term(inner)}) {_lean_string(label)}'
        case terms.ByteArray(value=value):
            return f'bytes [{", ".join(f"0x{b:02x}" for b in value)}]'
        case terms.Fix(body=body):
            return f'fix ({lean_term(body)})'
    raise ValueError(f'No Lean term for {t!r}.')


def lean_file() -> str:
    """The Lean file of the cases: one `example` per case, checked by `rfl`."""
    lines = [
        '-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception',
        '',
        '-- Generated by `python -m tests.oymomo.unit_ops_cases` from the cases in',
        '-- `tests/oymomo/unit_ops_cases.py`. Do not edit.',
        '',
        'import Oymomo.UnitOps',
        '',
        '/-! # The unit tools on the cases the Python tests check -/',
        '',
        'namespace Oymomo',
        'open Term',
    ]
    for case in CASES:
        expected = 'none' if case.expected is None else f'some ({lean_term(case.expected)})'
        lines += [
            '',
            f'/-- `{case.tool}`: {case.name}. -/',
            f'example : {LEAN_NAMES[case.tool]} ({lean_term(case.operand)}) =',
            f'    {expected} := by rfl',
        ]
    lines += ['', 'end Oymomo', '']
    return '\n'.join(lines)


def main() -> None:
    LEAN_PATH.write_text(lean_file(), encoding='utf-8')
    print(f'Wrote {LEAN_PATH}')


if __name__ == '__main__':
    main()
