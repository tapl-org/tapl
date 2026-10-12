# Plan: built-ins are global constants written `$name`

Status: **proposed**.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. A value struct applied to an index is `GetIndex`; `prim.extractvalue` goes (`oymomo: s [01] on a value struct is GetIndex`)
- [ ] 2. `$name` built-ins replace the `prim` binder, breaking (`oymomo: prims are $name built-ins`)
- [ ] 3. Built-ins can have a reduction rule, and `fix` is `$fix`, breaking (`oymomo: fix is $fix`)
- [ ] 4. A strict built-in's argument is a head in `banf_reduce` (`oymomo: banf_reduce reduces a strict built-in's argument`)
- [ ] 5. Write the constant folding plan, docs only (`oymomo: plan constant folding`)

Step 1 is independent of the rest; it comes first so that steps 2 to 4 have no dynamic
prims to carry along. [plan_struct_pack.md](plan_struct_pack.md) builds on step 4:
`$unpack` and `$pack` become two rules instead of two new terms and two reserved words.
Constant folding (`$add_i32` on literals) is a later plan, on the same rules; step 5
writes it.

## Goal

**One kind of primitive, written the same way from anywhere, and added by a table
entry.** Today there are two kinds:

| Kind | Today | Cost of a new one |
|---|---|---|
| opcodes (`add_i32`) | `prim.add_i32 {...}`, where `prim` is the program's outermost binder | a table entry |
| kernel built-ins (`fix`) | `fix g`, its own term and keyword | a term, a rule, a keyword, cases in 5 modules |

`prim` can't hold `fix`: it is a binder, so its index depends on depth (`$3` under three
lambdas), and `reduce`, which sees only the term, can't recognize `prim.fix`.

After this plan, each primitive is its own global constant, the same at any depth:

```
module: {main = => 'i32'} -> {main = f -> {entry = args: {a = 'i32'} -> ...}}
                                     the program no longer starts with `prim ->`
