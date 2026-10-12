# Plan: opcodes on literals fold to a constant

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. A built-in rule can be strict in its argument's fields (`oymomo: a built-in rule can be strict in its fields`)
- [ ] 2. Fold `add sub mul and or xor` (`oymomo: fold add, sub, mul, and, or, xor on literals`)
- [ ] 3. Fold division and shifts, except where LLVM has no defined result (`oymomo: fold division and shifts`)
- [ ] 4. Fold comparisons and conversions (`oymomo: fold comparisons and conversions`)

Step 1 comes first; steps 2 to 4 each add templates to the same evaluator, and step 2
adds the test that checks it against LLVM. Built on
[plan_builtin.md](plan_builtin.md): opcodes are built-ins (`$add_i32`), and a built-in
can have a rule in `bruijn.BUILTIN_RULES`.

## Goal

**An opcode whose operands are all literals reduces to its result**, so constants
computed in oymomo code don't reach BANF as instructions:

```
$add_i32 {a = [01000000]: 'i32', b = [02000000]: 'i32'}      ⇒   [03000000]: 'i32'
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
   `banf_opcodes.OPCODES` and `llvm_opcodes.DEFAULT_OPCODES`, so a call that doesn't fold
   is still an `OpcodeCall`.
2. **The evaluator is plain Python on integers, next to the signatures.**
   `banf_opcodes.evaluate(signature, operands: list[int]) -> int | None` computes the
   result from the operands' unsigned values; `None` means "no defined result" (decision
   4). The rule decodes the operand bytes, calls it, and encodes the result. No LLVM, so
   `banf_opcodes.py` stays LLVM-free (notes: "BANF does not depend on LLVM").
3. **Same result as LLVM.** The folded bytes are the bytes the compiled code would
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
4. **No undefined behaviour is folded.** Where LLVM gives poison or undefined
   behaviour, `evaluate` returns `None` and the call stays unreduced, exactly as today:
   - `sdiv udiv srem urem` with divisor 0;
   - `sdiv srem` of the signed minimum by -1;
   - `shl lshr ashr` by an amount of `N` or more.

   Folding never picks a value that LLVM doesn't promise.
5. **Operands must be literals of the right size.** The rule fires only when its
   argument is a struct whose labels are the signature's params, in order (as `convert`
   checks), and every field is a byte array literal:
   - with exactly `(N + 7) // 8` bytes, and a value below `2^N` (`i1`: `00` or `01`);
   - with no form, or with the param's form (`[01000000]: 'i32'` for an `i32` param).

   Anything else is not a redex, so it stays and reaches `convert`, which reports what it
   reports today (`$add_i32 expects a: i32, got i8.`, `Byte array: form must be written.`).
   A form is not a type, but folding a mismatched form would hide that error.
6. **The result has the signature's result form**: `Formed(ByteArray(bytes), result)`,
   such as `[03000000]: 'i32'` or `[01]: 'i1'`. So BANF still knows the constant's form,
   and an `if` on a folded comparison reduces by the existing `if` rule.
7. **A rule can be strict in its argument's fields.** Folding needs every field in whnf:
   in `$add_i32 {a = (x -> x) [01000000]: 'i32', b = ...}` the field must be reduced
   before the rule can read it. Step 4 of plan_builtin made the argument a head
   (`strict=True`); this plan makes `strict` one of three values:

   | `BuiltinRule.strict` | Reduced before the rule fires |
   |---|---|
   | `NONE` (`$fix`) | nothing |
   | `ARGUMENT` | the argument, to whnf |
   | `FIELDS` (opcodes) | the argument, then each of its fields, to whnf, in order |

   Fields stay lazy where they are not read: only a strict built-in's fields are reduced,
   and only once its argument is a struct. `bruijn.reduce` itself stays root-only: the
   rule only checks that the fields are already literals.
8. **BANF output changes where operands are literals.** A let whose value folds is no
   longer an op, so `banf_reduce` beta-reduces it and the constant is substituted
   (notes: "a let whose value isn't an op is beta-reduced"). Lets disappear, and an `if`
   on a folded condition becomes a jump. The golden files have no opcode on literals, so
   they don't change; unit tests that use literal operands to get an `OpcodeCall` switch
   to a param operand (`args.n`). The notes' "Opcodes are not run" goes.
9. **Scope.** All templates fold: arithmetic and logic (step 2), division and shifts
   (step 3), comparisons and conversions (step 4). `GetIndex` needs nothing: a struct
   literal applied to an index already reduces as a struct apply, and `GetIndex` is only
   for a value struct, which is never a literal.

---

## Design

### A. Strictness (step 1)

```python
class Strictness(Enum):
    NONE = 'none'
    ARGUMENT = 'argument'
    FIELDS = 'fields'


@dataclass(frozen=True)
class BuiltinRule:
    name: str
    strict: Strictness
    needs: str | None
    rule: Callable[[syntax.Term, syntax.Term], syntax.Term | None]
```

In `banf_reduce.step`, after the root and the head:

