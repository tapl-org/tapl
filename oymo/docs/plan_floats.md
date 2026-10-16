# Plan: floats as in LLVM: `'f32'`, `'f64'`, arithmetic, comparisons, conversions

**Status:** proposed, with open questions · 0 of 5 steps · no breaking changes
· [plan_c_interop.md](plan_c_interop.md) 1.3

## Goal

- **A program computes with IEEE 754 floats exactly as LLVM does.**
- `'f32'` is LLVM's `float`, `'f64'` its `double`.
- Each operation is one LLVM instruction or intrinsic: an opcode with the form as a
  field, e.g. `'fmul' {'f64', a, b}` is `fmul double a, b`.
- Reduction, the VM and LLVM agree bit for bit on every non-NaN result.

## Steps

One commit each; each leaves `hatch run full-check` green and updates `docs/notes.md`.

- [ ] 1. The forms `'f32'` and `'f64'`: literals, params, results, imports (`oymomo: add float forms`)
- [ ] 2. Arithmetic: `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'` (`oymomo: add float arithmetic`)
- [ ] 3. Comparisons: one symbol per predicate (`oymomo: add float comparisons`)
- [ ] 4. Conversions: `'fpext'`, `'fptrunc'`, `'fptosi'`, `'fptoui'`, `'sitofp'`, `'uitofp'`, `'bitcast'` (`oymomo: add float conversions`)
- [ ] 5. Exact intrinsics: `'sqrt'`, `'fabs'`, `'copysign'`, `'floor'`, `'ceil'`, `'trunc'`, ... (`oymomo: add float intrinsics`)

- Step 1 needs only forms: a float can be passed, returned, stored and given to an
  import (`sqrt` from libm) before oymomo computes with it.
- Steps 2–5 are opcodes, polymorphic in `form` ([plan_vm.md](plan_vm.md) step 3).

## Decisions

### Forms and literals (step 1)

1. **`'f32'` and `'f64'`**, LLVM's `float` and `double`; named like integer forms.
   Other widths: open question 1.
2. **A literal is its IEEE 754 bits, little-endian:** `[0000803f]~'f32'` and
   `[000000000000f03f]~'f64'` are 1.0.
   - Every bit pattern is a value, NaN payloads included.
   - Wrong size: `A f32 constant needs 4 bytes.`
   - Decimal syntax: open question 2.
3. **A float is a value like an integer:** param, result, struct field, let, import.
   No ABI work for scalars.
4. **No implicit change of bits or form.** Reading bits as an integer is the explicit
   `'bitcast'` (decision 10).

### Semantics (steps 2 to 5)

5. **LLVM's default FP environment only:** round to nearest even, no traps, no
   fast-math flags, no constrained intrinsics.
   - `'f64'` is Python's `float`.
   - `'f32'` is computed in binary64, then rounded to binary32 (exact for `+ - * /`
     and `sqrt`).
6. **A NaN result is never folded.** LLVM or the hardware picks the NaN. Tests compare
   NaNs as "is a NaN". A NaN *operand* folds if the result isn't NaN.
7. **An undefined conversion stops the VM.** `fptosi`/`fptoui` of NaN, ∞ or out of
   range: not folded; VM raises `VmError: fptosi f64 to i32: 3e10 is out of range.`
   Saturating versions: open question 3.

### Operations (steps 2 to 5)

All are opcodes ([plan_vm.md](plan_vm.md) decisions 7 to 10): pure, form as a field,
positional fields in LLVM's order, folded on literals except per decisions 6–7.

8. **Arithmetic:**

   | Symbol | Fields | LLVM |
   |---|---|---|
   | `'fadd'`, `'fmul'` | `form`, `a`, `b` | `fadd double a, b` |
   | `'fsub'` | `form`, `a`, `b` | `fsub double a, b` |
   | `'fdiv'`, `'frem'` | `form`, `a`, `b` | `fdiv double a, b` |
   | `'fneg'` | `form`, `value` | `fneg double x` |

   - `'fneg'` flips only the sign bit, so it folds even on a NaN.
   - `fdiv` by zero gives ∞ or NaN (IEEE 754), not undefined.
