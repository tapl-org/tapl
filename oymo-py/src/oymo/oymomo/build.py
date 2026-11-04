# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Building a unit: what `oymo build` writes after reduction.

A project is one unit, named `unit`. Its outputs are flat, with fixed names, in the
destination folder (by default `oymo-out/` in the current directory), which oymo only
writes and never reads:

- `unit.ll`: the low layer, or the only layer;
- `unit.guard.ll`: the high layer, for two layers;
- `unit.h.oymo`: the header, `low : high` for two layers.

oymo ends at the `.ll`: linking and running are clang's and the user's job, e.g.
`clang -Wno-override-module oymo-out/unit.ll ../math/oymo-out/unit.ll -o app`, or
`--target` for another platform. The `.ll` holds no triple and no data layout, so clang uses
its target's (and warns that it does, unless `-Wno-override-module`).
Before a build, `remove_stale` removes `unit.guard.ll`, so a one-layer build leaves no
guard behind.
"""

import os
import pathlib


# The destination folder's name in the current directory, by default.
DEFAULT_OUT = 'oymo-out'
# The unit's name: every output's name starts with it.
NAME = 'unit'
LL = f'{NAME}.ll'
GUARD_LL = f'{NAME}.guard.ll'
HEADER = f'{NAME}.h.oymo'


class BuildError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def remove_stale(out: str) -> None:
    """Removes the output in `out` that a build may not make again: the guard's `.ll`."""
    try:
        pathlib.Path(out, GUARD_LL).unlink(missing_ok=True)
    except OSError as error:
        raise BuildError(f'Cannot remove {os.path.join(out, GUARD_LL)!r}: {error.strerror}.') from error


def build(out: str, layers: list[str], header: str) -> None:
    """Writes into `out` the outputs of the unit whose layers' LLVM IR is `layers` (low, then
    high) and whose header is `header`."""
    names = [LL, GUARD_LL][: len(layers)]
    try:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BuildError(f'Cannot make the folder {out!r}: {error.strerror}.') from error
    for name, text in [*zip(names, layers, strict=True), (HEADER, header)]:
        try:
            pathlib.Path(out, name).write_text(text, encoding='utf-8')
        except OSError as error:
            raise BuildError(f'Cannot write {os.path.join(out, name)!r}: {error.strerror}.') from error
