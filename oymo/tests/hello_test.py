# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.hello import hello


def test_hello_default() -> None:
    assert hello() == 'Hello, world!'


def test_hello_name() -> None:
    assert hello('oymo') == 'Hello, oymo!'
