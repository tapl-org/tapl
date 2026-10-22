# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The code refactor to semantics.tex (refactor plan, stages 1-8) removes the syntax the old
BANF/LLVM pipeline reads (forms, builtins), so its modules no longer import. Their tests are
left out until the stage that rewrites them puts them back:

- stage 7 (LLVM): `llvm_translate_test.py`
- stage 8 (goldens, CLI): `golden_test.py`, `cli_test.py`
"""

OLD_PIPELINE = [
    'oymomo/llvm_translate_test.py',
    'golden_test.py',
    'cli_test.py',
]

collect_ignore = OLD_PIPELINE
