# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Renders oymomo terms as text.

The default rendering is compact: one line, with parentheses only where the grammar
needs them. With `pretty=True` the result is oymomo source that parses back to the same
term: parentheses only where needed, and quoted names where needed. A term that doesn't
fit in `width` columns breaks: a struct puts one field per line, a lambda puts its body on
the next line (unless the body is a struct, another lambda, or a short function applied to
a lambda, so `λm. λp. m [] (λr. {` stays on one line), an apply puts its argument on the
next line (unless the argument is a lambda and the function short), and an `if` puts
`then` and `else` on their own lines. An empty byte array as an argument prints `[]`.

A struct with two unlabeled fields applied to anything, `{e, t} c`, prints as
`if c then t else e`, which parses back to it (`reduction.branch`).

An apply of a lambda, `(λx. body) e`, prints as `let x = e in body`; a broken let puts
its body on the next line, so a chain of lets reads one let per line. In pretty mode a
chain of two or more lets (and so any term containing one) always breaks, even if it fits.
A BruijnIndex prints as `$i` in both modes. With `name_indices=True` a BruijnIndex prints
as the name of its binder instead, except where an inner binder shadows that name or no
binder is in scope; there it stays `$i`, so the output still resolves back to the same term.
"""

from oymo.core import syntax
from oymo.core.terminals import IDENT_CONTINUE, IDENT_START
from oymo.oymomo import reduction, terms
from oymo.oymomo.grammar import RESERVED, is_text_char

# Binding levels, loosest first. A term printed where a tighter level is needed gets parentheses.
_EXPRESSION, _APPLY, _PROJECT = range(3)

# A byte array longer than this prints as hex even if its bytes are text.
_MAX_TEXT_BYTES = 128


def show(
    term: syntax.Term, *, pretty: bool = False, name_indices: bool = False, width: int = 80, indent: int = 2
) -> str:
    """`name_indices` prints a BruijnIndex as its binder's name where that is safe.
    `width` (columns) and `indent` (spaces per level) only affect pretty output."""
    names = () if name_indices else None
    return (
        _pretty(term, _EXPRESSION, 0, 0, width, indent, names)
        if pretty
        else _flat(term, _EXPRESSION, names, grouped=False)
    )


def _bytes_text(value, *, grouped):
    """`'text'` if at most `_MAX_TEXT_BYTES` long and all bytes are UTF-8 text;
    otherwise `[hex]`, in groups of four if `grouped`."""
    if len(value) <= _MAX_TEXT_BYTES:
        try:
            text = value.decode('utf-8')
        except UnicodeDecodeError:
            text = None
        if text is not None and all(is_text_char(c) for c in text):
            return "'" + text + "'"
    if grouped:
        return '[' + ' '.join(value[i : i + 4].hex() for i in range(0, len(value), 4)) + ']'
    return f'[{value.hex()}]'


def _loosest(term):
    """The loosest level `term` can be printed at without parentheses."""
    match term:
        case terms.Lambda() | terms.Apply(function=terms.Lambda()):
            return _EXPRESSION
        case terms.Apply() if reduction.branch(term) is not None:
            return _EXPRESSION  # printed as `if`
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


def _flat(term, level, names, *, grouped=True):
    """One line. `names` holds the binder names in scope, innermost last, for naming a
    BruijnIndex; None prints `$i`. `grouped` groups hex bytes in fours (pretty mode)."""

    def sub(child, child_level, child_names=names):
        return _flat(child, child_level, child_names, grouped=grouped)

    separator = '= ' if grouped else ' = '
    match term:
        case terms.Variable(name=name):
            text = _name(name)
        case terms.BruijnIndex(index=index):
            text = _bruijn_name(index, names)
        case terms.Lambda(param_name=name, body=body):
            text = f'λ{_name(name)}. {sub(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply(function=terms.Lambda(param_name=name, body=body), argument=argument):
            value = sub(argument, _EXPRESSION)
            text = f'let {_name(name)} = {value} in {sub(body, _EXPRESSION, _bind(names, name))}'
        case terms.Apply() if (branch := reduction.branch(term)) is not None:
            c, t, e = branch
            text = f'if {sub(c, _EXPRESSION)} then {sub(t, _EXPRESSION)} else {sub(e, _EXPRESSION)}'
        case terms.Apply(function=function, argument=terms.ByteArray(value=b'')):
            # An index (E-Index): the empty byte array is the number 0, as in `m []`.
            text = f'{sub(function, _APPLY)} []'
        case terms.Apply(function=function, argument=argument):
            text = f'{sub(function, _APPLY)} {sub(argument, _PROJECT)}'
        case terms.Struct(fields=fields):
            text = '{' + ', '.join(f'{_label(f.label, separator)}{sub(f.value, _EXPRESSION)}' for f in fields) + '}'
        case terms.Project(struct=struct, label=label):
            text = f'{sub(struct, _PROJECT)}.{_name(label)}'
        case terms.Fix(body=body):
            text = f'fix {sub(body, _PROJECT)}'
        case terms.ByteArray(value=value):
            text = _bytes_text(value, grouped=grouped)
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
    if column + len(flat) <= width and not _has_let_chain(term):
        return flat
    grouped = level > _loosest(term)
    column += grouped
    pad = ' ' * (indent * depth)
    inner = ' ' * (indent * (depth + 1))
    match term:
        case terms.Lambda(param_name=name, body=body):
            header = f'λ{_name(name)}.'
            body_names = _bind(names, name)
            if _hugs(body, names=body_names):
                text = f'{header} {sub(body, _EXPRESSION, depth, column + len(header) + 1, body_names)}'
            else:
                text = f'{header}\n{inner}{sub(body, _EXPRESSION, depth + 1, len(inner), body_names)}'
        case terms.Apply(function=terms.Lambda(param_name=name, body=body), argument=argument):
            header = f'let {_name(name)} = '
            value = sub(argument, _EXPRESSION, depth, column + len(header))
            text = f'{header}{value} in\n{pad}{sub(body, _EXPRESSION, depth, len(pad), _bind(names, name))}'
        case terms.Apply() if (branch := reduction.branch(term)) is not None:
            c, t, e = branch
            text = (
                f'if {sub(c, _EXPRESSION, depth, column + 3)}\n'
                f'{pad}then {sub(t, _EXPRESSION, depth, len(pad) + 5)}\n'
                f'{pad}else {sub(e, _EXPRESSION, depth, len(pad) + 5)}'
            )
        case terms.Apply(function=function, argument=terms.Lambda() as argument) if _fits_flat(
            function, column, width, names
        ):
            # `m [] (λr. {`: a short function stays on the line of its lambda argument.
            head = _flat(function, _APPLY, names)
            text = f'{head} {sub(argument, _PROJECT, depth, column + len(head) + 1)}'
        case terms.Apply(function=function, argument=argument):
            argument_text = sub(argument, _PROJECT, depth + 1, len(inner))
            text = f'{sub(function, _APPLY, depth, column)}\n{inner}{argument_text}'
        case terms.Struct(fields=fields):
            lines = []
            for f in fields:
                head = f'{inner}{_label(f.label, "= ")}'
                value_flat = _flat(f.value, _EXPRESSION, names)
                if (
                    f.label
                    and _is_let(f.value)
                    and (len(head) + len(value_flat) + 1 > width or _has_let_chain(f.value))
                ):
                    # A broken let goes on its own lines, below its label: `relax=` then the lets.
                    deeper = ' ' * (indent * (depth + 2))
                    lines.append(f'{head.rstrip()}\n{deeper}{sub(f.value, _EXPRESSION, depth + 2, len(deeper))},')
                    continue
                lines.append(f'{head}{sub(f.value, _EXPRESSION, depth + 1, len(head))},')
            text = '{\n' + '\n'.join(lines) + '\n' + pad + '}'
        case terms.Project(struct=struct, label=label):
            text = f'{sub(struct, _PROJECT, depth, column)}.{_name(label)}'
        case terms.Fix(body=body):
            text = f'fix {sub(body, _PROJECT, depth, column + 4)}'
        case _:
            return flat
    return f'({text})' if grouped else text


def _fits_flat(term, column, width, names):
    return column + len(_flat(term, _APPLY, names)) <= width // 2


def _hugs(body, *, names):
    """Whether a lambda's body starts on the lambda's line: another lambda, a struct, or a
    short function applied to a lambda (`λp. m [] (λr. {`)."""
    match body:
        case terms.Lambda():
            return True
        case terms.Struct(fields=fields):
            return bool(fields)
        case terms.Apply(function=terms.Lambda()):
            return False
        case terms.Apply(function=function, argument=terms.Lambda()):
            return _fits_flat(function, 0, 80, names)
    return False


def _is_let(term):
    return isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda)


def _has_let_chain(term):
    """Whether `term` contains a let whose body is a let, where `_pretty` can break it."""
    match term:
        case terms.Apply(function=terms.Lambda(body=body), argument=argument):
            return _is_let(body) or _has_let_chain(body) or _has_let_chain(argument)
        case terms.Apply(function=function, argument=argument):
            return _has_let_chain(function) or _has_let_chain(argument)
        case terms.Lambda(body=body):
            return _has_let_chain(body)
        case terms.Struct(fields=fields):
            return any(_has_let_chain(f.value) for f in fields)
        case terms.Project(struct=struct) | terms.Fix(body=struct):
            return _has_let_chain(struct)
    return False


def _label(label, separator):
    """`label` and `separator` before a field's value; nothing for an unlabeled field (`''`)."""
    return '' if label == '' else f'{_name(label)}{separator}'


def _name(name):
    if name not in RESERVED and name[0] in IDENT_START and all(c in IDENT_CONTINUE for c in name):
        return name
    escaped = ''.join(
        '\\' + c if c in '"\\' else c if c.isprintable() else '\\u{' + format(ord(c), 'x') + '}' for c in name
    )
    return f'"{escaped}"'
