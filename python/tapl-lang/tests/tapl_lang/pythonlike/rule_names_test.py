# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.pythonlike import rule_names


def test_rule_name_consistency():
    assert rule_names.RULE_NAMES, 'Grammar rule names are not defined or empty.'
    for full_rule_name in rule_names.RULE_NAMES:
        names = full_rule_name.split('.')
        assert len(names) == 2, f'Rule name {full_rule_name} does not have exactly two parts.'
        assert names[0] == 'pythonlike', f'Rule name {full_rule_name} does not start with "pythonlike".'
        constant_name = names[1].upper()
        assert (
            constant_name in rule_names.__dict__
        ), f'Rule name {constant_name} is not found as a constant in the grammar module.'
