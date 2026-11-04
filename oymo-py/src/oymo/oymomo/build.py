# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Building a unit: what `oymo build` writes after reduction.

A project is one unit, named `unit`, built for the host. Its outputs are flat, with fixed
names, in the destination folder (by default `oymo-out/` in the current directory), which
oymo only writes and never reads:

- `unit.ll`: the low layer, or the only layer;
- `unit.guard.ll`: the high layer, for two layers;
- `unit.h.oymo`: the header, `low : high` for two layers;
- `unit`: the binary of `unit.ll`, when the low layer links a `main`;
- `unit.guard`: the binary of `unit.guard.ll`, for two layers whose high layer links a `main`.

Each binary is one `clang -Wno-override-module -x ir … -o …` run, from the `.ll` straight
to the binary; clang adds the system libraries itself. Nothing is run. Before a build,
`remove_stale` removes `unit`, `unit.guard` and `unit.guard.ll`, so a failed or one-layer
build leaves none of them behind.
"""

import os
import pathlib
import subprocess

from oymo.oymomo import ingot as ingots

# The destination folder's name in the current directory, by default.
DEFAULT_OUT = 'oymo-out'
# The unit's name: every output's name starts with it.
NAME = 'unit'
LL = f'{NAME}.ll'
GUARD_LL = f'{NAME}.guard.ll'
HEADER = f'{NAME}.h.oymo'
GUARD = f'{NAME}.guard'


class BuildError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def has_main(ingot: ingots.Ingot) -> bool:
    """Whether `ingot` defines a function linked as `main`."""
    return any(isinstance(symbol, ingots.Definition) and symbol.link == 'main' for symbol in ingot.symbols)


def remove_stale(out: str) -> None:
    """Removes the outputs in `out` that a build may not make again: the binaries and the
    guard's `.ll`."""
    for name in (NAME, GUARD, GUARD_LL):
        try:
            pathlib.Path(out, name).unlink(missing_ok=True)
        except OSError as error:
            raise BuildError(f'Cannot remove {os.path.join(out, name)!r}: {error.strerror}.') from error


def build(out: str, layers: list[tuple[ingots.Ingot, str]], header: str, clang: str | None) -> None:
    """Writes into `out` the outputs of the unit whose layers' ingots and LLVM IR are
    `layers` (low, then high) and whose header is `header`, and links its binaries with
    `clang` (None if it is not on PATH: an error only if there is a binary to link)."""
    names = [LL, GUARD_LL][: len(layers)]
    try:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BuildError(f'Cannot make the folder {out!r}: {error.strerror}.') from error
    for name, text in [*((name, ir_text) for name, (_, ir_text) in zip(names, layers, strict=True)), (HEADER, header)]:
        try:
            pathlib.Path(out, name).write_text(text, encoding='utf-8')
        except OSError as error:
            raise BuildError(f'Cannot write {os.path.join(out, name)!r}: {error.strerror}.') from error
    binaries = [NAME, GUARD][: len(layers)]
    for name, binary, (ingot, _) in zip(names, binaries, layers, strict=True):
        if not has_main(ingot):
            continue
        if clang is None:
            raise BuildError(f'Linking {binary} needs clang, which is not on PATH; install clang.')
        command = [clang, '-Wno-override-module', '-x', 'ir', os.path.join(out, name), '-o', os.path.join(out, binary)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise BuildError(f'clang failed:\n{result.stderr.rstrip()}')
