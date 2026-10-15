# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Reduces a resolved oymomo term until it has BANF's shape. See docs/notes.md, `banf_shape`.

Each position wants certain constructors. The term there is reduced with `reduce_until_top_stable`
until its top constructor can't change, then its own positions are visited. A term that can't get
the wanted constructor is left as it is, for `banf_translate.convert` to report.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import reduction, terms

FUEL = 10_000


class _Shaper:
    def __init__(self, fuel: int) -> None:
        self.fuel = fuel
        # id(term) -> (term, its reduce_until_top_stable). The term is kept so its id isn't reused.
        self.top_stable = {}

    def use_fuel(self, term):
        if self.fuel <= 0:
            raise reduction.ReductionError('Did not reach BANF shape: ran out of reduction steps.', _location(term))
        self.fuel -= 1

    # Reduction. Nothing is reduced under a Lambda, inside a Struct's fields, or in a lazy argument.

    def reduce_until_top_stable(self, term):
        """Reduces `term` until its top constructor can't change.

        Memoized by identity: the result depends only on the term (de Bruijn indices, no
        effects), and substitution shares a value instead of copying it. So an argument
        used more than once is reduced once (call-by-need), and costs fuel once.
        """
        cached = self.top_stable.get(id(term))
        if cached is not None and cached[0] is term:
            return cached[1]
        original = term
        while True:
            stepped = self.step(term)
            if stepped is term:
                break
            term = stepped
        self.top_stable[id(original)] = (original, term)
        return term

    def step(self, term):
        """Fires the rule at the root, or else unblocks it. Returns `term` itself when neither changes it."""
        reduced = reduction.reduce(term)
        if reduced is not term:
            self.use_fuel(term)
            return reduced
        return self.unblock(term)

    def unblock(self, term):
        """Runs `reduce_until_top_stable` on the blocker of `term`.

        The rule at the root of `term` may not fire yet because one part of `term` isn't
        reduced: the *blocker*. It's the callee of an Apply, the struct of a Project, or the
        index of `{...} index`. Each case below takes the blocker out and puts the reduced
        one back. Returns `term` itself when the blocker doesn't change.
        """
        match term:
            case terms.Apply(function=terms.Struct(), argument=index):
                # `{...} index` (also an `if`'s condition): picking a field needs the index.
                # Other arguments stay lazy.
                new = self.reduce_until_top_stable(index)
                return term if new is index else replace(term, argument=new)
            case terms.Apply(function=terms.ByteArray(), argument=argument):
                # An opcode call `'name' {...}`: its argument must be a struct literal whose fields
                # are byte arrays or structs. So the argument is reduced, then each of its fields.
                new = self.reduce_until_top_stable(argument)
                if isinstance(new, terms.Struct):
                    new = self.reduce_fields(new)
                return term if new is argument else replace(term, argument=new)
            case terms.Apply(function=terms.Builtin(name='fix' | 'struct_to_fields'), argument=argument):
                # `$fix` needs a lambda and `$struct_to_fields` a struct literal. Only the top is
                # reduced: the lambda's body and the struct's fields stay lazy.
                new = self.reduce_until_top_stable(argument)
                return term if new is argument else replace(term, argument=new)
            case terms.Apply(function=terms.Builtin(name='fields_to_struct'), argument=argument):
                new = self.reduce_field_list(argument)
                return term if new is argument else replace(term, argument=new)
            case terms.Apply(function=function):
                new = self.reduce_until_top_stable(function)
                return term if new is function else replace(term, function=new)
            case terms.Project(struct=struct):
                new = self.reduce_until_top_stable(struct)
                return term if new is struct else replace(term, struct=new)
            case terms.Formed(term=inner):
                # TODO: what about substitution in Formed.form?
                new = self.reduce_until_top_stable(inner)
                if isinstance(new, terms.Formed):
                    # The outer form replaces the inner one, as in `reduction.beta`: `beta` puts
                    # `a~F` in for a lazy `a`, and `a` may reduce to a formed term only now.
                    # TODO: what if new.term is also instance of terms.Formed?
                    new = new.term
                return term if new is inner else replace(term, term=new)
        return term

    def reduce_fields(self, struct):
        """`struct` with each field reduced by `reduce_until_top_stable`; `struct` itself if none changes."""
        values = [self.reduce_until_top_stable(f.value) for f in struct.fields]
        if all(new is f.value for new, f in zip(values, struct.fields, strict=True)):
            return struct
        return replace(struct, fields=[replace(f, value=new) for f, new in zip(struct.fields, values, strict=True)])

    def reduce_field_list(self, field_list):
        """Reduces what `reduction.from_field_list` reads: each node, its `more`, and if `more`
        is [01], its `label` and its `rest`. Never a `value`. `field_list` itself if nothing changes.

        A loop, not recursion, so a long (or endless) list costs fuel, not Python stack.
        """
        parents = []  # (node, position of its rest), outermost first
        node = self.reduce_until_top_stable(field_list)
        while isinstance(node, terms.Struct) and (more := reduction.field_position(node, 'more')) is not None:
            node = self.reduce_field(node, more)
            if reduction.bytes_of(node.fields[more].value) != b'\x01':
                break
            if (label := reduction.field_position(node, 'label')) is not None:
                node = self.reduce_field(node, label)
            if (rest := reduction.field_position(node, 'rest')) is None:
                break
            parents.append((node, rest))
            node = self.reduce_until_top_stable(node.fields[rest].value)
        for parent, rest in reversed(parents):
            node = _with_value(parent, rest, node)
        return node

    def reduce_field(self, struct, position):
        """`struct` with the field at `position` reduced; `struct` itself if it doesn't change."""
        return _with_value(struct, position, self.reduce_until_top_stable(struct.fields[position].value))

    # Positions 1 to 5: the fixed outer structure.

    def program(self, term):
        """1. `module -> <module_body>`"""
        term = self.reduce_until_top_stable(term)
        if not isinstance(term, terms.Lambda):
            return term
        return replace(term, body=self.module_body(term.body))

    def module_body(self, term):
        """2. `{label = <function>, ...}`"""
        term = self.reduce_until_top_stable(term)
        if not isinstance(term, terms.Struct):
            return term
        return replace(term, fields=[replace(f, value=self.function(f.value)) for f in term.fields])

    def function(self, term):
        """3. `blocks -> <blocks>`. A data definition, such as a byte array, isn't a lambda: it's only reduced."""
        term = self.reduce_until_top_stable(term)
        if not isinstance(term, terms.Lambda):
            return term
        return replace(term, body=self.blocks(term.body))

    def blocks(self, term):
        """4. `{label = <block>, ...}`"""
        term = self.reduce_until_top_stable(term)
        if not isinstance(term, terms.Struct):
            return term
        return replace(term, fields=[replace(f, value=self.block(f.value)) for f in term.fields])

    def block(self, term):
        """5. `args -> <block_body>`"""
        term = self.reduce_until_top_stable(term)
        if not isinstance(term, terms.Lambda):
            return term
        return replace(term, body=self.block_body(term.body, 0))

    # Position 6: a chain of lets ending in a terminal.

    def block_body(self, term, k):
        """`(x -> <block_body>) <op>`, or a terminal.

        `k` counts the lets since the block's `args` binder, so `args` is `$k` here.
        A let whose value isn't an op (a byte array, an index, ...) is beta-reduced away.
        """
        while True:
            match term:
                case terms.Apply(function=terms.Lambda() as let, argument=value):
                    value = self.reduce_until_top_stable(value)
                    if _is_op(value, k):
                        value = self.op(value)
                        rest = self.block_body(let.body, k + 1)
                        return replace(term, function=replace(let, body=rest), argument=value)
                    self.use_fuel(term)
                    term = reduction.beta(let, value)
                case _:
                    stepped = self.step(term)
                    if stepped is term:
                        return self.terminal(term)
                    term = stepped

    def terminal(self, term):
        match term:
            case terms.Apply(function=terms.Project(struct=terms.BruijnIndex()), argument=argument):
                # `blocks.label <op_arg>`: a jump.
                return replace(term, argument=self.op_arg(argument))
            case terms.Apply(function=terms.Struct(fields=fields) as struct, argument=condition):
                # A branch, `{e, t} c` or `if c then t else e`: `c` didn't reduce to an index,
                # so it's a run-time condition.
                jumps = [replace(f, value=self.jump(f.value)) for f in fields]
                return replace(term, function=replace(struct, fields=jumps), argument=self.atom(condition))
        return term  # [bytes], args.label, $i, or a term left for convert.

    # Positions 7 to 9.

    def op(self, term):
        """7. A let's value, already reduced by `reduce_until_top_stable`."""
        match term:
            case terms.Apply(argument=argument):
                return replace(term, argument=self.op_arg(argument))
            case terms.Struct():
                return self.struct_of_atoms(term)
        return term

    def op_arg(self, term):
        """8. A Struct of atoms, or a BruijnIndex forwarding the block's `args`."""
        term = self.reduce_until_top_stable(term)
        if isinstance(term, terms.Struct):
            return self.struct_of_atoms(term)
        return term

    def jump(self, term):
        """A branch's target: `blocks.label <op_arg>`."""
        term = self.reduce_until_top_stable(term)
        match term:
            case terms.Apply(function=terms.Project(struct=terms.BruijnIndex()), argument=argument):
                return replace(term, argument=self.op_arg(argument))
        return term

    def struct_of_atoms(self, struct):
        return replace(struct, fields=[replace(f, value=self.atom(f.value)) for f in struct.fields])

    def atom(self, term):
        """9. A ByteArray, a let `$i`, or `args.n`: all of these are where `reduce_until_top_stable` stops."""
        return self.reduce_until_top_stable(term)


def _location(term):
    return getattr(term, 'location', None)


def _with_value(struct, position, value):
    """`struct` with the value at `position` replaced; `struct` itself if `value` is already there."""
    if value is struct.fields[position].value:
        return struct
    fields = list(struct.fields)
    fields[position] = replace(fields[position], value=value)
    return replace(struct, fields=fields)


def _is_op(term, k):
    """An Apply, a Struct, or a Project other than `args.label` (`$k.label`).

    A struct literal applied to a condition (`{e, t} c`) is a branch, not an op.
    """
    match term:
        case terms.Apply(function=terms.Struct()):
            return False
        case terms.Apply() | terms.Struct():
            return True
        case terms.Project(struct=terms.BruijnIndex(index=index)):
            return index != k
        case terms.Project():
            return True
    return False


def step(term: syntax.Term) -> syntax.Term:
    return _Shaper(FUEL).step(term)


def reduce_until_top_stable(term: syntax.Term, fuel: int = FUEL) -> syntax.Term:
    return _Shaper(fuel).reduce_until_top_stable(term)


def shape(term: syntax.Term, fuel: int = FUEL) -> syntax.Term:
    """Reduces a resolved program until it has BANF's shape, as far as it can."""
    return _Shaper(fuel).program(term)
