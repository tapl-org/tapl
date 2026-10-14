# Plan: mutable memory, with a `'ptr'` form and load, store and alloca opcodes

Status: **proposed**, with open questions; 0 of 4 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. The `'ptr'` form: an address, passed and returned like any value (`oymomo: add the ptr form`)
- [ ] 2. `$load_T` and `$store_T` opcodes (`oymomo: add load and store`)
- [ ] 3. `$alloca_T` opcodes: stack slots in the entry block (`oymomo: add alloca`)
- [ ] 4. A data symbol is its address, breaking (`oymomo: module.x on data is an address`)

Step 1 alone already gives heap memory through an imported `malloc`, but nothing can
read or write it until step 2. Step 3 adds stack memory. Step 4 makes globals writable
and is the only breaking step; it depends on open question 4.

## Goal

**A program can read and write memory**: the heap (through imported functions such as
`malloc`), the stack, and its own globals. Today every value is immutable, and the only
memory a program touches is a data symbol, read with `module.errno` (BANF `GetData`).

```
module: {main = => 'i32'} -> {
  main = f -> {
    entry = args: {} ->
      let p = $alloca_i32 {} in
      let s = $store_i32 {address = p, value = [29000000]: 'i32'} in
      let v = $load_i32 {address = p} in
      let w = $add_i32 {a = v, b = [01000000]: 'i32'} in
      w,
  },
}
```

```
main: i32
  entry():
    p = alloca_i32
    s = store_i32 p, [29000000]:i32
    v = load_i32 p
    w = add_i32 v, [01000000]:i32
    return w
```

```llvm
define i32 @"main"()
{
entry:
  %"p" = alloca i32
  store i32 41, ptr %"p"
  %"v" = load i32, ptr %"p"
  %"w" = add i32 %"v", 1
  ret i32 %"w"
}
```

## Decisions

### The `'ptr'` form (step 1)

1. **One named form `'ptr'`: an address, with no pointee form**, as LLVM's opaque `ptr`.
   What is at the address is said by the op that reads or writes it (`$load_i32`), not
   by the pointer. So no `'ptr i32'`, no `{ptr = 'i32'}`, and no form arithmetic.
2. **A `'ptr'` is a value like any other.** It can be a block param, a function param or
   result, a struct field, a let, an import's param or result:
   `malloc = {size = 'i64'} => 'ptr'`, `free = {address = 'ptr'} => {}`.
3. **No pointer constants.** Its size is a layout fact (8 bytes on x86-64, 4 on wasm32),
   so a byte array can't be formed as `'ptr'`: `[00000000 00000000]: 'ptr'` is
   `Only integer constants are supported, got ptr.` A null pointer is open question 5.

### Memory ops are opcodes (steps 2, 3)

