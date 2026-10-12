# Plan: `if` is sugar for a struct applied to a condition

Status: **implemented**.

## Steps

One commit each. Each step leaves `hatch run full-check` green.

- [x] 1. Write the plan, docs only (`oymomo: plan if as struct apply`)
- [x] 2. BANF accepts `{e, t} c` as a branch, additive (`oymomo: a struct applied to an atom is a branch`)
- [x] 3. `if` parses to `{e, t} c`, and `If` goes (`oymomo: if is sugar for {else, then} c`)
- [x] 4. Write the switch plan, docs only (`oymomo: plan switch`)

Step 2 leaves `If` in place, so every existing test still passes. Step 3 changes no
syntax: `if c then t else e` still parses and still prints. Only the term behind it changes.
Step 4 writes [plan_switch.md](plan_switch.md) for the N-way case, which this plan leaves out (decision 12).

## Goal

**One way to choose: a struct applied to an index.** The struct apply rule already
covers what `If` does:

```
{a, b} [00]                  ⇒  a
{a, b} [01]                  ⇒  b
if [00] then t else e        ⇒  e      same as {e, t} [00]
if [01] then t else e        ⇒  t      same as {e, t} [01]
```

So `if c then t else e` is `{e, t} c`. The else arm comes first because `[00]` (false)
picks field 0. `If` is a term with cases in 7 modules (`terms`, `grammar`, `bruijn`,
`banf_reduce`, `banf_rename`, `banf_translate`, `printer`), all for a special case of a
rule that already exists.

After this plan, `if` is only syntax. The parser expands it, and the printer folds it back:

```
if c then t else e           parses to   {e, t} c
{e, t} c                     prints as   if c then t else e
{a, b} [01]                  prints as   if [01] then b else a
{x = a, y = b} c             prints as   {x = a, y = b} c       labeled: not an if
{a, b, d} c                  prints as   {a, b, d} c            3 fields: not an if
```

## Decisions

### Syntax

1. **`if c then t else e` stays, as sugar.** `grammar._if` builds
   `Apply(Struct([Field('', e), Field('', t)]), c)`. The `rn.IF` rule, its precedence
   (expression level, reaching as far right as it can), and the reserved words
   `if then else` are unchanged.

   ```python
   def _if(c):
       """`if c then t else e` is `{e, t} c`: `[00]` picks field 0, the else arm."""
       condition, then_clause, else_clause = c.values
       location = _location(c)
       struct = terms.Struct(
           fields=[
               terms.Field(label='', value=else_clause, location=getattr(else_clause, 'location', None)),
               terms.Field(label='', value=then_clause, location=getattr(then_clause, 'location', None)),
           ],
           location=location,
       )
       return terms.Apply(function=struct, argument=condition, location=location)
   ```

2. **The printer prints by shape, always.** `{a, b} c` is the general case that prints
   back as `if`. An `Apply` whose function is a `Struct` with exactly two fields, both
   unlabeled, prints as `if <argument> then <field 1> else <field 0>`, whatever the
   argument is. That is exactly what `_if` builds, so `parse(print(t)) == t` for every term.
   - A literal argument is not special: `{'1', '2'} [01]` prints as
     `if [01] then '2' else '1'`, and a stuck `{a, b} [02]:'i8'` as
     `if [02]:'i8' then b else a`. One rule, no exceptions.
   - A labeled field would be lost by `if`, so `{x = a, y = b} c` prints as it is.
3. **A shape helper** tells the printer when to print `if`. BANF does not use it, since it accepts labels (decision 10):

   ```python
   # bruijn.py
   def branch(term: syntax.Term) -> tuple[syntax.Term, syntax.Term, syntax.Term] | None:
       """`(condition, then, else)` if `term` is `{e, t} c` with both fields unlabeled, else None."""
       match term:
           case terms.Apply(
               function=terms.Struct(fields=[terms.Field(label='', value=e), terms.Field(label='', value=t)]),
               argument=c,
           ):
               return c, t, e
       return None
   ```

### Kernel

4. **No new reduction rule.** `bruijn.reduce` already steps `Apply(Struct, index)`. The
   `If` case and `_TRUE`/`_FALSE` go.
