# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


class Match:
    """Memoized result: how much input was consumed, and the action's value."""

    __slots__ = ('len', 'value')

    def __init__(self, length, value):
        self.len, self.value = length, value


MISMATCH = Match(-1, None)  # a mismatch is the sentinel, so None is a legal value


class _Skip:
    def __repr__(self):
        return 'SKIP'


SKIP = _Skip()  # a clause returning SKIP contributes nothing to a parent Seq's values


def drop(_ctx):
    """Ready-made action: consume input, contribute no value."""
    return SKIP


# ---- memo table ------------------------------------------------------------


class MemoEntry:
    def __init__(self):
        self.match = None
        self.in_progress = False
        self.left_recursion_detected = False
        self.version = 0

    def get(self, parser, clause, pos):
        # Cache miss, or entry is stale (an LR expansion bumped the version at pos)
        if self.match is None or self.version < parser.version_for_pos[pos]:
            if self.in_progress:
                # (clause, pos) is already on the call stack: left-recursive cycle.
                # Seed with MISMATCH (the fixed point) and flag the ancestor frame.
                if self.match is None:
                    self.left_recursion_detected = True
                    self.match = MISMATCH
            else:
                self.in_progress = True
                while True:
                    new = clause.match(parser, pos)
                    if self.match is not None and new.len <= self.match.len:
                        break  # no progress: fixed point reached
                    self.match = new
                    if not self.left_recursion_detected:
                        break  # not left-recursive: single evaluation
                    parser.version_for_pos[pos] += 1  # invalidate entries at pos
                    self.version = parser.version_for_pos[pos]
                self.in_progress = False
            self.version = parser.version_for_pos[pos]
        return self.match


# ---- clause base -----------------------------------------------------------


class Ctx:
    """Common part of every context. `text` is computed lazily (no slicing cost
    unless an action asks for it)."""

    __slots__ = ('_input', 'length', 'pos')

    def __init__(self, text, pos, length):
        self._input, self.pos, self.length = text, pos, length

    @property
    def end(self):
        return self.pos + self.length

    @property
    def text(self):
        return self._input[self.pos : self.pos + self.length]


class Clause:
    """action(ctx) -> value.  The ctx type depends on the clause type (see top).
    Actions must be pure and must not mutate ctx values: results are memoized,
    shared between parents, and computed speculatively (failed/discarded branches,
    every left-recursion growth iteration)."""

    def __init__(self, action=None):
        self.action = action

    def make(self, ctx):
        return Match(ctx.length, (self.action or self.default_action)(ctx))

    def default_action(self, ctx):
        raise NotImplementedError

    def match(self, parser, pos):
        raise NotImplementedError


# ---- terminals -------------------------------------------------------------


class TerminalCtx(Ctx):
    __slots__ = ()


class Char(Clause):
    def __init__(self, c, action=None):
        super().__init__(action)
        self.c = c

    def default_action(self, ctx):
        return ctx.text

    def match(self, parser, pos):
        if pos < len(parser.input) and parser.input[pos] == self.c:
            return self.make(TerminalCtx(parser.input, pos, 1))
        return MISMATCH


class Range(Clause):
    def __init__(self, lo, hi, action=None):
        super().__init__(action)
        self.lo, self.hi = lo, hi

    def default_action(self, ctx):
        return ctx.text

    def match(self, parser, pos):
        if pos < len(parser.input) and self.lo <= parser.input[pos] <= self.hi:
            return self.make(TerminalCtx(parser.input, pos, 1))
        return MISMATCH


class Str(Clause):
    def __init__(self, literal, action=None):
        super().__init__(action)
        self.literal = literal

    def default_action(self, ctx):
        return ctx.text

    def match(self, parser, pos):
        if parser.input.startswith(self.literal, pos):
            return self.make(TerminalCtx(parser.input, pos, len(self.literal)))
        return MISMATCH


class Any(Clause):
    """Matches any single character."""

    def default_action(self, ctx):
        return ctx.text

    def match(self, parser, pos):
        if pos < len(parser.input):
            return self.make(TerminalCtx(parser.input, pos, 1))
        return MISMATCH


# ---- Seq -------------------------------------------------------------------


class SeqCtx(Ctx):
    __slots__ = ('values',)  # subclause values, SKIPs removed

    def __init__(self, text, pos, length, values):
        super().__init__(text, pos, length)
        self.values = values


class Seq(Clause):
    def __init__(self, *subs, action=None):
        super().__init__(action)
        self.subs = subs

    def default_action(self, ctx):
        return ctx.values

    def match(self, parser, pos):
        values, p = [], pos
        for c in self.subs:
            m = c.match(parser, p)
            if m is MISMATCH:
                return MISMATCH
            if m.value is not SKIP:
                values.append(m.value)
            p += m.len
        return self.make(SeqCtx(parser.input, pos, p - pos, values))


# ---- First -----------------------------------------------------------------


class FirstCtx(Ctx):
    __slots__ = ('index', 'value')  # value and index of the alternative that matched

    def __init__(self, text, pos, length, value, index):
        super().__init__(text, pos, length)
        self.value, self.index = value, index


class First(Clause):
    def __init__(self, *subs, action=None):
        super().__init__(action)
        self.subs = subs

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        for i, c in enumerate(self.subs):
            m = c.match(parser, pos)
            if m is not MISMATCH:
                return self.make(FirstCtx(parser.input, pos, m.len, m.value, i))
        return MISMATCH


