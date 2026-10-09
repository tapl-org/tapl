# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Renders oymomo terms and forms as text.

The default rendering is compact: one line, with parentheses only where the grammar
needs them. Neither mode prints an omitted (`Void`) form. With `pretty=True` the result is
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
from oymo.oymomo.grammar import ASCII_TEXT, RESERVED

# Binding levels, loosest first. A term printed where a tighter level is needed gets parentheses.
_EXPRESSION, _FORMED, _APPLY, _ARROW, _PROJECT = range(5)

# A byte array longer than this prints as hex even if its bytes are text.
_MAX_TEXT_BYTES = 128


def show(
    term: syntax.Term, *, pretty: bool = False, name_indices: bool = False, width: int = 80, indent: int = 2
) -> str:
    """`name_indices` prints a BruijnIndex as its binder's name where that is safe.
    `width` (columns) and `indent` (spaces per level) only affect pretty output."""
    names = () if name_indices else None
    return _pretty(term, _EXPRESSION, 0, 0, width, indent, names) if pretty else _compact(term, names)


def show_form(form: syntax.Term, *, pretty: bool = False) -> str:
    """`form` as it is written after `:`."""
    return _form_text(form, None, compact=not pretty)


def _compact(term, names, level=_EXPRESSION):
    """Like `_flat`, but `:form` without a space, and bytes ungrouped."""
    match term:
        case terms.Variable(name=name):
            text = _name(name)
        case terms.BruijnIndex(index=index):
            text = _bruijn_name(index, names)
        case terms.Lambda(param_name=name, param_form=form, body=body):
            text = f'{_name(name)}{_compact_suffix(form, names)} → {_compact(body, _bind(names, name))}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            value = _compact(argument, names)
            suffix = _compact_suffix(form, names)
            text = f'let {_name(name)}{suffix} = {value} in {_compact(body, _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = f'{_compact(function, names, _APPLY)} {_compact(argument, names, _ARROW)}'
        case terms.FunctionForm(param=param, result=result):
            text = f'{_compact(param, names, _PROJECT)} ⇒ {_compact(result, names, _ARROW)}'
        case terms.Struct(fields=fields):
            text = '{' + ', '.join(f'{_name(f.label)} = {_compact(f.value, names)}' for f in fields) + '}'
        case terms.Project(struct=struct, label=label):
            text = f'{_compact(struct, names, _PROJECT)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = f'if {_compact(c, names)} then {_compact(t, names)} else {_compact(e, names)}'
        case terms.Fix(function=function):
            text = f'fix {_compact(function, names, _ARROW)}'
        case terms.ByteArray(value=value):
            text = _bytes_text(value, grouped=False)
        case terms.Formed(term=inner, form=form):
            inner_text = _formed_term(inner, lambda t, level: _compact(t, names, level), grouped=False)
            text = f'{inner_text}:{_compact(form, names, _FORMED)}'
        case syntax.ErrorTerm():
            text = 'error'
        case _:
            raise AssertionError(term)
    return f'({text})' if level > _loosest(term) else text


def _bytes_text(value, *, grouped, text=True):
    """`'text'` if `text`, at most `_MAX_TEXT_BYTES` long, and all bytes are ASCII text;
    otherwise `[hex]`, in groups of four if `grouped`."""
    if text and len(value) <= _MAX_TEXT_BYTES and all(chr(b) in ASCII_TEXT for b in value):
        return "'" + value.decode('ascii') + "'"
    if grouped:
        return '[' + ' '.join(value[i : i + 4].hex() for i in range(0, len(value), 4)) + ']'
    return f'[{value.hex()}]'


def _compact_suffix(form, names):
    """`:form` after a name; nothing for an omitted form."""
    return '' if form is terms.Void else ':' + _form_text(form, names, compact=True)


def _form_text(form, names, *, compact):
    """`form` as written after a binder's `:`. A struct, a byte array (with its own form or not)
    or a function form is written as it is; any other term goes in parentheses."""
    if isinstance(form, terms.FunctionForm):
        if _is_formed_byte_array(form.param):
            # `[00]:'i8' ⇒ R` would read as `[00] : ('i8' ⇒ R)`.
            param = form.param
            show = _compact(param, names) if compact else _flat(param, _EXPRESSION, names)
            param_text = f'({show})'
        else:
            param_text = _form_atom_text(form.param, names, compact=compact)
        return f'{param_text} ⇒ {_form_text(form.result, names, compact=compact)}'
    return _form_atom_text(form, names, compact=compact)


def _form_atom_text(form, names, *, compact):
    if _is_formed_byte_array(form):
        bytes_text = _bytes_text(form.term.value, grouped=not compact, text=False)
        return f'{bytes_text}{":" if compact else ": "}{_form_text(form.form, names, compact=compact)}'
    if isinstance(form, (terms.Struct, terms.ByteArray)):
        return _compact(form, names, _PROJECT) if compact else _flat(form, _PROJECT, names)
    return f'({_compact(form, names) if compact else _flat(form, _EXPRESSION, names)})'