5. **The condition is read by `bruijn.index_value`**, as for any struct apply: unsigned
   little-endian, any length, with a form ignored. `if [0100] then t else e` ⇒ `t`, which
   `If` didn't accept (it wanted exactly one byte). `if [02] ...` stays stuck, as before.
6. **The arms stay lazy.** `banf_reduce._head` makes the index the head of an
   `Apply(Struct, _)`, so `whnf` reduces only `c`, never `e` or `t`. That is what
   `If(condition=head)` did.

### BANF (step 2)

7. **A struct literal applied to an atom, in tail position, is a `Branch`.**
   `banf_reduce.terminal` gets the case that `If` has today:

   ```python
   case terms.Apply(function=terms.Struct(fields=fields) as struct, argument=condition):
       return replace(
           term,
           function=replace(struct, fields=[replace(f, value=self.jump(f.value)) for f in fields]),
           argument=self.atom(condition),
       )
   ```

8. **Such an apply is not an op**, so a let-bound branch is substituted, as a let-bound
   `if` is today (`let t = if args.c then f.a {} else f.b {} in t` is fine). `_is_op`
   adds:

   ```python
   case terms.Apply(function=terms.Struct()):
       return False
   ```

   This loses nothing: a struct literal picked by a run-time index is not a BANF op
   today either. `GetIndex` needs an atom callee and a literal index.

9. **`banf_translate.body` reads it as a `Branch`**, with field 1 as `then` and field 0
   as `else`:

   ```python
   case terms.Apply(function=terms.Struct(fields=[else_field, then_field]), argument=condition):
       atom = self.atom(condition, block)
       else_jump = self.jump(else_field.value, block)
       then_jump = self.jump(then_field.value, block)
       if then_jump is None or else_jump is None:
           raise TranslationError('Both branches of an if must be jumps, such as blocks.then0 {}.', location)
       if then_jump[0] == else_jump[0]:
           raise TranslationError('Both branches of an if jump to the same block.', location)
       return banf.Branch(atom, *then_jump, *else_jump, location)
   case terms.Apply(function=terms.Struct()):
       raise TranslationError('A branch needs two fields, {else, then}.', location)
   ```

   It must come before the `isinstance(term, terms.Apply | ...)` fallback. In `op`, a
   `case terms.Apply(function=terms.Struct())`, placed before the generic cases, raises
   `'An if must be in tail position.'`. The error messages keep saying `if`, since
   that is what the source says.
10. **Field labels are ignored in BANF**, as struct apply ignores them. Only the
    position matters, so `{x = f.b {}, y = f.a {}} c` is also a branch. It just doesn't
    print as `if`: only the printer needs unlabeled fields (decision 2).
11. **The `i1` check stays** (`banf_terms.verify`: `Branch condition must be i1`).

### Scope

12. **A branch has exactly two fields.** `banf_translate` rejects any other count with
    `'A branch needs two fields, {else, then}.'`. The kernel already reduces
    `{a, b, c} [02]`; only BANF limits the count. Allowing N fields is an N-way switch,
    which needs a new terminator, a selector form, a default, and a rule for repeated
    targets. That is a feature, while this plan is a refactor, so it gets its own plan
    (step 4).

### Removal (step 3)

13. **`terms.If` goes**, along with every `If` case. The printer's `if` cases now match
    `bruijn.branch(term)` instead of `terms.If`, so `_compact`, `_flat`, `_pretty`,
    `_has_let_chain` and `_loosest` keep their layout. A branch prints at the
    expression level, as `If` did.

## Implementation steps

### Step 2: BANF accepts `{e, t} c` as a branch

| File | Change |
|---|---|
| [banf_reduce.py](../src/oymo/oymomo/banf_reduce.py) | `terminal`: struct-apply case (decision 7). `_is_op`: `Apply(Struct)` is not an op (decision 8). |
| [banf_translate.py](../src/oymo/oymomo/banf_translate.py) | `body`: struct-apply branch (decision 9). `op`: tail-position error. |
| tests | Add a `{e, t} c` copy of each BANF `if` test (see Verification). |

### Step 3: `if` is sugar, and `If` goes

