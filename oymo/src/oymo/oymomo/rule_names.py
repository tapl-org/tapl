# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


RULE_NAMES = set()


def declare(rule_key: str) -> str:
    if not rule_key:
        raise ValueError('Rule name cannot be empty.')
    if rule_key.lower() != rule_key:
        raise ValueError('Rule name must be in lowercase.')
    rule_name = f'oymomo.{rule_key}'
    if rule_name in RULE_NAMES:
        raise ValueError(f'Rule {rule_name} is already defined.')
    RULE_NAMES.add(rule_name)
    return rule_name


START = declare('start')
TOKEN = declare('token')
GROUP = declare('group')
EXPRESSION = declare('expression')
VARIABLE = declare('variable')
LAMBDA = declare('lambda')
APPLY = declare('apply')
STRUCT = declare('struct')
FIELD_ACCESS = declare('field_access')
IF = declare('if')
LET = declare('let')
FIX = declare('fix')
BYTE_ARRAY = declare('byte_array')
PRIMARY = declare('primary')
FORM = declare('form')
ARROW_FORM = declare('arrow_form')
