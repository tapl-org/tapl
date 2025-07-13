# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse
import ast
import pathlib
import os


from tapl_lang.core.compiler import compile_tapl

# If you want to install it in editable mode for development,
# you can use the following command:
# pip install -e .

def compile(path: str) -> None:
    """
    Compiles the TAPL file at the given path.
    """
    absolute_path = os.path.abspath(path)
    p = pathlib.Path(absolute_path)
    source = p.read_text()
    layers = compile_tapl(source)
    dir_path = os.path.dirname(absolute_path)
    print(source)
    for i in range(len(layers)):
        suffix = i if i else ''
        filename = os.path.join(dir_path, f'{p.stem}{suffix}.py')
        python_code = ast.unparse(layers[i])
        with open(filename, 'w') as f:
            f.write(python_code)

def main():
    """
    Main function for the CLI application.
    """
    parser = argparse.ArgumentParser(description='A simple TAPL CLI.')
    parser.add_argument('file', type=str, help='programm read from script file.')
    args = parser.parse_args()

    compile(args.file)  # Call the compile function with the provided file path


if __name__ == '__main__':
    main()