| File | Change |
|---|---|
| [terms.py](../src/oymo/oymomo/terms.py#L97-L107) | Delete `If`. |
| [grammar.py](../src/oymo/oymomo/grammar.py#L146-L148) | `_if` builds `{e, t} c` (decision 1). `rn.IF`, `RESERVED` unchanged. |
| [bruijn.py](../src/oymo/oymomo/bruijn.py#L55-L56) | Delete the `If` cases in `_map_children` and `reduce`, and `_TRUE`/`_FALSE`. Add `branch` (decision 3). |
| [banf_reduce.py](../src/oymo/oymomo/banf_reduce.py#L101-L107) | Delete the `If` cases in `terminal`, `_head`, `_with_head`. |
| [banf_rename.py](../src/oymo/oymomo/banf_rename.py) | Delete the `If` case. `Apply` and `Struct` already cover a branch. |
| [banf_translate.py](../src/oymo/oymomo/banf_translate.py#L299-L342) | Delete the `If` cases in `op` and `body`. |
| [printer.py](../src/oymo/oymomo/printer.py) | In `_compact`, `_flat`, `_pretty`, `_has_let_chain`, `_loosest`: `case terms.If(...)` becomes `case terms.Apply() if (b := bruijn.branch(term))`, placed before the generic `Apply` case. |
| tests | `bruijn_test.test_reduce_if_sees_through_a_form` builds `If` directly: build it with `grammar.parse` or a `Struct` instead. Add printer round-trip tests (decision 2). The other `if` tests parse source, so they stay as they are. |
| [notes.md](notes.md#L527-L530) | The **If** section: `if` is sugar for `{e, t} c`, with the printing rule. The `reduce` table (l. 798): the `if` row points at struct apply. Heads (l. 1248): the head of `if c ...` is still `c`, through the struct apply rule. The BANF shape grammar (l. 1295) and the tail-position rules (l. 1404, 1431-1437) stay, worded in terms of `{e, t} c`. |

### Step 4: Write the switch plan

Docs only: [plan_switch.md](plan_switch.md), and a row for it under **Open** in
[plans.md](plans.md). It starts from decision 12: `{a0, a1, ..., an} i` in tail position,
with every field a jump, is an N-way jump. It must decide:

- **The BANF terminator:** a new `Switch`, or `Branch` generalized to N targets.
- **The selector's form:** `i8`, `i32`, any integer, or only some. `i1` with two fields
  stays a `Branch`.
- **An index past the last field:** LLVM `switch` needs a default. It could be
  `unreachable`, the last field, or an error the source must rule out.
- **Repeated targets:** two fields that jump to the same block are rejected for `if`,
  because an LLVM phi can't tell the two edges apart. With N fields, several cases
  sharing one block is normal, so the rule needs a real design: for example, the
  same target only with the same args, lowered to one edge.
- **Printing:** how BANF and the oymomo printer lay out an N-way jump.
- **LLVM:** lowering to `switch`, with case values from the field positions.

## Verification

- Step 2: for each BANF `if` test in `banf_reduce_test`, `banf_translate_test` and
  `llvm_translate_test`, add the same test written as `{e, t} c`, expecting the same
  BANF/LLVM. New tests:
  - a let-bound branch is substituted;
  - a 3-field struct is rejected;
  - a labeled struct is still a branch (`{x = f.b {}, y = f.a {}} args.c`);
  - a field that isn't a jump is rejected;
  - two fields jumping to the same block are rejected.
- Step 3:
  - `grammar.parse('if c then t else e') == grammar.parse('{e, t} c')`.
  - Printer: `{e, t} c` prints as `if c then t else e`, and so do `{'1', '2'} [01]`
    (`if [01] then '2' else '1'`) and the stuck `{a, b} [02]:'i8'`. `{x = a, y = b} c`
    and `{a, b, d} c` print as written. `parse(print(t)) == t` for each.
  - `bruijn_test`: `if [0100] then a else b` ⇒ `a`, and `if [02] ...` is stuck.
  - Every existing `if` test passes unchanged, except the one that builds `If`.
- Each step, the docs-only ones included, must pass this from `oymo/` before its commit:

  ```bash
  hatch run full-check
  ```

  It runs `hatch check --fix`, then `hatch test`.