| Term | Reduced by `step` |
|---|---|
| `$name a`, `ARGUMENT` or `FIELDS`, `a` not yet in whnf | `a` (the head, as in plan_builtin step 4) |
| `$name {l1 = e1, ...}`, `FIELDS` | the first field `ei` that `whnf` changes |

### B. The evaluator (steps 2 to 4)

```python
def evaluate(signature: OpcodeSignature, operands: list[int]) -> int | None:
    """The unsigned result of `signature` on unsigned operands, as LLVM computes it.
    None where LLVM has no defined result."""
```

One function per template group, keyed by `signature.template`, like `llvm_opcodes._impl`:
`_BINARY`, `_COMPARE`, `_CONVERT`, each a Python function on `(bits, operands)`.

### C. The rule (step 2)

```python
def _fold(signature):
    def rule(call, argument):
        operands = _literal_operands(signature, argument)  # None unless decision 5 holds
        if operands is None:
            return None
        result = banf_opcodes.evaluate(signature, operands)
        if result is None:
            return None
        return terms.Formed(terms.ByteArray(_encode(result, signature.result)), signature.result)
    return BuiltinRule(signature.name, Strictness.FIELDS, None, rule)
```

`BUILTIN_RULES` gets one such rule per name in `OPCODES` whose template is folded so far.

---

## Affected modules

| Module | Step | Change |
|---|---|---|
| `bruijn.py` | 1, 2 | `Strictness`; `$fix` is `NONE`; the opcode rules (C) |
| `banf_reduce.py` | 1 | the `FIELDS` positions (A) |
| `banf_opcodes.py` | 2, 3, 4 | `evaluate` (B), a template group per step |
| `llvm_translate_test.py` or a new `banf_opcodes_test.py` case | 2 | fold vs LLVM JIT, per template and width |
| `banf_translate_test.py` | 2 | tests that need an `OpcodeCall` use a param operand |
| `docs/notes.md` | 1–4 | "Heads" (`FIELDS`), the `reduce` list, "Opcodes are not run", "Monomorphic" |

---

## Open questions

> [!IMPORTANT]
> 1. **Where the rules are built.** `bruijn` is the kernel; building opcode rules there
>    makes it import `banf_opcodes`. Alternatives: a neutral `opcodes.py` holding the
>    signatures and the evaluator, imported by both; or `banf_opcodes` registering its
>    rules into `bruijn.BUILTIN_RULES` (an import side effect).
> 2. **Bare literals.** Decision 5 folds `$add_i32 {a = [01000000], b = [02000000]}`,
>    with no forms, though `convert` rejects it today (`Byte array: form must be
>    written.`). Folding gives the result a form, so the program becomes valid. Is that
>    wanted, or should folding need the forms too?
> 3. **Strictness for `$pack`.** [plan_struct_pack.md](plan_struct_pack.md) needs a
>    list's spine reduced, deeper than `FIELDS`. Should `Strictness` grow a fourth value
>    for it, or should a rule describe the positions it reads?

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: a built-in rule can be strict in its fields

- `bruijn.py`: `Strictness`; `$fix` is `NONE`. `banf_reduce.py`: A.
- Tests in `banf_reduce_test.py`, with a test-only `FIELDS` rule (monkeypatched
  `bruijn.BUILTIN_RULES`), such as `$both {a = x, b = y}` giving `{x, y}` once both
  fields are byte arrays:
  - `$both {a = (i -> i) [01], b = {c = [02]}.c}` reduces both fields, then fires.
  - `$both {a = e, b = (i -> i) [02]}` reduces `b` and stays (`e` is free).
  - An `ARGUMENT` rule still doesn't reduce fields; `$fix g` still doesn't reduce `g`.

Commit: `oymomo: a built-in rule can be strict in its fields`

### Step 2: fold `add sub mul and or xor`

- `banf_opcodes.py`: `evaluate` for these templates. `bruijn.py`: C.
- Tests:
  - `reduce`: the goal's `$add_i32`; wrapping (`$add_i8` of `ff` and `01` is `00`);
    a missing form folds, a wrong form or byte count is stuck, a run-time operand is
    stuck, wrong labels are stuck.
  - `banf_translate`: a folded let disappears; `$add_i8 {a = [01]: 'i32', b = ...}` still
    gives `$add_i8 expects a: i8, got i32.`
  - Fold vs LLVM (decision 3) for these templates, every width.
- `docs/notes.md`: "Opcodes are not run" goes; folding in the `reduce` list.

Commit: `oymomo: fold add, sub, mul, and, or, xor on literals`

### Step 3: fold division and shifts

- `banf_opcodes.py`: `sdiv udiv srem urem shl lshr ashr`, with decision 4's guards.
- Tests: each guard is stuck (divisor 0, signed minimum by -1, shift by `N` and more);
  fold vs LLVM on the defined cases.

Commit: `oymomo: fold division and shifts`

### Step 4: fold comparisons and conversions

- `banf_opcodes.py`: `eq ne slt sle sgt sge ult ule ugt uge`, `zext sext trunc`.
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

The final check: for every name in `banf_opcodes.OPCODES`, `bruijn.BUILTIN_RULES` has a
rule, and the fold-vs-LLVM test passes for it on every edge operand.
