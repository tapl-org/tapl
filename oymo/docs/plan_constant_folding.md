# Plan: opcodes on literals fold to a constant

Status: **proposed**. No open questions.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. Opcode signatures move to a neutral `opcodes.py` (`oymomo: move opcode signatures to opcodes.py`)
- [ ] 2. Fold `add sub mul and or xor` (`oymomo: fold add, sub, mul, and, or, xor on literals`)
- [ ] 3. Fold division and shifts, except where LLVM has no defined result (`oymomo: fold division and shifts`)
- [ ] 4. Fold comparisons and conversions (`oymomo: fold comparisons and conversions`)

Step 1 comes first; steps 2 to 4 each add templates to the same evaluator, and step 2
adds the test that checks it against LLVM. Built on [plan_builtin.md](implemented/plan_builtin.md):
opcodes are built-ins (`$add_i32`), and a built-in can have a rule in
`bruijn.BUILTIN_RULES`. Step 2 also needs step 1 of
[plan_struct_pack.md](plan_struct_pack.md): a rule lists its blockers.

## Goal

**An opcode whose operands are all literals reduces to its result**, so constants
computed in oymomo code don't reach BANF as instructions:

```
$add_i32 {a = [01000000]: 'i32', b = [02000000]: 'i32'}      ⇒   [03000000]: 'i32'
$add_i32 {a = [01000000], b = [02000000]}                    ⇒   [03000000]: 'i32'
$eq_i8 {a = [07]: 'i8', b = [07]: 'i8'}                       ⇒   [01]: 'i1'
$zext_i8_i32 {value = [ff]: 'i8'}                             ⇒   [ff000000]: 'i32'
$sdiv_i32 {dividend = [07000000]: 'i32', divisor = [00000000]: 'i32'}
                                                              stays: division by zero
$add_i32 {a = args.n, b = [01000000]: 'i32'}                  stays: args.n is a run-time value
```

Today the notes say "Opcodes are not run": every opcode is an `OpcodeCall` in BANF,
even on literals, and an `if` on a computed condition is always a `branch`. After this
plan, `let c = $eq_i8 {a = [07]: 'i8', b = [07]: 'i8'} in if c then f.a {} else f.b {}`
is the jump `f.a {}`.

## Decisions

1. **Each opcode gets a rule in `bruijn.BUILTIN_RULES`, generated from its signature.**
   No new term and no new syntax: `$add_i32 {...}` is already a call of a built-in, and a
   name may be in both tables (plan_builtin decision 9). The opcode keeps its entry in
   `opcodes.OPCODES` and `llvm_opcodes.DEFAULT_OPCODES`, so a call that doesn't fold
   is still an `OpcodeCall`.
2. **Signatures and the evaluator live in a neutral `opcodes.py`.** Today's
   `banf_opcodes.py` is renamed: it holds no BANF and no LLVM, only `OpcodeSignature`,
   `OPCODES` and their generators, and imports only `terms`. So the kernel (`bruijn`),
   BANF (`banf_terms`, `banf_translate`) and LLVM (`llvm_opcodes`) all import it, and no
   layer imports one above it. The one BANF-specific line, the check that no opcode is
   named like a BANF keyword, moves to `banf_terms.py`, which prints `OpcodeCall`s.
   Rejected: `bruijn` importing `banf_opcodes` (the kernel would depend on BANF), and
   `banf_opcodes` registering rules into `bruijn.BUILTIN_RULES` (an import side effect:
   whether `$add_i32` folds would depend on what was imported).
3. **The evaluator is plain Python on integers, next to the signatures.**
   `opcodes.evaluate(signature, operands: list[int]) -> int | None` computes the
   result from the operands' unsigned values; `None` means "no defined result" (decision
   5). The rule decodes the operand bytes, calls it, and encodes the result. No LLVM, so
   `opcodes.py` stays LLVM-free (notes: "BANF does not depend on LLVM").
4. **Same result as LLVM.** The folded bytes are the bytes the compiled code would
   produce:
   - operands and results are little-endian, `(N + 7) // 8` bytes for `iN`
     (notes: "Byte arrays are bracketed hex"), so `i1` is one byte holding 0 or 1;
   - arithmetic wraps modulo `2^N`;
   - signed templates (`sdiv srem ashr slt sle sgt sge sext`) read operands as two's
     complement; the rest read them as unsigned;
   - comparisons give `i1`; `zext`, `sext` and `trunc` change the width as LLVM does.

   A test runs each template through LLVM (llvmlite's JIT on the IR `llvm_translate`
   emits) on edge operands (0, 1, the maximum, the signed minimum, -1) and compares with
   the fold, for every width.
