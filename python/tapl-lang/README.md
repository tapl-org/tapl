# Tapl Lang

<!--
Part of the Tapl Language project, under the Apache License v2.0 with LLVM
Exceptions. See /LICENSE for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

[![PyPI - Version](https://img.shields.io/pypi/v/tapl-lang.svg)](https://pypi.org/project/tapl-lang)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tapl-lang.svg)](https://pypi.org/project/tapl-lang)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install tapl-lang
```

## License

`tapl-lang` is distributed under the terms of the [Apache-2.0 WITH LLVM-exception](https://spdx.org/licenses/Apache-2.0.html) license.


## Development Setup

```console
sudo apt install pipx
pipx ensurepath
pipx install hatch
```

As a temporary workaround until a better approach is found, create `/usr/bin/meld` with the following shell script when a diff tool for ApprovalTests is not set up.

```bash
#!/usr/bin/env bash

set -euo pipefail

CURSOR_BIN="/home/ortibazar/.cursor-server/bin/linux-arm64/e9ee1339915a927dfb2df4a836dd9c8337e17cc0/bin/remote-cli/cursor"

if [[ $# -ne 2 ]]; then
  printf 'Called as: %q' "$0"
  printf ' %q' "$@"
  printf '\n'
  echo "Usage: $0 <param1> <param2>" >&2
  exit 1
fi

if [[ ! -x "$CURSOR_BIN" ]]; then
  echo "Error: cursor binary is not executable or not found at:" >&2
  echo "  $CURSOR_BIN" >&2
  exit 1
fi

"$CURSOR_BIN" --diff "$1" "$2"
```