$add_i32 {a = args.a, b = args.a}    an opcode, as prim.add_i32 today
$fix g                               ⇒   g ($fix g)
$fix (self -> n -> n) a              ⇒   a
let y = args.p [01] in y             BANF `y = p.1`, LLVM `extractvalue`
prim -> fix -> prim fix              plain names: nothing is reserved
```

## Decisions

### Index access in BANF (step 1)

1. **A value struct applied to a literal index is a BANF op, `GetIndex`.** `s [01]`,
   where `s` is an atom (a let name or `args.p`), reads field 1, as `s.y` reads field
   `y`. The kernel's struct apply rule already gives `s i` this meaning; BANF now keeps
   it when `s` is a value instead of a struct literal. LLVM translates it to
   `extractvalue`, as it does `GetField`.
2. **`prim.extractvalue`, `DynamicPrim`, `DYNAMIC_PRIMS` and `PrimFormError` go.** They
   existed only for this. One syntax, `s [01]`, reads a field by index in the kernel
   and in BANF.
3. **The index is a byte array literal, read by `bruijn.index_value`**: unsigned
   little-endian, any length, a form on it ignored. It needs no int form, unlike
   `prim.extractvalue`'s index, since it is never a run-time value: `args.p [01]` is
   enough. A let name, `''`, or anything else as index is an error (LLVM's
   `extractvalue` needs a constant).
4. **BANF prints it as `p.1`.** A label written as digits needs quotes (`p."1"`), so
   `p.1` is never a label.

### Built-ins (steps 2 to 4)

5. **One leaf term, `Builtin(name)`, written `$name`.** `$` followed by digits stays a
   `BruijnIndex` (`$0`); an identifier can't start with a digit, so the two never
   overlap. `$` marks a reference that no user name binds: `$0` is bound by position,
   `$fix` by the kernel. User names are always written bare. No trivia between `$` and
   the name; the name is a plain identifier.
6. **Every built-in is a separate constant**, not a field of a global struct: there is
   no `$` value to project from, apply, or unpack.
7. **The program has no `prim` binder.** It is `module: {...} -> {...}`. `prim`, `fix`
   and every other word become plain names: nothing is reserved.
8. **Every built-in takes exactly one argument.** A built-in with several operands takes
   a struct, as prims do today. So a call is always `Apply(Builtin(name), arg)`, with no
   arity and no partial application. `$fix g a` is `($fix g) a`: the root is not a
   redex, and `$fix g` is its head, as `(fix g) a` is today.
9. **A name can be in two tables.** Reduction rules are in `bruijn.BUILTIN_RULES`;
   machine code is in `banf_opcodes.OPCODES` and `llvm_opcodes.DEFAULT_OPCODES`:

   | Name | Rule | Machine code |
   |---|---|---|
   | `fix` | yes | no: it must reduce away |
   | `add_i32` and the other prims | later: constant folding | yes |
   | `unpack`, `pack` (plan_struct_pack) | yes | no |

10. **Kernel-only built-ins never reach BANF.** A built-in is kernel-only when it has a
    rule and no opcode (`fix`, `unpack`, `pack`). This comes from the tables, with
    no flag to keep in sync. An opcode is a name in `OPCODES`, and the existing test
    keeps `OPCODES` and `DEFAULT_OPCODES` in step.
    - **Reduction removes them.** Every position `banf_reduce` visits is taken to whnf,
      and an applied built-in whose rule fires is gone: `$fix g` always fires, and
      `$unpack {...}` fires once its argument is a struct.
    - **`convert` is the only gate.** A `Builtin` enters BANF only through one case,
      `Apply(Builtin(name), arg)` to `OpcodeCall`, and that case accepts only names in
      `OPCODES`. Any other position that still holds a `Builtin` is not a BANF shape and
      is rejected anyway. `banf.verify` checks `OPCODES` again, as it does today.
    - **One message for each way a kernel-only built-in can be left over:**

      | Left over | Why | Message |
      |---|---|---|
      | `$fix` | not applied | `$fix must be applied.` |
      | `$unpack args.p` | strict, and its argument is a run-time value, not a struct literal | `$unpack has no opcode, so it must reduce away: its argument must reduce to a struct.` |
      | `$nope {}` | in no table | `Unknown built-in '$nope'.` |

      The second message's ending comes from the rule (`BuiltinRule.needs`, here
      `'a struct'`), so a new built-in brings its own message.
    - The parser doesn't know the tables: `$nope` parses, and only `convert` rejects it.
11. **A strict built-in's argument is a head (step 4).** A rule may need its argument
    reduced first: `$unpack s` needs `s` to be a struct. `banf_reduce` reads a flag on
    the rule, so a new built-in needs no change there. `$fix` is not strict.
12. **BANF prints machine built-ins assembly style (step 2).** The name, then the
    operands separated by commas, with no parentheses and no `prim.`; a function call
    gets the keyword `call`, as in Cranelift:
    ```
    t0 = eq_i32 n, [00000000]:i32          (today: t0 = prim.eq_i32(n, [00000000]:i32))
    t2 = call fact(t1)                     (today: t2 = fact(t1))
    t3 = mul_i32 n, t2
    jump next(t0, b)                       (unchanged)
    ```
    - A data read stays a bare name (`t0 = errno`): a machine built-in always has
      operands, so `t0 = add_i32` can only be data.
    - Struct ops don't change: `{x = n, y = [01]:i8}`, `s.y`, `p.1`.
    - The golden `.banf` and `.ll` files have no prim calls and no calls, so they don't
      change; the BANF printer's unit tests do.
13. **Precedence doesn't change.** `$name` is a primary, like a variable:
    `$fix f: t` is `$fix (f: t)`, `f $fix g` is `(f $fix) g`. The rule "a lambda, `if`,
    `let` or `fix` needs parentheses as an operand" loses `fix`.
14. **`If`, `Project` and `Lambda` stay terms.** They have their own syntax, and BANF
    matches on them.
15. **"prim" goes from the code (step 2).** Everything written `$name` is a
    **built-in**. A built-in with machine code is an **opcode**, the word Cranelift and
    LLVM use for `iadd` / `add`; a kernel-only built-in has a rule and no opcode. The
    printed name (`add_i32` in `t3 = add_i32 n, t2`) is the opcode's mnemonic.

    | Today | After |
    |---|---|
    | `banf_terms.PrimCall(op, args)` | `banf_terms.OpcodeCall(opcode, args)` |
    | `banf_prim.py`, `PRIMS`, `PrimSignature` | `banf_opcodes.py`, `OPCODES`, `OpcodeSignature` |
    | `llvm_prims.py`, `DEFAULT_PRIMS`, `PrimImpl` | `llvm_opcodes.py`, `DEFAULT_OPCODES`, `OpcodeImpl` |
    | `Target.prims` | `Target.opcodes` |
    | `banf_prim_test.py` | `banf_opcodes_test.py` |
    | notes: "Prim ops" | "Opcodes" |

---

## Design

### A. `GetIndex` (step 1)

```python
@dataclass
class GetIndex:
    struct: Atom
    index: int
    location: Location | None = field(default=None, compare=False)
