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

    # Positions 1 to 6: the fixed outer structure.

    def program(self, term):
        return self.lambda_then(term, self.module)  # 1. prim -> <module>

    def lambda_then(self, term, visit_body):
        term = self.whnf(term)
        if isinstance(term, terms.Lambda):
            term = replace(term, body=visit_body(term.body))
        return term

    def module(self, term):
        return self.lambda_then(term, self.module_body)  # 2. module -> <body>

    def module_body(self, term):
        return self.struct_then(term, self.function)  # 3. {label = <func>, ...}

    def struct_then(self, term, visit_value):
        term = self.whnf(term)
        if isinstance(term, terms.Struct):
            term = replace(term, fields=[replace(f, value=visit_value(f.value)) for f in term.fields])
        return term

    def function(self, term):
        return self.lambda_then(term, lambda body: self.struct_then(body, self.block))  # 4., 5.

    def block(self, term):
        return self.lambda_then(term, lambda body: self.block_body(body, 0))  # 6. args -> <block_body>

    # Position 7: a chain of lets ending in a terminal. `k` counts the lets since the block's
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
            case terms.If(condition=condition, then_clause=then_clause, else_clause=else_clause):
                return replace(
                    term,
                    condition=self.atom(condition),
                    then_clause=self.jump(then_clause),
                    else_clause=self.jump(else_clause),
                )
        return term  # [bytes], args.label, $i, or a term left for convert.

    # Positions 8 to 10.

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


def _head(term):
    match term:
        case (
            terms.Apply(function=head) | terms.Project(struct=head) | terms.If(condition=head) | terms.Formed(term=head)
        ):
            return head
    return None


def _with_head(term, head):
    match term:
        case terms.Apply():
            return replace(term, function=head)
        case terms.Project():
            return replace(term, struct=head)
        case terms.If():
            return replace(term, condition=head)
        case terms.Formed():
            return replace(term, term=head)
    raise AssertionError(term)


def _is_op(term, k):
    """An Apply, a Struct, or a Project other than `args.label` (`$k.label`)."""
    match term:
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