5. **No undefined behaviour is folded.** Where LLVM gives poison or undefined
   behaviour, `evaluate` returns `None` and the call stays unreduced, exactly as today:
   - `sdiv udiv srem urem` with divisor 0;
   - `sdiv srem` of the signed minimum by -1;
   - `shl lshr ashr` by an amount of `N` or more.

   Folding never picks a value that LLVM doesn't promise.
6. **Operands must be literals of the right size; a form is optional.** The rule fires
   only when its argument is a struct whose labels are the signature's params, in order
   (as `convert` checks), and every field is a byte array literal:
   - with exactly `(N + 7) // 8` bytes, and a value below `2^N` (`i1`: `00` or `01`);
   - with no form, or with the param's form (`[01000000]: 'i32'` for an `i32` param).

   A bare literal folds: `$add_i32 {a = [01000000], b = [02000000]}` gives
   `[03000000]: 'i32'`. The opcode's signature says how to read the bytes, so a form on
   the operand adds nothing; the byte count is the check. Such a call is rejected by
   `convert` today (`Byte array: form must be written.`); after folding it is valid,
   since the result carries the form (decision 7). A *wrong* form or byte count is not
   a redex: the call stays and reaches `convert`, which reports what it reports today
   (`$add_i32 expects a: i32, got i8.`). A form is not a type, but folding a mismatched
   form would hide that error.
7. **The result has the signature's result form**: `Formed(ByteArray(bytes), result)`,
   such as `[03000000]: 'i32'` or `[01]: 'i1'`. So BANF still knows the constant's form,
   and an `if` on a folded comparison reduces by the existing `if` rule.
8. **An opcode's blockers are its argument and each of its fields.** Folding reads
   every field reduced: in `$add_i32 {a = (x -> x) [01000000]: 'i32', b = ...}` the
   field must be reduced before the rule can read it. A rule lists the parts it reads
   as blockers (plan_struct_pack decision 8), so each opcode rule uses
   `bruijn.field_blockers`: the argument, then, once it is a struct, each field in
   order. No change in `banf_shape`.

   Fields stay lazy where they are not read: only a built-in's blockers are reduced,
   and fields only once the argument is a struct. `bruijn.reduce` itself stays
   root-only: the rule only checks that the fields are already literals.
9. **BANF output changes where operands are literals.** A let whose value folds is no
   longer an op, so `banf_shape` beta-reduces it and the constant is substituted
   (notes: "a let whose value isn't an op is beta-reduced"). Lets disappear, and an `if`
   on a folded condition becomes a jump. The golden files have no opcode on literals, so
   they don't change; unit tests that use literal operands to get an `OpcodeCall` switch
   to a param operand (`args.n`). The notes' "Opcodes are not run" goes.
10. **Scope.** All templates fold: arithmetic and logic (step 2), division and shifts
    (step 3), comparisons and conversions (step 4). `GetIndex` needs nothing: a struct
    literal applied to an index already reduces as a struct apply, and `GetIndex` is only
    for a value struct, which is never a literal.

---

## Design

### A. `opcodes.py` (step 1)

`banf_opcodes.py` → `opcodes.py`, `banf_opcodes_test.py` → `opcodes_test.py`, with no
change in content except `_BANF_KEYWORDS`, which moves to `banf_terms.py`. Imports:

```
terms  ←  opcodes  ←  bruijn, banf_terms, banf_translate, llvm_opcodes
```

### B. Blockers

From plan_struct_pack step 1. `banf_shape.unblock` reduces a built-in's blockers in
order, one per step:

| Term | Reduced by `step` |
|---|---|
| `$add_i32 a`, `a` not yet a struct | `a` |
| `$add_i32 {l1 = e1, ...}` | the first field `ei` that `reduce_until_top_stable` changes |

### C. The evaluator (steps 2 to 4)

```python
def evaluate(signature: OpcodeSignature, operands: list[int]) -> int | None:
    """The unsigned result of `signature` on unsigned operands, as LLVM computes it.
    None where LLVM has no defined result."""
```

One function per template group, keyed by `signature.template`, like `llvm_opcodes._impl`:
`_BINARY`, `_COMPARE`, `_CONVERT`, each a Python function on `(bits, operands)`.

### D. The rule (step 2)

