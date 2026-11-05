# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The shared cases of the unit tools: Python gives each expected result, and the Lean file
that checks the same cases is up to date."""

import pytest

from oymo.oymomo import unit_ops
from .unit_ops_cases import CASES, LEAN_PATH, lean_file


@pytest.mark.parametrize('case', CASES, ids=[f'{c.tool}: {c.name}' for c in CASES])
def test_case(case):
    assert getattr(unit_ops, case.tool)(case.operand) == case.expected


def test_case_names_are_unique():
    names = [(c.tool, c.name) for c in CASES]
    assert len(names) == len(set(names))


def test_lean_cases_are_up_to_date():
    assert LEAN_PATH.read_text(encoding='utf-8') == lean_file(), (
        'Regenerate it: hatch run python -m tests.oymomo.unit_ops_cases'
    )
