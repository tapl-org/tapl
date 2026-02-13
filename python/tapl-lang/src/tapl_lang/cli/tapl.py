# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse
import ast
import os
import pathlib

from tapl_lang.__about__ import __version__
from tapl_lang.lib.compiler import compile_tapl

# If you want to install it in editable mode for development,
# you can use the following command:
# pip install -e .


def compile_and_run(path: str) -> None:
    """
    Compiles the TAPL file at the given path.
    """
    absolute_path = os.path.abspath(path)
    p = pathlib.Path(absolute_path)
    source = p.read_text()
    layers = compile_tapl(source)
    dir_path = os.path.dirname(absolute_path)
    for i in reversed(range(len(layers))):
        suffix = i if i else ''
        filename = os.path.join(dir_path, f'{p.stem}{suffix}.py')
        python_code = ast.unparse(layers[i])
        with open(filename, 'w') as f:
            f.write(python_code)
        exec(python_code, globals())  # noqa: S102 # Find safe way to execute


def main():
    """
    Main function for the CLI application.
    """
    parser = argparse.ArgumentParser(
        prog='tapl',
        description='TAPL compiler CLI — compiles and runs .tapl source files.',
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )
    parser.add_argument('file', type=str, help='path to a .tapl source file')
    args = parser.parse_args()

    compile_and_run(args.file)


if __name__ == '__main__':
    main()
