# Plan: a struct of jumps applied to an integer is a switch

Status: **proposed**. Open questions below.

## Steps

One commit each. Each step leaves `hatch run full-check` green. Details are in
[Implementation steps](#implementation-steps).

- [ ] 1. BANF `Switch` terminator, verified and lowered to LLVM `switch`, additive (`oymomo: banf Switch terminator`)
- [ ] 2. `{a0, a1, ..., an} i` with three or more fields is a `Switch` (`oymomo: a struct of jumps applied to an index is a switch`)
- [ ] 3. A switch may repeat a target with the same args (`oymomo: a switch may repeat a target`)

Step 1 only adds BANF and LLVM code, tested on BANF modules built directly. Step 2 is
the only step that changes what oymomo source means. Step 3 is independent of step 2
and could be dropped. Built on [plan_if_as_struct_apply.md](implemented/plan_if_as_struct_apply.md):
`if c then t else e` is `{e, t} c`, and in tail position a two-field struct of jumps
applied to an atom is a BANF `Branch` (its decision 12 leaves out other counts).

## Goal

**A struct of jumps applied to a run-time index jumps to the field at that index.**
The kernel already gives `{a0, ..., an} i` that meaning for a literal `i`. BANF keeps it
when `i` is a value, as it does for two fields:

```
{f.b {}, f.a {}} args.c                      branch c, a(), b()            today: i1, two fields
{f.a {}, f.b {}, f.c {x = args.x}} args.k    switch k, a(), b(), c(x)      after step 2: i8 k
{f.a {}, f.b {}, f.a {}} args.k              switch k, a(), b(), a()       after step 3
{f.a {}} args.k                              error: use a jump
```

In LLVM, `switch k, a(), b(), c(x)` is:

```
switch i8 %"k", label %"unreachable" [i8 0, label %"a"  i8 1, label %"b"  i8 2, label %"c"]
```

Today the second line is "A branch needs two fields, {else, then}.". A choice among N
blocks needs N-1 compares and branches, each in its own block.

## Decisions

### BANF (step 1)

1. **A new terminator, `Switch`; `Branch` stays.**

   ```python
   @dataclass
   class Switch:
       selector: Atom
       targets: list[tuple[str, list[Atom]]]  # target i is taken when selector == i
       location: Location | None = field(default=None, compare=False)

   type Terminator = Jump | Branch | Switch | Return
   ```

   `Branch` keeps its printing (`branch c, a(), b()`), its `i1` check and its `br`
   lowering, so every `if` stays exactly as it is. Merging the two would change every
   printed BANF branch and every LLVM `br` for no gain.
2. **The selector is an integer form, `iN`, and N fields must fit in it.**
   `verify` rejects a non-integer selector ("Switch selector must be an integer form,
   got {x: i8}.") and more targets than the form has values: `i1` holds 2, `i8` 256.
   A switch on `i1` with two targets is accepted. Translation never makes one (step 2
   makes a `Branch`), but BANF doesn't need to forbid it.
3. **Target `k` is taken when the selector equals `k`**, read as unsigned, as
   `bruijn.index_value` reads an index. A case value is the field's position, so it is
   always in range for the form (decision 2).
4. **An index past the last target is undefined: the `switch` default is an
   `unreachable` block.** In the kernel such an apply is stuck, so it has no meaning
   to keep. See the open question: it could be an error the source must rule out, or
   the last target.
5. **Printing:** `switch k, a(), b(), c(x)`: the selector, then the targets in order,
   like `branch`.

### LLVM (step 1)

6. **`switch` with one case per target**, in order, and a default block that holds
   only `unreachable`. That block is added once per function, only if some switch
   needs it, under a label no BANF block can have.
7. **Phis count edges, not blocks**, as today: `_successors` returns one entry per
   target, so `predecessors` already counts a switch's targets one by one.

### Translation (step 2)

8. **`{a0, ..., an} i` in tail position with three or more fields is a `Switch`.** Two
   fields stay a `Branch` (decision 1). One field is an error: "A switch needs two or
   more fields; one is a jump." Labels are ignored, as they are for a branch.
9. **`banf_reduce` needs no change.** Its `terminal` case already reduces every field
   of `{...} c` to a jump and `c` to an atom, whatever the count. `_is_op` already makes
   a let-bound one substitute into the tail.
10. **The oymomo printer adds no sugar.** `{f.a {}, f.b {}, f.c {}} args.k` prints as
    written. A `case`/`match` syntax would be its own plan.

### Repeated targets (step 3)

11. **A switch may name a target more than once, only with the same args.**
    `{f.a {}, f.b {}, f.a {}} args.k` is fine; `{f.a {x = [01]: 'i8'}, f.b {}, f.a {x =
    [02]: 'i8'}} args.k` is "A switch passes different args to 'a'." An LLVM phi needs
    one entry per edge, and entries from the same block must have the same value, so
    the same args are the only case LLVM can express.
12. **`Branch` keeps rejecting the same target twice.** Allowing it would be the same
    rule; it is left out so that `if` stays as it is. It could follow later.

## Affected modules

| Module | Step | Change |
|---|---|---|
| [banf_terms.py](../src/oymo/oymomo/banf_terms.py) | 1 | `Switch`, `Terminator`, `_verify_function` (decisions 2, 3), `show_terminator` (decision 5). |
| [llvm_translate.py](../src/oymo/oymomo/llvm_translate.py) | 1 | `_successors`, `terminator`: `builder.switch` with `add_case` per target; the `unreachable` default block (decision 6). |
| [banf_translate.py](../src/oymo/oymomo/banf_translate.py) | 2 | `body`: three or more fields make a `Switch`; one field is an error (decision 8). |
| [banf_terms.py](../src/oymo/oymomo/banf_terms.py), [banf_translate.py](../src/oymo/oymomo/banf_translate.py) | 3 | Accept a repeated target with equal args; reject different args (decision 11). |
| [notes.md](notes.md) | 2, 3 | The BANF terminators, the shape grammar's branch line, the tail-position rules, the errors table. |

## Open questions

> [!IMPORTANT]
> **What happens when the index is past the last target?** The kernel has no answer (the
> apply is stuck), and LLVM `switch` needs a default.
> - **`unreachable` (this plan).** No cost. It is undefined behavior, which
>   [plan_banf_explicit.md](implemented/plan_banf_explicit.md) ("no defaults") may argue against.
> - **The last target.** Defined, but it gives a meaning the kernel doesn't have:
>   `{a, b, c} [07]` is stuck, while its BANF would jump to `c`.
> - **An error unless the form has exactly N values** (four targets on `i2`). Safe
>   and explicit, but it needs odd forms, or padding fields, in most programs.

> [!NOTE]
> **Which integer forms can be selectors?** This plan takes any `iN` that LLVM translation
> accepts. Should `i1` with two targets be rejected in BANF, so that a two-way choice
> on `i1` is always a `Branch`?

## Implementation steps

### Step 1: BANF `Switch` terminator

- `banf_terms`: the class, the `Terminator` union, verification and printing.
- `llvm_translate`: lowering, and the `unreachable` default block.
- Tests build modules directly, as `test_rejects_branch_with_same_target_twice` does:
  - printing: `switch k, a(), b(), c(x)`;
  - verify: a non-integer selector, too many targets for `i1`, a wrong arg count for a
    target;
  - LLVM: the IR of a three-way switch whose targets join with phis, checked with
    `llvm.parse_assembly(...).verify()`.

### Step 2: a struct of jumps applied to an index is a switch

- `banf_translate.body`: the `Apply(Struct)` case splits on the field count: two →
  `Branch`, three or more → `Switch`, one → error.
- Tests from oymomo source: a three-way and a four-way switch to BANF and to LLVM; a
  let-bound switch; labels ignored; one field; a field that isn't a jump; the selector
  form checked.
- `notes.md`.

### Step 3: a switch may repeat a target

- `banf_terms.verify` and `banf_translate`: equal args are accepted, different args
  rejected.
- `llvm_translate`: a repeated target adds one phi entry per edge, all with the same value.
- Tests: two cases to one join block, checked by LLVM's verifier; different args
  rejected.

## Verification

- Each step: `hatch run full-check` from `oymo/`.
- The LLVM tests run `llvm.parse_assembly(text).verify()`, as `ir_text` does.
- After step 2, every existing `if` test passes unchanged: two fields are still a
  `Branch`.