9. **Comparisons: one symbol per predicate, `fcmp_` + LLVM's predicate.** Fields
   `{form, lhs, rhs}`; each gives `'i1'`. The prefix keeps `'fcmp_ugt'` (unordered or
   greater) apart from `'icmp_ugt'` (unsigned greater).

   | Symbol | True when | LLVM |
   |---|---|---|
   | `'fcmp_oeq'` `'fcmp_one'` | neither is NaN, and `=` / `≠` | `fcmp oeq`, `fcmp one` |
   | `'fcmp_ogt'` `'fcmp_oge'` `'fcmp_olt'` `'fcmp_ole'` | neither is NaN, and `>` `≥` `<` `≤` | `fcmp ogt`, ... |
   | `'fcmp_ueq'` `'fcmp_une'` | either is NaN, or `=` / `≠` | `fcmp ueq`, `fcmp une` |
   | `'fcmp_ugt'` `'fcmp_uge'` `'fcmp_ult'` `'fcmp_ule'` | either is NaN, or `>` `≥` `<` `≤` | `fcmp ugt`, ... |
   | `'fcmp_ord'` | neither is NaN | `fcmp ord` |
   | `'fcmp_uno'` | either is NaN | `fcmp uno` |

   - No `fcmp false`/`fcmp true`: write `[00]~'i1'`.
   - `-0.0` equals `+0.0` under `oeq`.
10. **Conversions:** fields `{form, value, to}`, like `'zext'`
    (`'fpext' {'f32', x, 'f64'}`).

    | Symbol | From → to | LLVM |
    |---|---|---|
    | `'fpext'` | `'f32'` → `'f64'` | `fpext float x to double` |
    | `'fptrunc'` | `'f64'` → `'f32'` | `fptrunc double x to float`, rounded |
    | `'fptosi'`, `'fptoui'` | float → integer | toward zero; out of range is decision 7 |
    | `'sitofp'`, `'uitofp'` | integer → float | rounded to nearest |
    | `'bitcast'` | any → any of the same size | the same bits, read as `to` |

    - `'bitcast'` is the only way to see a float's bits; works on any same-size forms
      LLVM can bitcast (not structs).
11. **Intrinsics: only the exact ones**, `llvm.NAME` without the prefix:

    | Symbol | Fields | LLVM |
    |---|---|---|
    | `'sqrt'` | `form`, `value` | `llvm.sqrt` |
    | `'fabs'` | `form`, `value` | `llvm.fabs` |
    | `'copysign'` | `form`, `magnitude`, `sign` | `llvm.copysign` |
    | `'floor'`, `'ceil'`, `'round'`, `'roundeven'`, and round toward zero (open question 4) | `form`, `value` | `llvm.floor`, `llvm.ceil`, `llvm.round`, `llvm.roundeven`, `llvm.trunc` |
    | `'minnum'`, `'maxnum'`, `'minimum'`, `'maximum'` | `form`, `a`, `b` | `llvm.minnum`, ... |
    | `'fma'` | `form`, `a`, `b`, `c` | `llvm.fma`, `a × b + c` rounded once |

    - Transcendental functions (`sin`, `exp`, `log`, `pow`) are libm imports, e.g.
      `sin = {x = 'f64'} => 'f64'`.

## Implementation steps

