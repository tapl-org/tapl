# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

_SUBJECT_FIELD_NAME = 'subject__tapl'


def extract_subject(p: 'Proxy') -> Any:
    """Retrieve the internal subject from a Proxy instance."""
    return object.__getattribute__(p, _SUBJECT_FIELD_NAME)


# ruff: noqa: N805
class Proxy:
    """A proxy providing dynamic attribute access."""

    def __init__(self__tapl, subject__tapl: Any):
        object.__setattr__(self__tapl, _SUBJECT_FIELD_NAME, subject__tapl)

    def __getattribute__(self__tapl, name):
        return extract_subject(self__tapl).__getitem__(name)

    def __setattr__(self__tapl, name: str, value: Any):
        extract_subject(self__tapl).__setitem__(name, value)

    def __call__(self__tapl, *args, **kwargs):
        return extract_subject(self__tapl).__getitem__('__call__')(*args, **kwargs)

    def __repr__(self__tapl):
        return extract_subject(self__tapl).__getitem__('__repr__')()