def _is_formed_byte_array(term):
    return isinstance(term, terms.Formed) and isinstance(term.term, terms.ByteArray)


def _formed_term(term, show, *, grouped):
    """The `t` of `t : form`. A byte array with a form prints its bytes as hex."""
    if isinstance(term, terms.ByteArray):
        return _bytes_text(term.value, grouped=grouped, text=False)
    return show(term, _APPLY)


def _loosest(term):
    """The loosest level `term` can be printed at without parentheses."""
    match term:
        case terms.Lambda() | terms.If() | terms.Apply(function=terms.Lambda()):
            return _EXPRESSION
        case terms.Formed():
            return _FORMED
        case terms.FunctionForm():
            return _ARROW
        case terms.Apply() | terms.Fix():
            return _APPLY
    return _PROJECT


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
            text = f'{_name(name)}{_form_suffix(form, names)} → {_flat(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            value = _flat(argument, _EXPRESSION, names)
            suffix = _form_suffix(form, names)
            text = f'let {_name(name)}{suffix} = {value} in {_flat(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = f'{_flat(function, _APPLY, names)} {_flat(argument, _ARROW, names)}'
        case terms.FunctionForm(param=param, result=result):
            text = f'{_flat(param, _PROJECT, names)} ⇒ {_flat(result, _ARROW, names)}'
        case terms.Struct(fields=fields):
            text = '{' + ', '.join(f'{_name(f.label)} = {_flat(f.value, _EXPRESSION, names)}' for f in fields) + '}'
        case terms.Project(struct=struct, label=label):
            text = f'{_flat(struct, _PROJECT, names)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = (
                f'if {_flat(c, _EXPRESSION, names)} then {_flat(t, _EXPRESSION, names)}'
                f' else {_flat(e, _EXPRESSION, names)}'
            )
        case terms.Fix(function=function):
            text = f'fix {_flat(function, _ARROW, names)}'
        case terms.ByteArray(value=value):
            text = _bytes_text(value, grouped=True)
        case terms.Formed(term=inner, form=form):
            inner_text = _formed_term(inner, lambda t, level: _flat(t, level, names), grouped=True)
            text = f'{inner_text}: {_flat(form, _FORMED, names)}'
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
            header = f'{_name(name)}{_form_suffix(form, names)} →'
            body_names = _bind(names, name)
            if isinstance(body, terms.Lambda) or (isinstance(body, terms.Struct) and body.fields):
                text = f'{header} {sub(body, _EXPRESSION, depth, column + len(header) + 1, body_names)}'
            else:
                text = f'{header}\n{inner}{sub(body, _EXPRESSION, depth + 1, len(inner), body_names)}'
        case terms.Apply(function=terms.Lambda(param_name=name, param_form=form, body=body), argument=argument):
            header = f'let {_name(name)}{_form_suffix(form, names)} = '
            value = sub(argument, _EXPRESSION, depth, column + len(header))
            text = f'{header}{value} in\n{pad}{sub(body, _EXPRESSION, depth, len(pad), _bind(names, name))}'
        case terms.Apply(function=function, argument=argument):
            text = f'{sub(function, _APPLY, depth, column)}\n{inner}{sub(argument, _ARROW, depth + 1, len(inner))}'
        case terms.Struct(fields=fields):
            lines = []
            for f in fields:
                head = f'{inner}{_name(f.label)} = '
                lines.append(f'{head}{sub(f.value, _EXPRESSION, depth + 1, len(head))},')
            text = '{\n' + '\n'.join(lines) + '\n' + pad + '}'
        case terms.Project(struct=struct, label=label):
            text = f'{sub(struct, _PROJECT, depth, column)}.{_name(label)}'
        case terms.If(condition=c, then_clause=t, else_clause=e):
            text = (
                f'if {sub(c, _EXPRESSION, depth, column + 3)}\n'
                f'{pad}then {sub(t, _EXPRESSION, depth, len(pad) + 5)}\n'
                f'{pad}else {sub(e, _EXPRESSION, depth, len(pad) + 5)}'
            )
        case terms.Fix(function=function):
            text = f'fix {sub(function, _ARROW, depth, column + 4)}'
        case _:
            return flat
    return f'({text})' if grouped else text


def _form_suffix(form, names):
    """`: form` after a lambda param; nothing for an omitted form."""
    return '' if form is terms.Void else ': ' + _form_text(form, names, compact=False)


def _name(name):
    if name not in RESERVED and name[0] in IDENT_START and all(c in IDENT_CONTINUE for c in name):
        return name
    escaped = ''.join(
        '\\' + c if c in '"\\' else c if c.isprintable() else '\\u{' + format(ord(c), 'x') + '}' for c in name
    )
    return f'"{escaped}"'
