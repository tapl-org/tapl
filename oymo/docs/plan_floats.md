# Plan: floats as in LLVM: `'f32'`, `'f64'`, arithmetic, comparisons, conversions

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. The forms `'f32'` and `'f64'`: literals, params, results, imports (`oymomo: add float forms`)
- [ ] 2. Arithmetic: `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'` (`oymomo: add float arithmetic`)
- [ ] 3. Comparisons: one symbol per predicate (`oymomo: add float comparisons`)
- [ ] 4. Conversions: `'fpext'`, `'fptrunc'`, `'fptosi'`, `'fptoui'`, `'sitofp'`, `'uitofp'`, `'bitcast'` (`oymomo: add float conversions`)
- [ ] 5. Exact intrinsics: `'sqrt'`, `'fabs'`, `'copysign'`, `'floor'`, `'ceil'`, `'trunc'`, ... (`oymomo: add float intrinsics`)

Step 1 needs nothing but forms: a float can be passed, returned, stored in a struct
and given to an import (`sqrt` from libm) before oymomo can compute with it. Steps 2
to 5 are opcodes, polymorphic in `form`, as [plan_vm.md](plan_vm.md) step 3 (done)
made every opcode. This is [plan_c_interop.md](plan_c_interop.md) 1.3.
No step is breaking.

## Goal

**A program computes with IEEE 754 floats exactly as LLVM does.** `'f32'` is LLVM's
`float`, `'f64'` its `double`. Each operation is one LLVM instruction or intrinsic,
written as an opcode with the form as a field:

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

A literal is its bits: `[000000000000f03f]~'f64'` is 1.0. With literal arguments
reduction folds `'fmul'` and `'fadd'` to the bits LLVM would compute (decision 5); the
VM runs them in Python with the same bits ([plan_vm.md](plan_vm.md)).

## Decisions

### Forms and literals (step 1)

1. **`'f32'` and `'f64'`, LLVM's `float` and `double`.** Named as the integer forms
   are, by kind and width. They are what C needs (`float`, `double`). `'f16'`,
   `'bf16'`, `'f128'` and `x86_fp80` are open question 1.
2. **A float literal is its IEEE 754 bits, little-endian.** `[0000803f]~'f32'` is
   1.0, `[000000000000f03f]~'f64'` is 1.0, as every byte array is little-endian
   ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)).
   Every bit pattern is a value, NaNs with any payload included; a literal of the
   wrong size is `A f32 constant needs 4 bytes.`, as for integers. Writing floats as
   bits is hard to read; a decimal syntax is open question 2.
3. **A float is a value like an integer.** A block param, a function param or
   result, a struct field, a let, an import's param or result. LLVM passes scalar
   floats in float registers by itself, so no ABI work is needed
   ([plan_c_interop.md](plan_c_interop.md) phase 3 covers structs of floats).
