# Plan: a struct of jumps applied to an integer is a switch

Status: **implemented**.

## Steps

One commit each. Each step leaves `hatch run full-check` green. Details are in
[Implementation steps](#implementation-steps).

- [x] 1. A struct applied to an index past its last field selects the last field, in the kernel and in BANF `GetIndex` (`oymomo: an index past the last field selects the last field`)
- [x] 2. BANF `Switch` terminator, verified and lowered to LLVM `switch`, additive (`oymomo: banf Switch terminator`)
- [x] 3. `{a0, a1, ..., an} i` with three or more fields is a `Switch` (`oymomo: a struct of jumps applied to an index is a switch`)
- [x] 4. A switch may repeat a target with the same args (`oymomo: a switch may repeat a target`)

Step 1 changes what the kernel means, so that step 2's `Switch` keeps the kernel's
meaning instead of adding one. Step 2 only adds BANF and LLVM code, tested on BANF
modules built directly. Step 3 is the only step that changes what oymomo source
translates to. Step 4 is independent of step 3 and could be dropped. Built on
[plan_if_as_struct_apply.md](plan_if_as_struct_apply.md): `if c then t
else e` is `{e, t} c`, and in tail position a two-field struct of jumps applied to an
atom is a BANF `Branch` (its decision 12 leaves out other counts).

## Goal

**A struct of jumps applied to a run-time index jumps to the field at that index.**
After step 1 the kernel gives `{a0, ..., an} i` that meaning for a literal `i`, with an
index past the last field selecting the last field (decision 1). BANF keeps it when
`i` is a value, as it does for two fields:

```
{f.b {}, f.a {}} args.c                      branch c, a(), b()            today: i1, two fields
{f.a {}, f.b {}, f.c {x = args.x}} args.k    switch k, a(), b(), c(x)      after step 3: i8 k
{f.a {}, f.b {}, f.a {}} args.k              switch k, a(), b(), a()       after step 4
{f.a {}} args.k                              error: use a jump
```

In LLVM, `switch k, a(), b(), c(x)` is:

```
switch i8 %"k", label %"c" [i8 0, label %"a"  i8 1, label %"b"]
```

Today the second line is "A branch needs two fields, {else, then}.". A choice among N
blocks needs N-1 compares and branches, each in its own block.

## Decisions

### Kernel (step 1)

1. **A struct applied to an index at or past its length selects its last field.**
   In [`reduce`](../../src/oymo/oymomo/reduction.py): `{a, b, c} [07]` → `c`, where today it
   is stuck. The last field is a catch-all: `{a, b, other} k` is case 0, case 1,
   default. With two fields, `if` gets any nonzero index as true: `{e, t} [02]` → `t`.
   The rule is still a function of the literal, so confluence
   ([plan_confluence.md](../plan_confluence.md)) is unaffected. The cost: a wrong index
   no longer leaves a stuck term to see; it silently takes the last field.
2. **`{} i` stays stuck**, as there is no last field, and so does an index that is not
   a byte array literal (`''`, `$0`), as today. Labels don't matter, as today:
   `{x = [01], y = [02]} [05]` → `[02]`. Indexing a built-in (`$f [i]`,
   [plan_builtin.md](plan_builtin.md)) is a different rule and is unchanged.
3. **BANF `GetIndex` agrees: an index past the last field reads the last field.**
   `op_form` and the LLVM lowering both use `min(index, len(fields) - 1)`; a struct
   form with no fields is still "has no field at index {index}". `GetIndex` keeps the
   index as written, so BANF printing shows the source literal.

### BANF (step 2)

4. **A new terminator, `Switch`; `Branch` stays.**

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
5. **BANF puts no requirement on the selector's form**, as the kernel puts none on an
   index. `verify` checks the selector's scope and each target's arg count, nothing
   about the selector's form or how many targets it can hold. Which selectors can be
   lowered is LLVM translation's concern (decision 11). A switch with no targets is
   rejected ("A switch needs a target."), as `{} i` is stuck: there is no last target.
6. **Target `k` is taken when the selector equals `k`**, read as unsigned, as
   `reduction.index_value` reads an index.
7. **An index past the last target takes the last target**, as in the kernel
   (decision 1). It needs no default in BANF, so it keeps
   [plan_banf_explicit.md](plan_banf_explicit.md)'s "no defaults".
   Undefined behavior (`unreachable`) and requiring exactly as many targets as the
   form has values were the other options.
8. **Printing:** `switch k, a(), b(), c(x)`: the selector, then the targets in order,
   like `branch`.

### LLVM (step 2)

9. **`switch` whose default is the last target**, with one case per other target, in
   order: `0` to `n-1` for targets `a0` to `a(n-1)`. No extra block is added.
10. **Phis count edges, not blocks**, as today: `_successors` returns one entry per
    target, so `predecessors` already counts a switch's targets one by one. The default
    is the last target's one edge.
11. **LLVM translation rejects a selector it can't lower.** The selector must be an
    integer form, `iN` ("Switch selector must be an integer form, got {x: i8}."), and
    every case value must fit in it: `n` targets need `n-1` cases, `0` to `n-2`, so `i1`
    holds 3 targets and `i8` 257 ("A switch on i1 has 4 targets; it holds 3."). Any `iN`
    LLVM translation accepts is allowed, `i1` included; translation never makes a
    two-target switch on `i1` (step 3 makes a `Branch`), but nothing forbids one.

### Translation (step 3)

12. **`{a0, ..., an} i` in tail position with three or more fields is a `Switch`.** Two
    fields stay a `Branch` (decision 4). One field is an error: "A switch needs two or
    more fields; one is a jump." No fields is "A switch needs two or more fields.", and a
    field that isn't a jump is "Every field of a switch must be a jump, such as blocks.a
    {}." Labels are ignored, as they are for a branch.
13. **`banf_reduce` needs no change.** Its `terminal` case already reduces every field
    of `{...} c` to a jump and `c` to an atom, whatever the count. `_is_op` already makes
    a let-bound one substitute into the tail.
14. **The oymomo printer adds no sugar.** `{f.a {}, f.b {}, f.c {}} args.k` prints as
    written. A `case`/`match` syntax would be its own plan.

### Repeated targets (step 4)

15. **A switch may name a target more than once, only with the same args.**
    `{f.a {}, f.b {}, f.a {}} args.k` is fine; `{f.a {x = [01]: 'i8'}, f.b {}, f.a {x =
    [02]: 'i8'}} args.k` is "A switch passes different args to 'a'." An LLVM phi needs
    one entry per edge, and entries from the same block must have the same value, so
    the same args are the only case LLVM can express.
16. **`Branch` keeps rejecting the same target twice.** Allowing it would be the same
    rule; it is left out so that `if` stays as it is. It could follow later.

## Affected modules

| Module | Step | Change |
|---|---|---|
| [reduction.py](../../src/oymo/oymomo/reduction.py) | 1 | `reduce`: the struct apply case selects the last field for an index at or past the length (decisions 1, 2). |
| [banf_terms.py](../../src/oymo/oymomo/banf_terms.py), [llvm_translate.py](../../src/oymo/oymomo/llvm_translate.py) | 1 | `GetIndex`: `op_form` and lowering read the last field for an index past it (decision 3). |
| [banf_terms.py](../../src/oymo/oymomo/banf_terms.py) | 2 | `Switch`, `Terminator`, `_verify_function` (decision 5), `show_terminator` (decision 8). |
| [llvm_translate.py](../../src/oymo/oymomo/llvm_translate.py) | 2 | `_successors`, `terminator`: `builder.switch` to the last target, with `add_case` per other target (decision 9); the selector checks (decision 11). |
| [banf_translate.py](../../src/oymo/oymomo/banf_translate.py) | 3 | `body`: three or more fields make a `Switch`; one field is an error (decision 12). |
| [banf_terms.py](../../src/oymo/oymomo/banf_terms.py), [banf_translate.py](../../src/oymo/oymomo/banf_translate.py) | 4 | Accept a repeated target with equal args; reject different args (decision 15). |
| [notes.md](../notes.md) | 1, 3, 4 | The struct apply rule; the BANF terminators, the shape grammar's branch line, the tail-position rules, the errors table. |
| [plan_struct_apply.md](plan_struct_apply.md) | 1 | A note that an index past the last field now selects it, pointing here. |

## Implementation steps

### Step 1: an index past the last field selects the last field

- `reduction.reduce`: `fields[min(position, len(fields) - 1)]` when `fields` is non-empty.
- `banf_terms.op_form` and `llvm_translate` for `GetIndex`: the same clamp.
- Tests:
  - `reduce`: `{a, b, c} [07]` → `c`, `{a, b} [0001]` → `b`, `{x = .., y = ..} [05]`
    → `y`'s value; `{} [00]` stays stuck;
  - `if` with a nonzero index other than `[01]` takes the then arm;
  - `GetIndex` past the last field: its form, and the LLVM `extractvalue` index.
- `notes.md`, `plan_struct_apply.md`.

### Step 2: BANF `Switch` terminator

- `banf_terms`: the class, the `Terminator` union, verification and printing.
- `llvm_translate`: lowering, with the last target as the default, and the selector
  checks.
- Tests build modules directly, as `test_rejects_branch_with_same_target_twice` does:
  - printing: `switch k, a(), b(), c(x)`;
  - verify: a wrong arg count for a target; a non-integer selector is accepted;
  - LLVM: the IR of a three-way switch whose targets join with phis, checked with
    `llvm.parse_assembly(...).verify()`, and the default being the last target;
  - LLVM errors: a non-integer selector, four targets on `i1`.

### Step 3: a struct of jumps applied to an index is a switch

- `banf_translate.body`: the `Apply(Struct)` case splits on the field count: two →
  `Branch`, three or more → `Switch`, one → error.
- Tests from oymomo source: a three-way and a four-way switch to BANF and to LLVM; a
  let-bound switch; labels ignored; one field; a field that isn't a jump.
- `notes.md`.

### Step 4: a switch may repeat a target

- `banf_terms.verify` and `banf_translate`: equal args are accepted, different args
  rejected.
- `llvm_translate`: a repeated target adds one phi entry per edge, all with the same value,
  including when the last target (the default) also appears as a case. Step 2 rejected any
  repeated target there ("A switch cannot name the same block twice."); this lifts it.
- Tests: two cases to one join block, checked by LLVM's verifier; different args
  rejected.

## Verification

- Each step: `hatch run full-check` from `oymo/`.
- The LLVM tests run `llvm.parse_assembly(text).verify()`, as `ir_text` does.
- After step 1, every existing struct apply test passes unchanged except ones that
  expect an index past the last field to be stuck; those are updated.
- After step 3, every existing `if` test passes unchanged: two fields are still a
  `Branch`.