4. **Load, store and alloca are opcodes**, generated from templates like the others,
   one per form (monomorphic, see [notes.md › Opcodes](notes.md#monomorphic-one-op-per-signature)).
   `T` is one of `i1 i8 i16 i32 i64 ptr`:

   | Op | Signature | LLVM |
   |---|---|---|
   | `load_T` | `{address: ptr} => T` | `load T, ptr %address` |
   | `store_T` | `{address: ptr, value: T} => {}` | `store T %value, ptr %address` |
   | `alloca_T` | `{} => ptr` | `alloca T` |

   No new BANF op, term, syntax or reserved word: they are `OpcodeCall`s. The label is
   `address`, not `ptr`, since labels name the operand's role.
5. **`store_T` gives `{}`**, the struct form with no fields, since every op gives a value
   and there is no void form ([notes.md › Omitted forms](notes.md#omitted-forms-are-empty)).
   In LLVM the let's name is bound to the constant `{} zeroinitializer`; nothing reads
   it but a return or a jump. `{}` needs no new LLVM case: a struct form with no fields
   is the literal struct type `{}`.
6. **Effects happen in let order, as calls do today.** `module.putchar {...}` is already
   an effect: `shape` keeps every let whose value reduces to an op, dead or not, and
   `convert` keeps their order. Memory ops are ops, so they get the same guarantee, with
   no change to `banf_reduce`:
   - a let whose value is `$store_i32 {...}` is kept even if its name is never used;
   - two loads of the same address are two lets, never merged or swapped with a store;
   - an op can't be an operand ([notes.md › Operands must be atoms](notes.md#operands-must-be-atoms)),
     so no effect hides inside another op.

   The kernel itself never runs an opcode (`$load_i32 {...}` is stuck), but `shape` is
   the only strategy that keeps these lets: full β and `whnf` may inline one, which
   drops or copies its effect. Open question 1 (required) decides how to fix that.
7. **No memory opcode gets a reduction rule.** [plan_constant_folding.md](implemented/plan_constant_folding.md)
   folds an opcode whose operands are literals; a load, store or alloca never folds.
8. **An alloca must be in the entry block.** LLVM allows one anywhere, but outside the
   entry block it grows the stack on every pass through a loop, and LLVM's `mem2reg`
   only promotes entry-block allocas. The verifier rejects others:
   `$alloca_i32 must be in the entry block.` The translator doesn't move it, so BANF to
   LLVM stays one let to one instruction. A pointer from the entry block reaches other
   blocks as a jump argument, as any value does. See open question 3.
9. **Memory has the target's byte order.** A byte array is always little-endian
   ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)),
   and `$store_i32` of `[2a000000]: 'i32'` then `$load_i32` gives 42 on every target.
   Reading the same memory with another form (`$load_i8` after `$store_i32`) gives the
   bytes in the target's order, as in C. This is the "cost, later" that note names;
   the note now says it applies.

### Globals (step 4)

10. **A data symbol is its address.** `module.counter` on a data declaration is a
    `'ptr'` atom, the LLVM global `@counter`, instead of a read. A read is
    `$load_i32 {address = module.counter}`, a write `$store_i32 {address = module.counter, value = v}`.
    `GetData` goes; the atom is a new `banf.Global(name)`, printed as the bare name.
    Open question 4 has the alternatives.

---

## Design

### A. Forms (step 1)

| Module | Change |
|---|---|
| `llvm_translate.llvm_type` | `'ptr'` → `ir.PointerType()` |
| `llvm_translate` constants | `'ptr'` stays rejected by today's "Only integer constants" message |
| `banf_terms`, `banf_translate` | none: a named form is any byte array; `'ptr'` already passes as a literal form |

### B. Opcodes (steps 2, 3)

```python
VALUE_FORMS = INT_FORMS + ('ptr',)

def _memory():
    for form in VALUE_FORMS:
        yield OpcodeSignature(f'load_{form}', 'load', (('address', _PTR),), _named(form))
        yield OpcodeSignature(f'store_{form}', 'store', (('address', _PTR), ('value', _named(form))), _EMPTY_STRUCT)
        yield OpcodeSignature(f'alloca_{form}', 'alloca', (), _PTR)
```

`OpcodeImpl` today gets `(builder, args)`. Load and alloca need the element type, and
store must return the `{}` constant, so the memory impls close over the form:

```python
def _load(form):   return lambda builder, args: builder.load(args[0], typ=llvm_type(form))
def _store(form):  return lambda builder, args: (builder.store(args[1], args[0]), _EMPTY)[1]
def _alloca(form): return lambda builder, args: builder.alloca(llvm_type(form))
```

The value name (`%"v"`) is set by the caller, as today. `llvm_type` moves where both
`llvm_opcodes` and `llvm_translate` can use it, or `llvm_opcodes` builds the types
itself.

### C. The entry-block check (step 3)

`banf_terms._verify_function`: an `OpcodeCall` whose template is `alloca` in any block
but `blocks[0]` raises `FormError` (or a new `ShapeError`). The template is read from
`OPCODES`, so the check needs no name parsing.

### D. Globals (step 4)

| Module | Change |
|---|---|
| `banf_terms.py` | `GetData` goes; atom `Global(name)` with form `'ptr'`; `Data` docstring: writable |
| `banf_translate.py` | `module.x` on data is an atom, not an op; it can be an operand |
| `llvm_translate.py` | `Global(name)` → the `ir.GlobalVariable` itself |
| golden files | every `module.errno` read becomes `$load_i32 {address = module.errno}` |

---

## Breaking changes

Steps 1 to 3: none. `load_*`, `store_*` and `alloca_*` are new opcode names, and the
parser already accepts any `$name`.

Step 4: `module.x` on data is an address, so every data read changes. `banf.GetData`
goes.

---

## Open questions

> [!IMPORTANT]
> 1. **Required before step 2: how does reduction keep the meaning of effects?**
>    Confluence of terms still holds: memory opcodes have no rules, so they are stuck
>    terms, like `module.putchar {...}` today, and no rule overlap changes. What breaks
>    is that reduction keeps meaning. With decision 6, a program means its kept lets,
>    in order, but full β inlines any let, so it drops or copies effects:
>
>    | Term | Full β gives | Lost |
>    |---|---|---|
>    | `let s = $store_i32 {address = p, value = x} in args.n` | `args.n` | the store |
>    | `let p = $alloca_i32 {} in module.g {a = p, b = p}` | `module.g {a = $alloca_i32 {}, b = $alloca_i32 {}}` | one slot becomes two |
>    | `let v = $load_i32 {address = p} in let s = $store_i32 {address = p, value = y} in v` | `$load_i32 {address = p}` | the store |
>
>    So `t` and its normal form are the same term up to reduction but compile to
>    different programs, and [plan_confluence.md](plan_confluence.md)'s "every strategy
>    gives the same result" no longer covers what a program does. Calls to imports have
>    this problem today; memory makes it common. Options:
>
>    - **(a) Accept it: only `shape` runs programs.** A program's meaning is defined on
>      shaped terms; full β and `whnf` are strategies over terms only. No code change,
>      but the kernel can't reason about any term with an effect, and every future pass
>      that inlines (constant folding, a higher layer's optimizer) must know which lets
>      are effects.
>    - **(b) Call-by-value beta (Plotkin's λv).** Beta fires only when the argument is a
>      *value*: a lambda, a byte array, a variable, a built-in, or a struct or formed
>      term of values. An op such as `$store_i32 {...}` or `module.g {...}` is not a
>      value, so `(x -> body) ($store_i32 {...})` is not a redex in any order, and the
>      let is never dropped or copied. λv is confluent, so plan_confluence carries
>      over with "beta" read as βv. Cost: the kernel stops being lazy:
>      `(x -> args.n) ((y -> y y) (y -> y y))` no longer reduces to `args.n`; `$fix`
>      needs its argument to be a lambda (it is, in practice). `shape`'s let rule
>      (keep a let whose value is an op) becomes the kernel's beta rule instead of a
>      special case.
>    - **(c) A memory token.** Every memory op and call takes a value of form `'mem'`
>      and gives a new one (`$store_i32 {mem = m, address = p, value = v}` gives `m'`;
>      `$load_i32` gives `{mem, value}`), as GHC's `State#` or Sea of Nodes do. An op is
>      then a pure function of its `mem`: dropping a store whose `m'` is unused, or
>      copying one, changes nothing, so full β keeps the meaning. Cost: every op and
>      call gets a `mem` field, results become structs, `'mem'` has no LLVM type and
>      must be erased, and compiled code updates memory in place, which is right only
>      if each `mem` is used once. Nothing checks that (a form is not a type), so a
>      higher layer must.
>    - **(d) Effects as commands with a continuation.** An effectful op takes the rest
>      of the block as a lambda: `$load_i32 {address = p, then = v -> rest}`. A term
>      then describes a sequence of commands rather than running it, as Haskell's `IO`
>      does: copying or dropping a command copies or drops a description, which full β
>      may do. Running happens only in tail position of a block. Cost: block bodies
>      change from let chains to nested continuations, so `banf_reduce`, `convert` and
>      every program in the tests change; calls to imports change too.
>
>    Recommended: (b). It needs no new form or field, keeps today's let chains, makes
>    the rule `shape` already follows a kernel rule, and keeps plan_confluence's
>    guarantee meaningful for programs. It changes E-Beta, so it touches
>    plan_confluence's step 2 and [reduction_rules.md](reduction_rules.md); it may be
>    better as its own plan, done before step 2 here.
> 2. **`{}` for store's result**, or the stored value (`$store_i32` gives `v`)? The value
>    is handy for chains, but the let's name would then be a second name for `v`, and
>    LLVM's `store` has no result to bind.
> 3. **Allocas only in the entry block** (decision 8), or anywhere with LLVM's meaning
>    (a fresh slot each time it runs), or anywhere with the translator moving them to
>    the entry block (one slot per function call)?
> 4. **Globals.** (a) `module.x` on data is its address, breaking (decision 10,
>    recommended: LLVM's meaning of `@x`, one way to read and write). (b) Keep
>    `module.x` as a read and add a built-in `$address` that only `convert` understands.
>    (c) Leave globals read-only for now and drop step 4.
> 5. **What else in this plan?** Each could be a step here or a later plan:
>    - null: a `$null {}` opcode, or `ptr` constants once a target size is known;
>    - pointer comparison: `eq_ptr`, `ne_ptr`;
>    - addresses inside memory: `$offset {address, bytes = i64}` (a byte offset, `gep i8`),
>      or a field address from a struct form (`gep {i32, i8}, 0, 1`). Byte offsets need
>      layout facts in the kernel, which [Type, Form, Layout](notes.md#type-form-layout)
>      keeps out;
>    - load and store of struct forms (`load_{...}` isn't a name the templates can make);
>    - arrays on the stack (`alloca` with a count).
> 6. **Names.** `load`, `store`, `alloca` follow LLVM, like the other opcodes. Cranelift
>    says `stack_slot` / `stack_addr` for alloca.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: the `'ptr'` form

- A.
- Tests:
  - `llvm_translate`: a function with a `'ptr'` param that returns it; an imported
    `malloc = {size = 'i64'} => 'ptr'` called from `main`; a struct form with a `'ptr'`
    field; `[00]: 'ptr'` is `Only integer constants are supported, got ptr.`
  - golden `heap.oymo`: call `malloc`, pass the pointer to `free`.
- `docs/notes.md`: `'ptr'` in the BANF to LLVM table; Overview's Type/Form/Layout table
  gets a pointer row.

Commit: `oymomo: add the ptr form`

### Step 2: `$load_T` and `$store_T`

- B, without alloca.
- Tests:
  - `opcodes`: `load_i32` and `store_ptr` signatures; both tables still have the
    same names.
  - `banf_translate`: a dead store let is kept; two loads stay two lets, in order;
    `$store_i32 {value = v, address = p}` is `$store_i32 takes {address, value}, got {value, address}.`;
    `$load_i32 {address = args.n}` with `n: 'i32'` is `$load_i32 expects address: ptr, got i32.`
  - `llvm_translate`: load, store, and a store's `{}` returned from a function.
  - golden `heap.oymo` grows a store and a load through the `malloc` pointer.
- `docs/notes.md`: Opcodes table; "Effects happen in let order" in Translation; the
  byte-order note in Design decisions (decision 9).

Commit: `oymomo: add load and store`

### Step 3: `$alloca_T`

- B (alloca), C.
- Tests:
  - `banf_terms`: `verify` rejects an alloca outside `blocks[0]`.
  - `llvm_translate`: `alloca i32`; a pointer passed from `entry` to a loop block.
  - golden `memory.oymo`: the goal example, and a loop that sums into a stack slot.
- `docs/notes.md`: Opcodes table; the new message in Error messages.

Commit: `oymomo: add alloca`

### Step 4: a data symbol is its address

- D, as decided by open question 4.
- Tests: every `GetData` test becomes a load through `module.x`; a store to a defined
  global, then a load; `module.errno` as a call argument of form `'ptr'`.
- Golden files with data reads change.
- `docs/notes.md`: "Data is read-only" in BANF › Module; `GetData` rows in Ops,
  Translation and Glossary.
- Status of this plan: **implemented**.

Commit: `oymomo: module.x on data is an address`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: the goal program's LLVM IR runs under `llvmlite`'s JIT and returns
42, and a program that stores to a global in one function and loads it in another
returns the stored value.