4. **No implicit change of bits or form.** As for integers, a written form replaces
   the atom's form in BANF and LLVM never converts
   ([llvm_translate.py](../src/oymo/oymomo/llvm_translate.py) rejects a let formed
   as something its op doesn't give). Reading a float's bits as an integer is the
   explicit `'bitcast'` (decision 10).

### Semantics (steps 2 to 5)

5. **LLVM's default floating-point environment, and nothing else.** Round to nearest,
   ties to even; no traps; no fast-math flags (`nnan`, `ninf`, `nsz`, `reassoc`,
   ...); no constrained intrinsics. A result is the correctly rounded IEEE 754
   result, so reduction, the VM and LLVM agree bit for bit on every non-NaN
   result:
   - **`'f64'`** is Python's `float`: `+ - * /` and `math.sqrt` are correctly
     rounded binary64, `math.fmod` is exact.
   - **`'f32'`** is computed in binary64, then rounded to binary32
     (`struct.pack('<f', ...)`). For `+ - * /` and `sqrt` this is exact: binary64
     has more than `2 × 24 + 2` bits, so rounding twice gives the same result as
     rounding once.
6. **A NaN result is never folded.** LLVM doesn't fix which NaN an operation gives
   (payload and sign may vary by target), so reduction leaves an operation whose
   result is a NaN unfolded, as it leaves an integer division by zero, and LLVM or
   the hardware picks. The VM gives some NaN; differential tests compare NaNs as
   "is a NaN", not by bits. A NaN *operand* is fine to fold when the result isn't
   a NaN (`'fcmp_uno'` of a NaN is `[01]~'i1'`).
7. **A conversion LLVM leaves undefined stops the VM.** `fptosi` and `fptoui` of a
   NaN, an infinity, or a value out of the target's range are poison in LLVM;
   reduction doesn't fold them, and the VM raises
   `VmError: fptosi f64 to i32: 3e10 is out of range.`, as for integer division by
   zero ([plan_vm.md](plan_vm.md) decision 4). The saturating
   `llvm.fptosi.sat` is open question 3.

### Operations (steps 2 to 5)

All are opcodes ([plan_vm.md](plan_vm.md) decisions 7 to 10): pure, form as a
field, folded on literals except where decisions 6 and 7 say not.

8. **Arithmetic**, LLVM's instructions:

   | Symbol | Fields | LLVM |
   |---|---|---|
   | `'fadd'`, `'fmul'` | `form`, `a`, `b` | `fadd double a, b` |
   | `'fsub'` | `form`, `a`, `b` | `fsub double a, b` |
   | `'fdiv'`, `'frem'` | `form`, `a`, `b` | `fdiv double a, b` |
   | `'fneg'` | `form`, `value` | `fneg double x` |

   Fields are positional, in LLVM's order, and labels are ignored, as for every VM
   symbol ([plan_vm.md](plan_vm.md) decision 7): `'fsub' {'f64', x, y}` is `x - y`.
   `'fneg'` flips the sign bit and nothing else, so `'fneg'` of a NaN is a NaN with
   its sign flipped: the one NaN result folded, since LLVM fixes its bits.
   `fdiv` by zero is not undefined: it gives an infinity or a NaN, as IEEE 754 says.
9. **Comparisons, one symbol per predicate, named `fcmp_` and LLVM's predicate**, as
   integer comparisons are named `icmp_` and theirs ([plan_vm.md](plan_vm.md)
   decision 10). The prefix matters: LLVM's `fcmp ugt` means "unordered or
   greater", `icmp ugt` "unsigned greater", and `'fcmp_ugt'` and `'icmp_ugt'` keep
   them apart:

   | Symbol | True when | LLVM |
   |---|---|---|
   | `'fcmp_oeq'` `'fcmp_one'` | neither is NaN, and `=` / `≠` | `fcmp oeq`, `fcmp one` |
   | `'fcmp_ogt'` `'fcmp_oge'` `'fcmp_olt'` `'fcmp_ole'` | neither is NaN, and `>` `≥` `<` `≤` | `fcmp ogt`, ... |
   | `'fcmp_ueq'` `'fcmp_une'` | either is NaN, or `=` / `≠` | `fcmp ueq`, `fcmp une` |
   | `'fcmp_ugt'` `'fcmp_uge'` `'fcmp_ult'` `'fcmp_ule'` | either is NaN, or `>` `≥` `<` `≤` | `fcmp ugt`, ... |
   | `'fcmp_ord'` | neither is NaN | `fcmp ord` |
   | `'fcmp_uno'` | either is NaN | `fcmp uno` |

   Fields `{form, lhs, rhs}`, as LLVM's `fcmp olt double lhs, rhs`; each gives
   `'i1'`. LLVM's `fcmp false` and `fcmp true` are
   left out: they don't read their operands, and a program writes `[00]~'i1'`.
   `-0.0` equals `+0.0` under `oeq`, as IEEE 754 says.
10. **Conversions**, LLVM's casts, with fields `{form, value, to}` in LLVM's order
    (`fpext float %x to double` is `'fpext' {'f32', x, 'f64'}`), as `'zext'`:

    | Symbol | From → to | LLVM |
    |---|---|---|
    | `'fpext'` | `'f32'` → `'f64'` | `fpext float x to double` |
    | `'fptrunc'` | `'f64'` → `'f32'` | `fptrunc double x to float`, rounded |
    | `'fptosi'`, `'fptoui'` | float → integer | toward zero; out of range is decision 7 |
    | `'sitofp'`, `'uitofp'` | integer → float | rounded to nearest |
    | `'bitcast'` | any → any of the same size | the same bits, read as `to` |

    `'bitcast'` is the only way to see a float's bits as an integer or back
    (`'bitcast' {'f32', x, 'i32'}`, LLVM's `bitcast float %x to i32`). It works on any two forms of
    the same size that LLVM can bitcast (not structs), so it is not float-only.
11. **Intrinsics, only the exact ones.** Each is LLVM's `llvm.NAME` intrinsic, named
    without the prefix, and each has one correctly rounded or exact result, so
    reduction and the VM can compute it with Python:

    | Symbol | Fields | LLVM |
    |---|---|---|
    | `'sqrt'` | `form`, `value` | `llvm.sqrt` |
    | `'fabs'` | `form`, `value` | `llvm.fabs` |
    | `'copysign'` | `form`, `magnitude`, `sign` | `llvm.copysign` |
    | `'floor'`, `'ceil'`, `'round'`, `'roundeven'`, and round toward zero (open question 4) | `form`, `value` | `llvm.floor`, `llvm.ceil`, `llvm.round`, `llvm.roundeven`, `llvm.trunc` |
    | `'minnum'`, `'maxnum'`, `'minimum'`, `'maximum'` | `form`, `a`, `b` | `llvm.minnum`, ... |
    | `'fma'` | `form`, `a`, `b`, `c` | `llvm.fma`, `a × b + c` rounded once |

    LLVM's `llvm.trunc` (round toward zero) clashes with the integer `'trunc'`
    (narrow an integer): open question 4. `fma` is exact in Python with
    `math.fma` (3.13) or with `fractions.Fraction` on older versions. Transcendental
    functions (`sin`, `exp`, `log`, `pow`) have no one right answer across libms, so
    they are imports from libm, not opcodes: a program declares
    `sin = {x = 'f64'} => 'f64'`.

---

## Design

### A. Forms (step 1)

| Module | Change |
|---|---|
| `banf_terms.py` | nothing: `'f32'` and `'f64'` are named forms |
| `llvm_translate.py` | `llvm_type`: `'f32'` → `ir.FloatType()`, `'f64'` → `ir.DoubleType()`; `_const`: a float constant from its bits (`struct.unpack('<f' / '<d', ...)`), and for a NaN with a payload, the bits bitcast from an integer constant, so no payload is lost |
| `vm_compile.py`, `vm.py` | a float value is a Python `float`; an `'f32'` value is always one an `f32` can hold; constants decoded with `struct`, results encoded the same way |
| `opcodes.py` | `FLOAT_FORMS = ('f32', 'f64')`, next to the integer forms, for `accepts` |

### B. Arithmetic, comparisons, conversions, intrinsics (steps 2 to 5)

| Module | Change |
|---|---|
| `opcodes.py` | an entry per symbol of decisions 8 to 11; `run` on Python floats, rounding to `f32` where `form` is `'f32'`; `accepts` float forms (and integer forms for `'sitofp'`, `'uitofp'`, `'bitcast'`) |
| `reduction.py` | none: the one fold rule of [plan_vm.md](plan_vm.md) decision 8 folds float forms too, except a NaN result (decision 6) and an undefined conversion (decision 7); `run` returns `None` for both, as `opcodes.evaluate` does for division by zero |
| `llvm_opcodes.py` | `builder.fadd`, `fsub`, `fmul`, `fdiv`, `frem`, `fneg`; `builder.fcmp_ordered` / `fcmp_unordered`; `fpext`, `fptrunc`, `fptosi`, `fptoui`, `sitofp`, `uitofp`, `bitcast`; intrinsics through `module.declare_intrinsic` |
| `banf_terms.py` | printed as LLVM writes them: `fadd f64 a, b`, `fcmp olt f64 a, b`, `fptosi f64 x to i32` |

---

## Breaking changes

None. `'f32'` and `'f64'` had no LLVM type before, and the new symbols were unknown.

---

## Open questions

> [!IMPORTANT]
> 1. **Other float forms** (decision 1). `'f16'` (LLVM `half`, Python's
>    `struct` `'e'`) is cheap; `'bf16'` has no Python support but is a truncated
>    `f32`; `'f128'` and `x86_fp80` need software arithmetic in the VM. Which, and
>    when?
> 2. **Decimal literals** (decision 2). `1.5~'f64'` as parser sugar for the bytes
>    `[000000000000f83f]`, so oymomo still sees only byte arrays. Hex float
>    (`0x1.8p0`) would be exact; decimal needs a rounding rule (nearest, as C).
>    The printer would show floats the same way.
> 3. **Saturating conversions** (decision 7). `llvm.fptosi.sat` and
>    `llvm.fptoui.sat` define every input (NaN to 0, out of range to the min or
>    max); `'fptosi_sat'` would never trap and always fold. Add them with step 4?
> 4. **The name of `llvm.trunc`** (decision 11). The integer `'trunc'` narrows an
>    integer; LLVM's float `llvm.trunc` rounds toward zero. One symbol whose meaning
>    depends on `form` (as `'add'` and `'fadd'` are kept apart, that would be the
>    only overload), or a distinct name (`'trunc_toward_zero'`, `'ftrunc'`)?
> 5. **Float vectors.** Once [plan_memory.md](plan_memory.md) step 5 adds vectors,
>    every symbol here accepts a float vector where LLVM does; reduction folds only
>    scalars.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: the forms `'f32'` and `'f64'`

- A.
- Tests:
  - `llvm_translate`: a function that returns its `'f64'` param is
    `define double @"g"(double %"x")`; `[0000803f]~'f32'` is `float 1.0`; a NaN
    with a payload keeps its bits through LLVM (JIT, read back with `struct`); a
    struct with a float field; an import `sqrt = {x = 'f64'} => 'f64'` called under
    the JIT; a 3-byte `'f32'` literal is `A f32 constant needs 4 bytes.`
  - `vm`: the same programs give the same bits.
  - golden `float.oymo`: the goal program, with `sqrt` bound by the host in the VM.
- `docs/notes.md`: `'f32'`, `'f64'` in the Type/Form/Layout table and the BANF to LLVM
  table; float literals are bits.

Commit: `oymomo: add float forms`

### Step 2: arithmetic

- B, for decision 8.
- Tests:
  - `opcodes`: each op on edge operands (`±0`, `±1`, the smallest subnormal, the
    largest finite, `±∞`, a NaN) for both forms gives what LLVM's JIT gives, bit for
    bit except NaN results, which are NaN on both sides.
  - `reduction`: `'fadd' {'f64', [000000000000f03f], [0000000000000040]}`
    (1.0 + 2.0) folds to `[0000000000000840]~'f64'` (3.0); `0.0 / 0.0` (a NaN)
    stays; `'fneg'` of a NaN folds with its sign flipped; an `'f32'` result
    that rounds differently from `'f64'` (`0.1 + 0.2`) folds to the `f32` bits.
  - `llvm_translate`: `test_fold_matches_llvm` covers the float symbols.
- `docs/notes.md`: float arithmetic, rounding, NaNs not folded.

Commit: `oymomo: add float arithmetic`

### Step 3: comparisons

- B, for decision 9.
- Tests:
  - `opcodes`: every predicate on every pair of `{-∞, -1, -0, +0, 1, +∞, NaN}`
    matches LLVM's JIT.
  - `reduction`: `'fcmp_olt'` of literals folds to `[01]~'i1'` or `[00]~'i1'`;
    `'fcmp_uno'` with a NaN operand folds to `[01]~'i1'`.
  - `banf_translate`: `'icmp_ult' {'f32', a, b}` is
    `'icmp_ult' takes an integer form, got f32; for floats use 'fcmp_ult'.`
- `docs/notes.md`: the predicate table.

Commit: `oymomo: add float comparisons`

### Step 4: conversions

- B, for decision 10.
- Tests:
  - `opcodes`: `fptrunc` of a `'f64'` that isn't an `f32` rounds to nearest even;
    `sitofp` of `2^53 + 1` to `'f64'` rounds; `fptosi` of `-1.5` to `'i32'` is `-1`;
    `fptoui` of `-1.0`, of a NaN and of `2^32` to `'i32'` don't fold and are
    `VmError` in the VM; `'bitcast'` of `1.0~'f32'` to `'i32'` is `[0000803f]`.
  - `banf_translate`: `'fpext' {'f64', x, 'f32'}` is
    `'fpext': to must be wider than f64, got f32.`; `'bitcast'` between forms of
    different sizes is an error.
  - `llvm_translate`: each conversion under the JIT matches the VM.
- `docs/notes.md`: conversions, and `'bitcast'` as the one way to read bits.

Commit: `oymomo: add float conversions`

### Step 5: exact intrinsics

Open question 4 is decided first.

- B, for decision 11.
- Tests:
  - `opcodes`: each intrinsic on the edge operands of step 2 matches LLVM's JIT;
    `fma` of operands where `a × b + c` rounded twice differs from once gives the
    once-rounded result; `minnum` of a NaN and `1.0` is `1.0`, `minimum` of them is
    a NaN; `minimum(-0.0, +0.0)` is `-0.0`.
  - `llvm_translate`: `'sqrt'` is `call double @llvm.sqrt.f64`.
- `docs/notes.md`: intrinsics, and why transcendental functions are imports.
- Status of this plan: **implemented**.

Commit: `oymomo: add float intrinsics`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: the goal program runs under LLVM's JIT and in the VM, and
`hypot(3.0, 4.0)` is `5.0` in both; every float symbol matches LLVM's JIT on the edge
operands, bit for bit except NaN results.