```

- `banf_translate.op`: before today's cases,
  `Apply(function=f, argument=i)` where `f` is an atom and `bruijn.index_value(i)` is
  not None gives `GetIndex(atom(f), index)`. An atom applied to anything else is
  `An index must be a byte array literal, such as [01].`
- `banf_terms.form_of`: the field at `index` of the struct atom's form, or
  `Form {x: i32} has no field at index 2.`
- `banf_terms.show_op`: `p.1`.
- `llvm_translate`: `builder.extract_value(struct, index)`, as for `GetField`.
- `banf_reduce`: nothing. `args.p [01]` is an apply, so it is already kept as a let's op,
  and its argument is already in whnf.

### B. `Builtin` (step 2)

```python
@dataclass
class Builtin(Term):
    """A kernel built-in, written `$name`, applied like a function: `$fix g`."""

    name: str
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from ()
```

```python
rn.PRIMARY: First(
    Ref(rn.BYTE_ARRAY), Ref(rn.STRUCT), Ref(rn.GROUP), Ref(rn.BRUIJN_INDEX), Ref(rn.BUILTIN), Ref(rn.VARIABLE)
),
# `$name`. No trivia between `$` and the name. `$` with digits is a BruijnIndex, tried first.
rn.BUILTIN: Seq(_punct('$'), Identifier(reserved=frozenset(), skip=(), ...), action=...),
```

- Printer: `$name`, at the `_PROJECT` level, like a variable.
- `bruijn`, `banf_rename`: a leaf, so `_map_children` and `other` need no case.

BANF without the `prim` binder:

| Module | Change |
|---|---|
| `banf_reduce.py` | position 1 (`prim -> <module>`) goes; the program starts at `module -> <body>` |
| `banf_rename.py` | `PRIM` is no longer a fixed name; `program` starts at `module` |
| `banf_translate.py` | the program shape is `module: {...} -> {...}`; `binder` loses `PRIM` (above a block body: lets, `args` `$k`, `blocks` `$k+1`, `module` `$k+2`); `op` turns `Apply(Builtin(name), arg)` into a `OpcodeCall` |

Messages: `prim.add_i8 must be applied.` becomes `$add_i8 must be applied.`,
`prim.sub_i32 takes {...}` becomes `$sub_i32 takes {...}`, `Unknown prim op 'add'.`
becomes `Unknown built-in '$add'.`, `'prim' cannot be used as a value.` goes, and the
program shape message drops `prim ->`.

### C. Rules (step 3)

```python
@dataclass(frozen=True)
class BuiltinRule:
    name: str
    strict: bool  # The argument must be in whnf before the rule can fire.
    needs: str  # What the argument must reduce to, for the error when it doesn't: 'a struct'.
    rule: Callable[[syntax.Term, syntax.Term], syntax.Term | None]


def _fix(call, function):
    """`$fix g` becomes `g ($fix g)`."""
    return terms.Apply(function=function, argument=call, location=call.location)


BUILTIN_RULES: dict[str, BuiltinRule] = {rule.name: rule for rule in (BuiltinRule('fix', False, 'anything', _fix),)}
```

In `reduce`, disjoint from beta (a `Lambda` callee) and struct apply (a `Struct` callee):

```python
case terms.Apply(function=terms.Builtin(name=name), argument=argument) if (
    (builtin := BUILTIN_RULES.get(name)) is not None
    and (result := builtin.rule(term, argument)) is not None
):
    return result