# ---- Ref -------------------------------------------------------------------


class RefCtx(Ctx):
    __slots__ = ('name', 'value')  # name of the referenced rule and its value

    def __init__(self, text, pos, length, value, name):
        super().__init__(text, pos, length)
        self.value, self.name = value, name


class Ref(Clause):
    """Goes through parser.match(), i.e. the memo table. Every left-recursive
    cycle passes through a Ref, so left recursion is always detected."""

    def __init__(self, name, action=None):
        super().__init__(action)
        self.name = name

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        m = parser.match(parser.rules[self.name], pos)
        if m is MISMATCH:
            return MISMATCH
        return self.make(RefCtx(parser.input, pos, m.len, m.value, self.name))


# ---- Memoized --------------------------------------------------------------


class MemoizedCtx(Ctx):
    __slots__ = ('value',)  # sub's memoized value

    def __init__(self, text, pos, length, value):
        super().__init__(text, pos, length)
        self.value = value


class Memoized(Clause):
    """Memoizes sub at each position without naming it as a rule. Only sub's
    result is memoized; this clause's own action runs on every match."""

    def __init__(self, sub, action=None):
        super().__init__(action)
        self.sub = sub

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        m = parser.match(self.sub, pos)
        if m is MISMATCH:
            return MISMATCH
        return self.make(MemoizedCtx(parser.input, pos, m.len, m.value))


# ---- repetition ------------------------------------------------------------


class RepeatCtx(Ctx):
    __slots__ = ('values',)  # one value per iteration, SKIPs removed

    def __init__(self, text, pos, length, values):
        super().__init__(text, pos, length)
        self.values = values


class _Repeat(Clause):
    min_count = 0

    def __init__(self, sub, action=None):
        super().__init__(action)
        self.sub = sub

    def default_action(self, ctx):
        return ctx.values

    def match(self, parser, pos):
        values, p, count = [], pos, 0
        while True:
            m = self.sub.match(parser, p)
            if m is MISMATCH:
                break
            count += 1
            if m.value is not SKIP:
                values.append(m.value)
            p += m.len
            if m.len == 0:
                break  # empty iteration: counts once, then stop (avoids an infinite loop)
        if count < self.min_count:
            return MISMATCH
        return self.make(RepeatCtx(parser.input, pos, p - pos, values))


class ZeroOrMore(_Repeat):
    min_count = 0


class OneOrMore(_Repeat):
    min_count = 1


# ---- Optional --------------------------------------------------------------


class OptionalCtx(Ctx):
    __slots__ = ('matched', 'value')  # value is None when not matched

    def __init__(self, text, pos, length, value, matched):
        super().__init__(text, pos, length)
        self.value, self.matched = value, matched


class Optional(Clause):
    """Default value is None when absent (not SKIP), so positions in a parent
    Seq's values stay stable. An action may return SKIP to drop it instead."""

    def __init__(self, sub, action=None):
        super().__init__(action)
        self.sub = sub

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        m = self.sub.match(parser, pos)
        if m is MISMATCH:
            return self.make(OptionalCtx(parser.input, pos, 0, None, False))
        return self.make(OptionalCtx(parser.input, pos, m.len, m.value, True))


# ---- lookahead and end of input --------------------------------------------


class AndCtx(Ctx):
    __slots__ = ('value',)  # the lookahead clause's value; nothing is consumed

    def __init__(self, text, pos, length, value):
        super().__init__(text, pos, length)
        self.value = value


class And(Clause):
    """Positive lookahead: succeeds if sub matches, consumes nothing."""

    def __init__(self, sub, action=None):
        super().__init__(action)
        self.sub = sub

    def default_action(self, _ctx):
        return SKIP

    def match(self, parser, pos):
        m = self.sub.match(parser, pos)
        if m is MISMATCH:
            return MISMATCH
        return self.make(AndCtx(parser.input, pos, 0, m.value))


class NotCtx(Ctx):
    __slots__ = ()


class Not(Clause):
    """Negative lookahead: succeeds if sub does NOT match, consumes nothing."""

    def __init__(self, sub, action=None):
        super().__init__(action)
        self.sub = sub

    def default_action(self, _ctx):
        return SKIP

    def match(self, parser, pos):
        if self.sub.match(parser, pos) is MISMATCH:
            return self.make(NotCtx(parser.input, pos, 0))
        return MISMATCH


class EofCtx(Ctx):
    __slots__ = ()


class Eof(Clause):
    def default_action(self, _ctx):
        return SKIP

    def match(self, parser, pos):
        if pos == len(parser.input):
            return self.make(EofCtx(parser.input, pos, 0))
        return MISMATCH


# ---- parser ----------------------------------------------------------------


class Parser:
    def match(self, clause, pos):
        entry = self.memo.setdefault((clause, pos), MemoEntry())
        return entry.get(self, clause, pos)

    def parse(self, text, start_rule, rules):
        """Returns (consumed_length, value), or None on mismatch."""
        self.input = text
        self.rules = rules
        self.version_for_pos = [0] * (len(text) + 1)
        self.memo = {}
        m = self.match(rules[start_rule], 0)
        return None if m is MISMATCH else (m.len, m.value)
