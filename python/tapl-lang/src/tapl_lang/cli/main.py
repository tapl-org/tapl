# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse

# If you want to install it in editable mode for development,
# you can use the following command:
# pip install -e .


def main():
    """
    Main function for the CLI application.
    Parses arguments and prints a greeting.
    """
    parser = argparse.ArgumentParser(description='A simple TAPL CLI.')
    parser.add_argument('name', type=str, help='The name to greet.')
    args = parser.parse_args()

    print(f'Hello, {args.name}! Welcome to TAPL.')  # noqa: T201


if __name__ == '__main__':
    main()