```

`Fix`, `unfold`, the `fix` keyword and the `FIX` rule go away.

### D. Heads (step 4)

| Term | Head |
|---|---|
| `$name a`, with `name` strict | `a` |
| `$name a`, otherwise | `$name` (as today: the callee, already in whnf) |

---

## Affected modules

| Module | Step | Change |
|---|---|---|
| `banf_terms.py` | 1, 3 | `GetIndex`, and no dynamic prims (1); remove `fix` from the printer's `_RESERVED` (3) |
| `banf_prim.py`, `llvm_prims.py` | 1, 2 | remove the dynamic prims and `extractvalue` (1); renamed `banf_opcodes.py`, `llvm_opcodes.py` (2, decision 15) |
| `banf_terms.py`, `llvm_translate.py` | 2 | `PrimCall` is `OpcodeCall`; `Target.prims` is `Target.opcodes` (decision 15) |
| `llvm_translate.py` | 1 | `GetIndex` |
| `terms.py` | 2, 3 | add `Builtin` (2); remove `Fix` (3) |
| `rule_names.py`, `grammar.py` | 2, 3 | the `BUILTIN` rule (2); remove `FIX` and `fix` from `RESERVED` (3) |
| `printer.py` | 2, 3 | `$name` (2); remove the `Fix` cases (3) |
| `bruijn.py` | 3 | `BuiltinRule`, `BUILTIN_RULES`, the `reduce` case; remove `unfold` and the `Fix` cases |
| `banf_reduce.py` | 2, 4 | no position 1 (2); the strict head (4) |
| `banf_rename.py` | 2, 3 | no `PRIM` fixed name (2); remove the `Fix` case (3) |
| `banf_translate.py` | 1, 2, 3 | `GetIndex`, no dynamic prims (1); B (2); the no-machine-code error (3) |
| golden files | 2 | `.oymo` and `.shaped.oymo` lose `prim ->`; `.banf` and `.ll` don't change |
| `docs/notes.md` | 1–4 | see each step |

---

## Open questions

None.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: a value struct applied to an index is `GetIndex`

- A, and remove `prim.extractvalue`: `DynamicPrim`, `DYNAMIC_PRIMS`, `PrimFormError`,
  `_dynamic_form`, the dynamic-prim cases in `form_of`, `_check_op` and
  `banf_translate.op`, and `DEFAULT_PRIMS['extractvalue']`.
- Tests (the `prim.extractvalue` tests become `GetIndex` tests):
  - `banf_translate`: `let y = args.p [01] in y` on a labeled and on an unlabeled param
    struct, and on a let-bound struct, prints `y = p.1`; `[0100]` and `[01]: 'i8'` are
    index 1 too; `args.p t` with `t` a let, and `args.p ''`, are
    `An index must be a byte array literal, such as [01].`; `args.p [02]` on a
    two-field struct is `Form {i32, i8} has no field at index 2.`
  - `banf_terms`: `form_of`, `show_op` and `verify` for `GetIndex`.
  - `llvm_translate`: `args.p [00]` gives the same `extractvalue` as `args.p.x`.
  - `PRIMS` and `DEFAULT_PRIMS` have the same names again.
- `docs/notes.md`: the "Dynamic prims" section goes; `GetIndex` in "What the shape is",
  `form_of`, the BANF printer, and "BANF to LLVM".
- `plan_struct_apply.md` stays as written: it is closed. `plans.md` notes that step 1
  here replaces its `prim.extractvalue`.

Commit: `oymomo: s [01] on a value struct is GetIndex`

### Step 2: `$name` built-ins replace the `prim` binder

- `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`: `Builtin` and `$name` (B).
- `banf_reduce.py`, `banf_rename.py`, `banf_translate.py`: BANF without `prim` (B).
- `banf_terms.show_op`: assembly style (decision 12); the expected BANF text in
  `banf_terms_test`, `banf_translate_test` and `docs/notes.md` changes with it.
- The rename of decision 15, in code, tests and `docs/notes.md`.
- Every program in the tests and golden files drops `prim ->`; `prim.x` becomes `$x`.
- Tests:
  - Grammar: `$fix` is `Builtin('fix')`; `$0` is still `BruijnIndex(0)`; `$fix g a` is
    `($fix g) a`; `$ fix` (with a space) and `$"fix"` are errors.
  - Printer: round trips of `$add_i32`, `$add_i32 {a = x, b = x}`, `$0`.
  - `resolve`: `$add_i32` is kept; `prim -> prim` is an ordinary lambda.
  - `banf_translate`: each changed message; a program starting with `prim ->` is
    rejected with the program shape message; `let t = $nope {} in t` is
    `Unknown built-in '$nope'.`
- `docs/notes.md`: "Program shape" and "`prim`: the machine primitives" (no binder,
  `$name`); "Kernel syntax decisions" (`$name` next to `$0`); "`convert` finds binders
  by index"; BANF positions; every example with `prim ->` or `prim.`.

Commit: `oymomo: prims are $name built-ins`

### Step 3: rules, and `fix` is `$fix`

- `bruijn.py`: C. `banf_translate.py`: the gate and the messages of decision 10; the
  `OpcodeCall` case accepts only names in `OPCODES`.
- Remove `Fix`, `FIX`, `fix` from both `RESERVED` sets, the printer's `Fix` cases,
  `unfold`, and the `Fix` cases in `bruijn` and `banf_rename`.
- Tests:
  - `reduce`: `$fix g` → `g ($fix g)`; stuck: `$fix` alone, `$fix g a` (the root only),
    `$nope g`.
  - `banf_reduce`: `$fix (self -> n -> n) a` → `a`.
  - `banf_translate`: `let t = $fix in t` is `$fix must be applied.`
  - Every `fix g` in the tests becomes `$fix g`. `fix -> fix` is a lambda.
- `docs/notes.md`: the kernel syntax table, precedence, reserved words
  (`if then else let in`), the `reduce` list, "Heads", the fuel example, and
  "Why recursion needs no `fix`".

Commit: `oymomo: fix is $fix`

### Step 4: a strict built-in's argument is a head

- `banf_reduce.py`: D.
- Tests in `banf_reduce_test.py`, with a test-only strict rule (monkeypatched
  `bruijn.BUILTIN_RULES`), such as `$first s` giving the first field of a struct:
  - `$first ((x -> x) {a = '1'})` → `'1'`: the argument is reduced, then the rule fires.
  - `$first e`, with `e` a free name, is stuck and unchanged.
  - `$fix g` still doesn't reduce `g`.
- `docs/notes.md`: the strict head in "Heads".

Commit: `oymomo: banf_reduce reduces a strict built-in's argument`