Module changes: see [Background › Design](#design).

| Step | Design | Tests (summary) | `notes.md` |
|---|---|---|---|
| 1 | A | return an `'f64'` param; `float 1.0`; NaN payload kept through JIT; float struct field; `sqrt` import under JIT; 3-byte `'f32'` error; VM gives same bits; golden `float.oymo` | `'f32'`, `'f64'` in the form and BANF→LLVM tables; literals are bits |
| 2 | B, decision 8 | edge operands vs. JIT; folding 1.0 + 2.0; NaN stays; `'fneg'` of NaN folds; `'f32'` `0.1 + 0.2`; `test_fold_matches_llvm` | arithmetic, rounding, NaNs not folded |
| 3 | B, decision 9 | every predicate × `{-∞, -1, -0, +0, 1, +∞, NaN}` vs. JIT; literal folds; `'icmp_ult'` on `'f32'` errors | predicate table |
| 4 | B, decision 10 | rounding cases; `fptosi -1.5` is `-1`; undefined `fptoui` → `VmError`; `'bitcast'`; `'fpext'` narrowing and `'bitcast'` size errors; JIT = VM | conversions; `'bitcast'` reads bits |
| 5 | B, decision 11 (decide open question 4 first) | edge operands vs. JIT; `fma` rounded once; `minnum`/`minimum` with NaN and ±0; `'sqrt'` is `llvm.sqrt.f64`; plan → **implemented** | intrinsics; why transcendentals are imports |

**Final check:** the goal program gives `hypot(3.0, 4.0) = 5.0` under the JIT and the
VM; every float symbol matches the JIT on edge operands (NaN results: "is a NaN").

## Open questions

1. **Other float forms** (decision 1): `'f16'`, `'bf16'`, `'f128'`, `x86_fp80`. Which, and when?
2. **Decimal literals** (decision 2): `1.5~'f64'` as parser sugar for bytes? Hex float or decimal?
3. **Saturating conversions** (decision 7): add `'fptosi_sat'`/`'fptoui_sat'` with step 4?
4. **The name of `llvm.trunc`** (decision 11): overload `'trunc'` on `form`, or a distinct name?
   - a. One `'trunc'` whose meaning depends on `form`
   - b. `'trunc_toward_zero'`
   - c. `'ftrunc'`
5. **Float vectors:** after [plan_memory.md](implemented/plan_memory.md) step 5, every
   symbol accepts float vectors where LLVM does; reduction folds only scalars.

## Dependencies

- [plan_vm.md](plan_vm.md): opcodes polymorphic in `form` (step 3, done), fold rule
  (decision 8), VM errors (decision 4).
- [plan_c_interop.md](plan_c_interop.md): this plan is 1.3; phase 3 covers structs of floats.
- Open question 5 waits on [plan_memory.md](implemented/plan_memory.md) step 5 (vectors).

## Background (for agents)

Context kept for reference; not needed to follow the plan.

### Example: the goal program

```
module~{hypot = => 'f64', sqrt = {x = 'f64'} => 'f64'} -> {
  hypot = f -> {
    entry = args~{x = 'f64', y = 'f64'} ->
      let xx = 'fmul' {'f64', args.x, args.x} in
      let yy = 'fmul' {'f64', args.y, args.y} in
      let s = 'fadd' {'f64', xx, yy} in
      module.sqrt {x = s},
  },
}
```

```
hypot: f64
  entry(x: f64, y: f64):
    xx = fmul f64 x, x
    yy = fmul f64 y, y
    s = fadd f64 xx, yy
    t0 = call sqrt(s)
    return t0
```

```llvm
define double @"hypot"(double %"x", double %"y")
{
entry:
  %"xx" = fmul double %"x", %"x"
  %"yy" = fmul double %"y", %"y"
  %"s" = fadd double %"xx", %"yy"
  %"t0" = call double @"sqrt"(double %"s")
  ret double %"t0"
}
```

With literal arguments, reduction folds `'fmul'` and `'fadd'` to LLVM's bits
(decision 5); the VM runs them in Python with the same bits.

### Design

**A. Forms (step 1)**

| Module | Change |
|---|---|
| `banf_terms.py` | nothing: `'f32'` and `'f64'` are named forms |
| `llvm_translate.py` | `llvm_type`: `'f32'` → `ir.FloatType()`, `'f64'` → `ir.DoubleType()`; `_const`: a float constant from its bits (`struct.unpack('<f' / '<d', ...)`), and for a NaN with a payload, the bits bitcast from an integer constant, so no payload is lost |
| `vm_compile.py`, `vm.py` | a float value is a Python `float`; an `'f32'` value is always one an `f32` can hold; constants decoded with `struct`, results encoded the same way |
| `opcodes.py` | `FLOAT_FORMS = ('f32', 'f64')`, next to the integer forms, for `accepts` |

**B. Arithmetic, comparisons, conversions, intrinsics (steps 2 to 5)**

| Module | Change |
|---|---|
| `opcodes.py` | an entry per symbol of decisions 8 to 11; `run` on Python floats, rounding to `f32` where `form` is `'f32'`; `accepts` float forms (and integer forms for `'sitofp'`, `'uitofp'`, `'bitcast'`) |
| `reduction.py` | none: the one fold rule of [plan_vm.md](plan_vm.md) decision 8 folds float forms too, except a NaN result (decision 6) and an undefined conversion (decision 7); `run` returns `None` for both, as `opcodes.evaluate` does for division by zero |
| `llvm_opcodes.py` | `builder.fadd`, `fsub`, `fmul`, `fdiv`, `frem`, `fneg`; `builder.fcmp_ordered` / `fcmp_unordered`; `fpext`, `fptrunc`, `fptosi`, `fptoui`, `sitofp`, `uitofp`, `bitcast`; intrinsics through `module.declare_intrinsic` |
| `banf_terms.py` | printed as LLVM writes them: `fadd f64 a, b`, `fcmp olt f64 a, b`, `fptosi f64 x to i32` |

### Notes on the decisions

- 1: they are what C needs (`float`, `double`).
- 2: byte arrays are always little-endian
  ([notes.md](notes.md#byte-arrays-are-always-little-endian)); the size error matches
  integers. Bits are hard to read, hence open question 2.
- 3: LLVM passes scalar floats in float registers by itself.
- 4: as for integers, a written form replaces the atom's form in BANF, and LLVM never
  converts ([llvm_translate.py](../src/oymo/oymomo/llvm_translate.py) rejects a let
  formed as something its op doesn't give).
- 5: no fast-math means no `nnan`, `ninf`, `nsz`, `reassoc`, ... Results are correctly
  rounded. In Python `+ - * /` and `math.sqrt` are correctly rounded binary64,
  `math.fmod` is exact. `'f32'` rounding uses `struct.pack('<f', ...)`; double rounding
  is exact because binary64 has more than `2 × 24 + 2` bits.
- 6: LLVM doesn't fix a NaN's payload or sign (varies by target); same treatment as
  integer division by zero. The VM gives some NaN. Example: `'fcmp_uno'` of a NaN
  folds to `[01]~'i1'`.
- 7: these are poison in LLVM; the VM error mirrors integer division by zero
  ([plan_vm.md](plan_vm.md) decision 4).
- 8: labels are ignored, as for every VM symbol ([plan_vm.md](plan_vm.md) decision 7):
  `'fsub' {'f64', x, y}` is `x - y`. `'fneg'` of a NaN is the one NaN result folded,
  since LLVM fixes its bits.
- 9: integer comparisons are named `icmp_` + predicate ([plan_vm.md](plan_vm.md)
  decision 10). `fcmp false`/`true` are left out because they don't read operands.
- 10: `'bitcast' {'f32', x, 'i32'}` is LLVM's `bitcast float %x to i32`; not float-only.
- 11: each has one correctly rounded or exact result, so Python can compute it. `fma` is
  exact with `math.fma` (3.13) or `fractions.Fraction` on older versions.
  Transcendentals have no one right answer across libms. `llvm.trunc` (toward zero)
  clashes with integer `'trunc'` (narrowing): open question 4.

### Notes on the open questions

- 1: `'f16'` (LLVM `half`, `struct` `'e'`) is cheap; `'bf16'` has no Python support but
  is a truncated `f32`; `'f128'` and `x86_fp80` need software arithmetic in the VM.
- 2: sugar for `[000000000000f83f]`, so oymomo still sees only byte arrays. Hex float
  (`0x1.8p0`) is exact; decimal needs a rounding rule (nearest, as C). The printer
  would show floats the same way.
- 3: `llvm.fptosi.sat`/`llvm.fptoui.sat` define every input (NaN → 0, out of range →
  min or max), so they never trap and always fold.
- 4: (a) would be the only overload, since `'add'` and `'fadd'` are kept apart.

### Test details per step

- **1:** `define double @"g"(double %"x")`; `[0000803f]~'f32'` is `float 1.0`; NaN
  payload read back with `struct`; golden `float.oymo` binds `sqrt` by the host in the VM.
- **2:** edge operands: `±0`, `±1`, smallest subnormal, largest finite, `±∞`, a NaN,
  both forms. `'fadd' {'f64', [000000000000f03f], [0000000000000040]}` folds to
  `[0000000000000840]~'f64'`; `0.0 / 0.0` stays; `0.1 + 0.2` in `'f32'` folds to the
  `f32` bits.
- **3:** `'fcmp_olt'` of literals folds to `[01]~'i1'` or `[00]~'i1'`; `'fcmp_uno'`
  with NaN folds to `[01]~'i1'`; error text:
  `'icmp_ult' takes an integer form, got f32; for floats use 'fcmp_ult'.`
- **4:** `fptrunc` of a non-`f32` `'f64'` rounds to nearest even; `sitofp` of
  `2^53 + 1` rounds; `fptoui` of `-1.0`, NaN, `2^32` to `'i32'`: not folded, `VmError`;
  `'bitcast'` of `1.0~'f32'` to `'i32'` is `[0000803f]`; error text:
  `'fpext': to must be wider than f64, got f32.`
- **5:** `fma` where twice-rounded differs from once; `minnum(NaN, 1.0)` is `1.0`,
  `minimum` is NaN; `minimum(-0.0, +0.0)` is `-0.0`; `'sqrt'` is
  `call double @llvm.sqrt.f64`.

### Breaking changes

None: `'f32'` and `'f64'` had no LLVM type before, and the new symbols were unknown.
