# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Renders oymomo terms and forms as text.

The default rendering is compact: one line, with parentheses only where the grammar
needs them. Neither mode prints an `unknown` form. With `pretty=True` the result is
oymomo source that parses back to the same term: parentheses only where needed, and
quoted names where needed. A term that doesn't fit in `width` columns breaks: a struct puts one
field per line, a lambda puts its body on the next line (unless the body is a struct
or another lambda, so `prim → decls → defs → {` stays on one line),
an apply puts its argument on the next line, and an `if` puts `then` and `else` on
their own lines.

An apply of a lambda, `(x → body) e`, prints as `let x = e in body`; a broken let puts
its body on the next line, so a chain of lets reads one let per line. A BruijnIndex
prints as `$i` in both modes. With `name_indices=True` it prints as the name of its
binder instead, except where an inner binder shadows that name or no binder is in
scope; there it stays `$i`, so the output still resolves back to the same term.
"""

from oymo.core import syntax
from oymo.core.terminals import IDENT_CONTINUE, IDENT_START
from oymo.oymomo import terms
from oymo.oymomo.grammar import RESERVED, UNKNOWN_FORM

# Binding levels, loosest first. A term printed where a tighter level is needed gets parentheses.
_EXPRESSION, _APPLY, _FIELD_ACCESS = range(3)


def show(
    term: syntax.Term, *, pretty: bool = False, name_indices: bool = False, width: int = 80, indent: int = 2
) -> str:
    """`name_indices` prints a BruijnIndex as its binder's name where that is safe.
    `width` (columns) and `indent` (spaces per level) only affect pretty output."""
    names = () if name_indices else None
    return _pretty(term, _EXPRESSION, 0, 0, width, indent, names) if pretty else _compact(term, names)


def show_form(form: terms.Form, *, pretty: bool = False) -> str:
    return _pretty_form(form, arrow=True) if pretty else _compact_form(form)


def _compact(term, names, level=_EXPRESSION):
    """Like `_flat`, but `:form` without a space, and bytes ungrouped."""
    match term:
        case terms.Variable(name=name):
            text = _name(name)
        case terms.BruijnIndex(index=index):
            text = _bruijn_name(index, names)
        case terms.Lambda(param_name=name, param_form=form, body=body):
            text = f'{_name(name)}{_compact_suffix(form)} → {_compact(body, _bind(names, name))}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            value = _compact(argument, names)
            text = f'let {_name(name)}{_compact_suffix(form)} = {value} in {_compact(body, _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = f'{_compact(function, names, _APPLY)} {_compact(argument, names, _FIELD_ACCESS)}'
        case terms.Struct(fields=fields):
            text = '{' + ', '.join(f'{_name(f.label)} = {_compact(f.value, names)}' for f in fields) + '}'
        case terms.FieldAccess(struct=struct, label=label):
            text = f'{_compact(struct, names, _FIELD_ACCESS)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = f'if {_compact(c, names)} then {_compact(t, names)} else {_compact(e, names)}'
        case terms.Fix(function=function):
            text = f'fix {_compact(function, names, _FIELD_ACCESS)}'
        case terms.ByteArray(value=value, form=form):
            text = f'[{value.hex()}]{_compact_suffix(form)}'
        case syntax.ErrorTerm():
            text = 'error'
        case _:
            raise AssertionError(term)
    return f'({text})' if level > _loosest(term) else text


def _compact_suffix(form):
    """`:form` after a name or byte array; nothing for an unknown form. An arrow form needs parentheses here."""
    return '' if form == UNKNOWN_FORM else ':' + _compact_form(form, arrow=False)


def _compact_form(form, *, arrow=True):
    match form:
        case str():
            return _name(form)
        case terms.FunctionForm(param=param, result=result):
            text = f'{_compact_form(param, arrow=False)} → {_compact_form(result)}'
            return text if arrow else f'({text})'
        case terms.StructForm(fields=fields):
            return '{' + ', '.join(f'{_name(label)}{_compact_field_suffix(f)}' for label, f in fields) + '}'
    raise AssertionError(form)


def _compact_field_suffix(form):
    """A struct-form field takes an arrow form without parentheses."""
    return '' if form == UNKNOWN_FORM else ': ' + _compact_form(form)


def _loosest(term):
    """The loosest level `term` can be printed at without parentheses."""
    match term:
        case terms.Lambda() | terms.If() | terms.Apply(function=terms.Lambda()):
            return _EXPRESSION
        case terms.Apply() | terms.Fix():
            return _APPLY
    return _FIELD_ACCESS


def _bind(names, name):
    """`names` with a binder entered; None stays None."""
    return None if names is None else (*names, name)


def _bruijn_name(index, names):
    """The name of the binder `index` lambdas out. `$index` if `names` is None (naming is off),
    doesn't reach it, or an inner binder shadows it."""
    if names is None or index >= len(names):
        return f'${index}'
    name = names[-1 - index]
    return f'${index}' if name in names[len(names) - index :] else _name(name)