### Step 5: write the constant folding plan

Docs only. Write `docs/plan_constant_folding.md` in the same format as this plan, with
its own steps, and add it to `plans.md` as open. It gives opcodes a rule in
`bruijn.BUILTIN_RULES`, so `$add_i32 {a = [01000000]: 'i32', b = [02000000]: 'i32'}`
reduces to `[03000000]: 'i32'`. It must decide at least:

- **Same result as LLVM.** Folding must give the bytes the compiled code would give:
  little-endian, wrapping arithmetic, `i1` as one byte holding 0 or 1. A test compares
  the folded result with the result of running the LLVM code, for each prim template.
- **No undefined behaviour.** `sdiv`/`udiv`/`srem`/`urem` by zero, `sdiv`/`srem` of the
  minimum by -1, and shifts by the bit width or more are poison or undefined in LLVM.
  These must stay unreduced (the rule returns None), not fold to some value.
- **Operand shapes.** The argument is a struct, and every field must be a byte array
  literal with the right byte count; a form on it is read or ignored. That needs
  strictness on each field, not only on the argument, so step 4's `strict` flag may
  need to become per field.
- **The result's form.** The signature's result form, as a `Formed` byte array
  (`[03000000]: 'i32'`), so BANF still knows the constant's form.
- **What changes in BANF.** `let t = $add_i32 {...literals...} in t` becomes a constant,
  so lets disappear, BANF output changes, and the golden files may change. The notes'
  "Prims are not run" goes.
- **Scope.** Which templates fold first (arithmetic, comparisons, conversions), and
  whether `GetIndex` on a struct literal needs anything (it already reduces as a struct
  apply).

- Status of this plan: **implemented**.

Commit: `oymomo: plan constant folding`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: `plan_struct_pack.md` can add `$unpack` and `$pack` by adding two
entries to `bruijn.BUILTIN_RULES` (and their tests), with no other module changed.
