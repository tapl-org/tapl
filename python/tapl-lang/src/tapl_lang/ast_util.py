# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast

from tapl_lang.syntax import Location


def ast_typelib_attribute(attr_name: str, loc: Location) -> ast.expr:
    name = ast.Name(id='t', ctx=ast.Load())
    attr = ast.Attribute(value=name, attr=attr_name, ctx=ast.Load())
    loc.locate(name, attr)
    return attr


def ast_typelib_call(function_name: str, args: list[ast.expr], loc: Location) -> ast.expr:
    call = ast.Call(func=ast_typelib_attribute(function_name, loc), args=args)
    loc.locate(call)
    return call


def ast_method_call(value: ast.expr, method_name: str, args: list[ast.expr], loc: Location) -> ast.expr:
    func = ast.Attribute(value=value, attr=method_name, ctx=ast.Load())
    call = ast.Call(func=func, args=args)
    loc.locate(func, call)
    return call