def _flat(term, level, names):
    """`names` holds the binder names in scope, innermost last, for naming a BruijnIndex; None prints `$i`."""
    match term:
        case terms.Variable(name=name):
            text = _name(name)
        case terms.BruijnIndex(index=index):
            text = _bruijn_name(index, names)
        case terms.Lambda(param_name=name, param_form=form, body=body):
            text = f'{_name(name)}{_form_suffix(form)} → {_flat(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            value = _flat(argument, _EXPRESSION, names)
            text = f'let {_name(name)}{_form_suffix(form)} = {value} in {_flat(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = f'{_flat(function, _APPLY, names)} {_flat(argument, _FIELD_ACCESS, names)}'
        case terms.Struct(fields=fields):
            text = '{' + ', '.join(f'{_name(f.label)} = {_flat(f.value, _EXPRESSION, names)}' for f in fields) + '}'
        case terms.FieldAccess(struct=struct, label=label):
            text = f'{_flat(struct, _FIELD_ACCESS, names)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = (
                f'if {_flat(c, _EXPRESSION, names)} then {_flat(t, _EXPRESSION, names)}'
                f' else {_flat(e, _EXPRESSION, names)}'
            )
        case terms.Fix(function=function):
            text = f'fix {_flat(function, _FIELD_ACCESS, names)}'
        case terms.ByteArray(value=value, form=form):
            hex_groups = ' '.join(value[i : i + 4].hex() for i in range(0, len(value), 4))
            text = f'[{hex_groups}]{_form_suffix(form)}'
        case syntax.ErrorTerm():
            text = 'error'
        case _:
            raise AssertionError(term)
    return f'({text})' if level > _loosest(term) else text


def _pretty(term, level, depth, column, width, indent, names):
    """`depth` counts indentation steps for new lines; `column` is where the term starts on the current line."""

    def sub(child, child_level, child_depth, child_column, child_names=names):
        return _pretty(child, child_level, child_depth, child_column, width, indent, child_names)

    flat = _flat(term, level, names)
    if column + len(flat) <= width:
        return flat
    grouped = level > _loosest(term)
    column += grouped
    pad = ' ' * (indent * depth)
    inner = ' ' * (indent * (depth + 1))
    match term:
        case terms.Lambda(param_name=name, param_form=form, body=body):
            header = f'{_name(name)}{_form_suffix(form)} →'
            body_names = _bind(names, name)
            if isinstance(body, terms.Lambda) or (isinstance(body, terms.Struct) and body.fields):
                text = f'{header} {sub(body, _EXPRESSION, depth, column + len(header) + 1, body_names)}'
            else:
                text = f'{header}\n{inner}{sub(body, _EXPRESSION, depth + 1, len(inner), body_names)}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            header = f'let {_name(name)}{_form_suffix(form)} = '
            value = sub(argument, _EXPRESSION, depth, column + len(header))
            text = f'{header}{value} in\n{pad}{sub(body, _EXPRESSION, depth, len(pad), _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = (
                f'{sub(function, _APPLY, depth, column)}\n{inner}{sub(argument, _FIELD_ACCESS, depth + 1, len(inner))}'
            )
        case terms.Struct(fields=fields):
            lines = []
            for f in fields:
                head = f'{inner}{_name(f.label)} = '
                lines.append(f'{head}{sub(f.value, _EXPRESSION, depth + 1, len(head))},')
            text = '{\n' + '\n'.join(lines) + '\n' + pad + '}'
        case terms.FieldAccess(struct=struct, label=label):
            text = f'{sub(struct, _FIELD_ACCESS, depth, column)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = (
                f'if {sub(c, _EXPRESSION, depth, column + 3)}\n'
                f'{pad}then {sub(t, _EXPRESSION, depth, len(pad) + 5)}\n'
                f'{pad}else {sub(e, _EXPRESSION, depth, len(pad) + 5)}'
            )
        case terms.Fix(function=function):
            text = f'fix {sub(function, _FIELD_ACCESS, depth, column + 4)}'
        case _:
            return flat
    return f'({text})' if grouped else text


def _form_suffix(form):
    """`: form` after a lambda param or byte array, where an arrow form needs parentheses."""
    return '' if form == UNKNOWN_FORM else ': ' + _pretty_form(form, arrow=False)


def _pretty_form(form, *, arrow):
    match form:
        case str():
            return _name(form)
        case terms.FunctionForm(param=param, result=result):
            text = f'{_pretty_form(param, arrow=False)} → {_pretty_form(result, arrow=True)}'
            return text if arrow else f'({text})'
        case terms.StructForm(fields=fields):
            parts = (
                _name(label) + ('' if f == UNKNOWN_FORM else ': ' + _pretty_form(f, arrow=True)) for label, f in fields
            )
            return '{' + ', '.join(parts) + '}'
    raise AssertionError(form)


def _name(name):
    if name not in RESERVED and name[0] in IDENT_START and all(c in IDENT_CONTINUE for c in name):
        return name
    escaped = ''.join(
        '\\' + c if c in '"\\' else c if c.isprintable() else '\\u{' + format(ord(c), 'x') + '}' for c in name
    )
    return f'"{escaped}"'
