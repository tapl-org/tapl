# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Reduces a resolved oymomo term until it has BANF's shape. See docs/notes.md, `banf_reduce`.

Each position wants certain constructors. The term there is reduced with `whnf` until its
top constructor is one of them, then its own positions are visited. A term that can't get
the wanted constructor is left as it is, for `banf_translate.convert` to report.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import bruijn, terms

FUEL = 10_000


class _Reducer:
    def __init__(self, fuel: int) -> None:
        self.fuel = fuel

    def use_fuel(self, term):
        if self.fuel <= 0:
            raise bruijn.BruijnError('Did not reach BANF shape: ran out of reduction steps.', _location(term))
        self.fuel -= 1

    def reduce(self, term):
        reduced = bruijn.reduce(term)
        if reduced is not term:
            self.use_fuel(term)
        return reduced

    def step(self, term):
        """One step at the root, or else a whnf of the head. Returns `term` itself when neither changes it."""
        reduced = self.reduce(term)
        if reduced is not term:
            return reduced
        head = _head(term)
        if head is not None:
            reduced_head = self.whnf(head)
            if reduced_head is not head:
                return _with_head(term, reduced_head)
        return term

    def whnf(self, term):
        while (stepped := self.step(term)) is not term:
            term = stepped
        return term

    # Positions 1 to 5: the fixed outer structure.

    def program(self, term):
        return self.lambda_then(term, self.module_body)  # 1. module -> <body>

    def lambda_then(self, term, visit_body):
        term = self.whnf(term)
        if isinstance(term, terms.Lambda):
            term = replace(term, body=visit_body(term.body))
        return term

    def module_body(self, term):
        return self.struct_then(term, self.function)  # 2. {label = <func>, ...}

    def struct_then(self, term, visit_value):
        term = self.whnf(term)
        if isinstance(term, terms.Struct):
            term = replace(term, fields=[replace(f, value=visit_value(f.value)) for f in term.fields])
        return term

    def function(self, term):
        # 3., 4. A data definition, such as a byte array, isn't a lambda: it's only taken to whnf.
        return self.lambda_then(term, lambda body: self.struct_then(body, self.block))

    def block(self, term):
        return self.lambda_then(term, lambda body: self.block_body(body, 0))  # 5. args -> <block_body>

    # Position 6: a chain of lets ending in a terminal. `k` counts the lets since the block's
    # `args` binder, so `args` is `$k` here.

    def block_body(self, term, k):
        while True:
            match term:
                case terms.Apply(function=terms.Lambda() as let, argument=value):
                    value = self.whnf(value)
                    if _is_op(value, k):
                        value = self.op(value)
                        rest = self.block_body(let.body, k + 1)
                        return replace(term, function=replace(let, body=rest), argument=value)
                    self.use_fuel(term)
                    term = bruijn.beta(let, value)
                    continue
            stepped = self.step(term)
            if stepped is term:
                return self.terminal(term)
            term = stepped

    def terminal(self, term):
        match term:
            case terms.Apply(function=terms.Project(struct=terms.BruijnIndex()), argument=argument):
                return replace(term, argument=self.op_arg(argument))  # blocks.label <op_arg>
            case terms.Apply(function=terms.Struct(fields=fields) as struct, argument=condition):
                # A branch, `{e, t} c` or `if c then t else e`: `c` didn't reduce to an index,
                # so it's a run-time condition.
                return replace(
                    term,
                    function=replace(struct, fields=[replace(f, value=self.jump(f.value)) for f in fields]),
                    argument=self.atom(condition),
                )
        return term  # [bytes], args.label, $i, or a term left for convert.

    # Positions 7 to 9.

    def op(self, term):
        """A let's op, already in whnf, so its callee or struct (the head) is reduced too."""
        match term:
            case terms.Apply(argument=argument):
                return replace(term, argument=self.op_arg(argument))
            case terms.Struct():
                return self.atoms_of(term)
        return term

    def op_arg(self, term):
        """A Struct of atoms, or a BruijnIndex forwarding the block's `args`."""
        term = self.whnf(term)
        return self.atoms_of(term) if isinstance(term, terms.Struct) else term

    def atoms_of(self, struct):
        return replace(struct, fields=[replace(f, value=self.atom(f.value)) for f in struct.fields])

    def jump(self, term):
        term = self.whnf(term)
        match term:
            case terms.Apply(function=terms.Project(struct=terms.BruijnIndex()), argument=argument):
                return replace(term, argument=self.op_arg(argument))
        return term

    def atom(self, term):
        """A ByteArray, a let `$i`, or `args.n`: all of these are where whnf stops."""
        return self.whnf(term)


def _location(term):
    return getattr(term, 'location', None)


def _strict_builtin(term):
    """Whether `term` is `$name arg` with a strict rule: one that needs `arg` in whnf first."""
    match term:
        case terms.Apply(function=terms.Builtin(name=name)):
            builtin = bruijn.BUILTIN_RULES.get(name)
            return builtin is not None and builtin.strict
    return False


def _head(term):
    match term:
        case terms.Apply(function=terms.Struct(), argument=head):
            # A struct applied to an index: the index is the head, so it's reduced only once
            # the callee is a struct. Other arguments stay lazy. This is also an `if`'s condition.
            return head
        case terms.Apply(argument=head) if _strict_builtin(term):
            # A strict built-in's argument is its head: the rule reads it, so it must be
            # reduced first. `$fix g` is not strict, so `g` stays lazy.
            return head
        case terms.Apply(function=head) | terms.Project(struct=head) | terms.Formed(term=head):
            return head
    return None


def _with_head(term, head):
    match term:
        case terms.Apply(function=terms.Struct()):
            return replace(term, argument=head)
        case terms.Apply() if _strict_builtin(term):
            return replace(term, argument=head)
        case terms.Apply():
            return replace(term, function=head)
        case terms.Project():
            return replace(term, struct=head)
        case terms.Formed():
            return replace(term, term=head)
    raise AssertionError(term)


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
    return _Reducer(FUEL).step(term)


def whnf(term: syntax.Term, fuel: int = FUEL) -> syntax.Term:
    return _Reducer(fuel).whnf(term)


def shape(term: syntax.Term, fuel: int = FUEL) -> syntax.Term:
    """Reduces a resolved program until it has BANF's shape, as far as it can."""
    return _Reducer(fuel).program(term)