```python
def _fold(signature):
    def rule(call, argument):
        operands = _literal_operands(signature, argument)  # None unless decision 6 holds
        if operands is None:
            return None
        result = opcodes.evaluate(signature, operands)
        if result is None:
            return None
        return terms.Formed(terms.ByteArray(_encode(result, signature.result)), signature.result)
    return BuiltinRule(signature.name, field_blockers, None, rule)
```

`BUILTIN_RULES` gets one such rule per name in `opcodes.OPCODES` whose template is
folded so far.

---

## Affected modules

| Module | Step | Change |
|---|---|---|
| `banf_opcodes.py` → `opcodes.py` | 1, 2, 3, 4 | renamed (A); `evaluate` (C), a template group per step |
| `banf_terms.py`, `banf_translate.py`, `llvm_opcodes.py` | 1 | import `opcodes`; `banf_terms` gets the keyword check |
| `banf_opcodes_test.py` → `opcodes_test.py`, `llvm_translate_test.py` | 1 | renamed import |
| `bruijn.py` | 2 | the opcode rules (D), with `field_blockers` |
| `banf_shape.py` | — | none: blockers come from plan_struct_pack step 1 |
| `opcodes_test.py` or `llvm_translate_test.py` | 2 | fold vs LLVM JIT, per template and width |
| `banf_translate_test.py` | 2 | tests that need an `OpcodeCall` use a param operand |
| `docs/notes.md` | 1–4 | module table and opcode sections (`opcodes.py`); the `reduce` list, "Opcodes are not run", "Monomorphic" |
| `docs/plan_memory.md`, `docs/plan_struct_pack.md` | 1 | `banf_opcodes` → `opcodes` where they name it |

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: opcode signatures move to `opcodes.py`

- `git mv` `banf_opcodes.py` → `opcodes.py` and `banf_opcodes_test.py` →
  `opcodes_test.py`; the module docstring says it is shared by the kernel, BANF and LLVM.
- `_BANF_KEYWORDS` and its check move to `banf_terms.py`.
- Imports in `banf_terms.py`, `banf_translate.py`, `llvm_opcodes.py`,
  `llvm_translate_test.py`; the `bruijn.BUILTIN_RULES` comment.
- `docs/notes.md`: every `banf_opcodes` reference; open plans that name it.
- No behaviour change: the existing tests pass unchanged apart from imports.

Commit: `oymomo: move opcode signatures to opcodes.py`

### Step 2: fold `add sub mul and or xor`

- Needs plan_struct_pack step 1 (`field_blockers`).
- `opcodes.py`: `evaluate` for these templates. `bruijn.py`: D.
- Tests:
  - `reduce`: the goal's `$add_i32`, with forms and bare; wrapping (`$add_i8` of `ff`
    and `01` is `00`); a wrong form or byte count is stuck, a run-time operand is
    stuck, wrong labels are stuck.
  - `reduce_until_top_stable`: `$add_i32 {a = (x -> x) [01000000]: 'i32', b = …}`
    reduces the field, then folds.
  - `banf_translate`: a folded let disappears; a bare-literal `$add_i32` is accepted
    and folds; `$add_i8 {a = [01]: 'i32', b = ...}` still gives
    `$add_i8 expects a: i8, got i32.`
  - Fold vs LLVM (decision 4) for these templates, every width.
- `docs/notes.md`: "Opcodes are not run" goes; folding in the `reduce` list.

Commit: `oymomo: fold add, sub, mul, and, or, xor on literals`

### Step 3: fold division and shifts

- `opcodes.py`: `sdiv udiv srem urem shl lshr ashr`, with decision 5's guards.
- Tests: each guard is stuck (divisor 0, signed minimum by -1, shift by `N` and more);
  fold vs LLVM on the defined cases.

Commit: `oymomo: fold division and shifts`

### Step 4: fold comparisons and conversions

- `opcodes.py`: `eq ne slt sle sgt sge ult ule ugt uge`, `zext sext trunc`.
- Tests: the goal's `$eq_i8` and `$zext_i8_i32`; `sext` of `ff` to `i32` is
  `ffffffff`; `banf_translate`: an `if` on a folded comparison is a jump. Fold vs LLVM.
- Status of this plan: **implemented**; `plans.md` moves it to Closed.

Commit: `oymomo: fold comparisons and conversions`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: for every name in `opcodes.OPCODES`, `bruijn.BUILTIN_RULES` has a
rule, and the fold-vs-LLVM test passes for it on every edge operand.
