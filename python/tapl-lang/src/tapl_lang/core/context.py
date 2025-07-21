# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Context:
    def __init__(self, fields: dict[str, Any] | None = None):
        self.fields: dict[str, Slot] = {}
        if fields:
            self.store_many(fields)

    def load(self, name: str) -> Any:
        return self.fields[name].value

    def store(self, name: str, value: Any) -> None:
        self.fields[name] = Slot(value)

    def delete(self, name: str) -> None:
        del self.fields[name]

    def store_many(self, fields: dict[str, Any]) -> None:
        for name, value in fields.items():
            self.store(name, value)

    def __repr__(self) -> str:
        if '__repr__' in self.fields:
            return self.fields['__repr__'].value()
        return object.__repr__(self)


_INTERNAL_FIELD_NAME = 'internal__tapl'


def get_proxy_internal(proxy: Proxy) -> Context:
    """Retrieve the internal context from a Proxy instance."""
    return object.__getattribute__(proxy, _INTERNAL_FIELD_NAME)


# ruff: noqa: N805
class Proxy:
    """A proxy providing dynamic attribute access."""

    def __init__(self__tapl, context__tapl: Context):
        object.__setattr__(self__tapl, _INTERNAL_FIELD_NAME, context__tapl)

    def __getattribute__(self__tapl, name):
        return get_proxy_internal(self__tapl).load(name)

    def __setattr__(self__tapl, name: str, value: Any):
        get_proxy_internal(self__tapl).store(name, value)

    def __call__(self__tapl, *args, **kwargs):
        return get_proxy_internal(self__tapl).load('__call__')(*args, **kwargs)

    def __repr__(self__tapl):
        return get_proxy_internal(self__tapl).__repr__()
