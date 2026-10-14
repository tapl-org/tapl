# Plan: mutable memory, with `'ptr'` and `'mem'` forms and load, store and alloca opcodes

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. The `'ptr'` form: an address, passed and returned like any value (`oymomo: add the ptr form`)
- [ ] 2. The `'mem'` form: a linear memory token, erased in LLVM (`oymomo: add the mem form`)
- [ ] 3. `$load_T` and `$store_T` opcodes, threading `mem` (`oymomo: add load and store`)
- [ ] 4. `$alloca_T` opcodes: stack slots in the entry block (`oymomo: add alloca`)
- [ ] 5. A data symbol is its address, breaking (`oymomo: module.x on data is an address`)

Step 1 alone already gives heap memory through an imported `malloc`, but nothing can
read or write it until step 3. Step 2 adds the token every memory op takes. Step 4 adds
stack memory. Step 5 makes globals writable and is the only breaking step; it depends
on open question 2.

## Goal

**A program can read and write memory**: the heap (through imported functions such as
`malloc`), the stack, and its own globals. Today every value is immutable, and the only
memory a program touches is a data symbol, read with `module.errno` (BANF `GetData`).

**Reduction keeps the meaning of memory.** Every memory op takes the memory it acts on
as a value of form `'mem'` and gives the new memory back, so an op is a pure function
of its operands. Full β may then drop or copy any let without changing what the program
does, and [plan_confluence.md](plan_confluence.md)'s guarantee covers programs, not
only terms.

```
module: {main = => {mem = 'mem', value = 'i32'}} -> {
  main = f -> {
    entry = args: {mem = 'mem'} ->
      let a = $alloca_i32 {mem = args.mem} in
      let m1 = a.mem in
      let p = a.address in
      let m2 = $store_i32 {mem = m1, address = p, value = [29000000]: 'i32'} in
      let r = $load_i32 {mem = m2, address = p} in
      let m3 = r.mem in
      let v = r.value in
      let w = $add_i32 {a = v, b = [01000000]: 'i32'} in
      let s = {mem = m3, value = w} in
      s,
  },
}
```

```
main: {mem: mem, value: i32}
  entry(mem: mem):
    a = alloca_i32 mem
    m1 = a.mem
    p = a.address
    m2 = store_i32 m1, p, [29000000]:i32
    r = load_i32 m2, p
    m3 = r.mem
    v = r.value
    w = add_i32 v, [01000000]:i32
    s = {mem = m3, value = w}
    return s
```

```llvm
define i32 @"main"()
{
entry:
  %"a" = alloca i32
  store i32 41, ptr %"a"
  %"r" = load i32, ptr %"a"
  %"w" = add i32 %"r", 1
  ret i32 %"w"
}
```

`'mem'` is erased: `m1`, `m2`, `m3` and the `mem` param have no LLVM value, and a
struct left with one field after erasure is that field, so `a` is the pointer, `r` the
loaded `i32`, and `s` the returned `i32` (decision 6).

## Decisions

### The `'ptr'` form (step 1)

1. **One named form `'ptr'`: an address, with no pointee form**, as LLVM's opaque `ptr`.
   What is at the address is said by the op that reads or writes it (`$load_i32`), not
   by the pointer. So no `'ptr i32'`, no `{ptr = 'i32'}`, and no form arithmetic.
2. **A `'ptr'` is a value like any other.** It can be a block param, a function param or
   result, a struct field, a let, an import's param or result:
   `malloc = {mem = 'mem', size = 'i64'} => {mem = 'mem', address = 'ptr'}`.
3. **No pointer constants.** Its size is a layout fact (8 bytes on x86-64, 4 on wasm32),
   so a byte array can't be formed as `'ptr'`: `[00000000 00000000]: 'ptr'` is
   `Only integer constants are supported, got ptr.` A null pointer is open question 3.

### Effects: a memory token (step 2)

4. **Memory is a value of form `'mem'`.** Every op that reads or writes memory takes a
   `mem` operand and gives a new `mem`, as GHC's `State#` or Sea of Nodes do. An op is
   then a pure function of its operands, so:
   - E-Beta stays as it is: full, lazy β, with no value restriction;
   - dropping a let whose `mem` nothing reads, or copying an op, changes nothing;
   - [plan_confluence.md](plan_confluence.md) carries over unchanged, and
     `normalize(t)` and `t` compile to the same program (with decision 7).

   This was open question 1. The alternatives were: (a) only `shape` defines meaning;
   (b) call-by-value β, which makes the kernel strict and needs a value set that no
   application is in; (d) effects as commands with a continuation, which changes every
   block body. (c), this decision, keeps let chains and lazy β, and its cost is
   decisions 5 to 7.
5. **Each `mem` is used exactly once on each path through a function.** The compiled
   code updates memory in place, which is right only if no one reads an old `mem`:

   ```
   let m1 = $store_i32 {mem = m0, address = p, value = x} in
   $load_i32 {mem = m0, address = p}        -- reads the memory before the store
   ```

   A `mem` is a name of form `'mem'` or a `'mem'` field of a name (`args.mem`, `r.mem`).
   A use is an op operand, a jump argument, or the returned value; using a whole name
   (`blocks.l r`) uses each of its `mem` fields. A branch or switch counts once if each
   target uses it once. Not once is an error from the verifier:
   `'m0' is memory and is used 2 times; memory must be used exactly once.`
   Exactly once, not at most once: a dropped `mem` would end the chain early, but LLVM
   still runs the ops after it. A function with a `mem` param must so return a `mem`.

   β keeps linearity (substituting for a binder used once uses the value once), so the
   check runs once, on BANF. A form is not a type, so the kernel itself can't check it.
6. **`'mem'` is erased in LLVM.** `erase(F)` drops every `'mem'` field and param; a
   struct form left with one field is that field's form, and with none it is `{}`. So:

   | BANF | LLVM |
   |---|---|
   | `{mem = 'mem', value = 'i32'}` | `i32` |
   | a `'mem'` param, block param, or jump argument | nothing |
   | `let m1 = r.mem` | nothing |
   | `let v = r.value`, `r` of erased form `i32` | `v` is `r`'s value |
   | `{mem = m3, value = w}` | `w` |

   The same rule erases import forms:
   `{mem = 'mem', size = 'i64'} => {mem = 'mem', address = 'ptr'}` is `ptr (i64)`.
7. **`convert` merges equal memory ops.** Full β may copy a let:
   `let a = $alloca_i32 {mem = m} in ... a.mem ... a.address` becomes
   `($alloca_i32 {mem = m}).mem` and `($alloca_i32 {mem = m}).address`, and `shape`
   lets them again as two allocas. They are the same op on the same `mem`, so they mean
   the same slot; `convert` keeps one let for each distinct op on a `mem` operand, and
   decision 5 counts uses after merging. Ops without a `mem` operand are not merged:
   copying them is already harmless.
8. **Effects happen in `mem` order, which is let order.** A let can only use earlier
   names, and each `mem` is used once (decision 5), so the memory ops of a block form one
   chain, in let order. `convert` keeps let order as today, with no scheduling.

### Memory ops are opcodes (steps 3, 4)

9. **Load, store and alloca are opcodes**, generated from templates like the others,
   one per form (monomorphic, see [notes.md › Opcodes](notes.md#monomorphic-one-op-per-signature)).
   `T` is one of `i1 i8 i16 i32 i64 ptr`:

   | Op | Signature | LLVM |
   |---|---|---|
   | `load_T` | `{mem: mem, address: ptr} => {mem: mem, value: T}` | `load T, ptr %address` |
   | `store_T` | `{mem: mem, address: ptr, value: T} => mem` | `store T %value, ptr %address` |
   | `alloca_T` | `{mem: mem} => {mem: mem, address: ptr}` | `alloca T` |

   No new BANF op, term, syntax or reserved word: they are `OpcodeCall`s. The label is
   `address`, not `ptr`, since labels name the operand's role. After erasure (decision 6)
   a load gives `T`, a store nothing, and an alloca `ptr`, which are LLVM's own results.
10. **A load takes and gives `mem`**, though it doesn't change memory. That keeps the
    chain total, so decision 8 needs no scheduling and decision 5 no special case for
    readers. The cost is that two loads can't be reordered. See open question 5.
11. **No memory opcode gets a reduction rule.** [plan_constant_folding.md](implemented/plan_constant_folding.md)
    folds an opcode whose operands are literals; a load, store or alloca never folds,
    and a `mem` is never a literal.
12. **An alloca must be in the entry block.** LLVM allows one anywhere, but outside the
    entry block it grows the stack on every pass through a loop, and LLVM's `mem2reg`
    only promotes entry-block allocas. The verifier rejects others:
    `$alloca_i32 must be in the entry block.` The translator doesn't move it, so BANF to
    LLVM stays one let to one instruction. A pointer from the entry block reaches other
    blocks as a jump argument, as any value does. See open question 4.
13. **Memory has the target's byte order.** A byte array is always little-endian
    ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)),
    and `$store_i32` of `[2a000000]: 'i32'` then `$load_i32` gives 42 on every target.
    Reading the same memory with another form (`$load_i8` after `$store_i32`) gives the
    bytes in the target's order, as in C. This is the "cost, later" that note names;
    the note now says it applies.

### Globals (step 5)

14. **A data symbol is its address.** `module.counter` on a data declaration is a
    `'ptr'` atom, the LLVM global `@counter`, instead of a read. A read is
    `$load_i32 {mem = m, address = module.counter}`, a write
    `$store_i32 {mem = m, address = module.counter, value = v}`. The address is a
    constant, so it needs no `mem`. `GetData` goes; the atom is a new
    `banf.Global(name)`, printed as the bare name. Open question 2 has the alternatives.

---

## Design

### A. Forms (steps 1, 2)

| Module | Change |
|---|---|
| `llvm_translate.llvm_type` | `'ptr'` → `ir.PointerType()`; `llvm_type(F)` is of `erase(F)` |
| `llvm_translate` constants | `'ptr'` and `'mem'` stay rejected by today's "Only integer constants" message |
| `llvm_translate` | `erase(F)` (decision 6); a name of erased form `'mem'` binds no value; a `GetField` from a struct erased to one field is that value; a `MakeStruct` erased to one field is that field |
| `banf_terms`, `banf_translate` | none for the forms: a named form is any byte array |

### B. Linearity (step 2)

`banf_terms._verify_function` gains a pass over each block: it counts the uses of each
`mem` (decision 5) in the lets and the terminal, and each block param of form `'mem'`
starts the count. A branch or switch adds one use for a `mem` that each target uses
once, and an error if the targets disagree. The error is a new `MemoryError`, or a
`FormError`.

### C. Opcodes (steps 3, 4)

```python
VALUE_FORMS = INT_FORMS + ('ptr',)

def _memory():
    for form in VALUE_FORMS:
        yield OpcodeSignature(f'load_{form}', 'load', (('mem', _MEM), ('address', _PTR)),
                              _struct(mem=_MEM, value=_named(form)))
        yield OpcodeSignature(f'store_{form}', 'store',
                              (('mem', _MEM), ('address', _PTR), ('value', _named(form))), _MEM)
        yield OpcodeSignature(f'alloca_{form}', 'alloca', (('mem', _MEM),),
                              _struct(mem=_MEM, address=_PTR))
```

`OpcodeImpl` today gets `(builder, args)`. The translator drops erased operands, so the
impls see only `address` and `value`. Load and alloca need the element type, so the
memory impls close over the form:

```python
def _load(form):   return lambda builder, args: builder.load(args[0], typ=llvm_type(form))
def _store(form):  return lambda builder, args: (builder.store(args[1], args[0]), None)[1]
def _alloca(form): return lambda builder, args: builder.alloca(llvm_type(form))
```

A store gives `None`: its result is a `mem`, which binds no value. The value name
(`%"r"`) is set by the caller, as today. `llvm_type` moves where both `llvm_opcodes`
and `llvm_translate` can use it, or `llvm_opcodes` builds the types itself.

### D. Merging (step 3)

`banf_translate.convert`: before it adds a let whose value is an `OpcodeCall` with a
`mem` operand, it looks the op up by `(opcode, atoms)`; if an earlier let in the block
has it, the new name is that let's name. Atoms compare by name, after renaming.

### E. The entry-block check (step 4)

`banf_terms._verify_function`: an `OpcodeCall` whose template is `alloca` in any block
but `blocks[0]` raises `FormError` (or a new `ShapeError`). The template is read from
`OPCODES`, so the check needs no name parsing.

### F. Globals (step 5)

| Module | Change |
|---|---|
| `banf_terms.py` | `GetData` goes; atom `Global(name)` with form `'ptr'`; `Data` docstring: writable |
| `banf_translate.py` | `module.x` on data is an atom, not an op; it can be an operand |
| `llvm_translate.py` | `Global(name)` → the `ir.GlobalVariable` itself |
| golden files | every `module.errno` read becomes a `$load_i32` on a `mem` |

---

## Breaking changes

Steps 1 to 4: none. `'mem'` is a new named form, `load_*`, `store_*` and `alloca_*` are
new opcode names, and the parser already accepts any `$name`. A function that uses no
memory needs no `mem`. Imports without a `mem` param work as today (open question 1).

Step 5: `module.x` on data is an address, so every data read changes, and a function
that reads data now needs a `mem`. `banf.GetData` goes.

---

## Open questions

1. **Imports without `mem`.** `module.putchar {...}` is an effect today, kept only
   because `shape` keeps op lets, so full β can still drop or copy it. (a) Leave such
   imports as they are; an import that touches memory declares `mem`
   (`malloc`, `free`). (b) Require `mem` on every import, breaking: `putchar` becomes
   `{mem = 'mem', c = 'i32'} => {mem = 'mem', value = 'i32'}`. (b) makes decision 4
   hold for every program; it could be its own plan.
2. **Globals.** (a) `module.x` on data is its address, breaking (decision 14,
   recommended: LLVM's meaning of `@x`, one way to read and write). (b) Keep
   `module.x` as a read and add a built-in `$address` that only `convert` understands;
   the read then needs a `mem` too. (c) Leave globals read-only for now and drop step 5.
3. **What else in this plan?** Each could be a step here or a later plan:
   - null: a `$null {}` opcode, or `ptr` constants once a target size is known;
   - pointer comparison: `eq_ptr`, `ne_ptr`;
   - addresses inside memory: `$offset {address, bytes = i64}` (a byte offset, `gep i8`),
     or a field address from a struct form (`gep {i32, i8}, 0, 1`). Byte offsets need
     layout facts in the kernel, which [Type, Form, Layout](notes.md#type-form-layout)
     keeps out;
   - load and store of struct forms (`load_{...}` isn't a name the templates can make);
   - arrays on the stack (`alloca` with a count).
4. **Allocas only in the entry block** (decision 12), or anywhere with LLVM's meaning
   (a fresh slot each time it runs), or anywhere with the translator moving them to
   the entry block (one slot per function call)?
5. **Loads that only read `mem`.** Decision 10 makes a load give a new `mem`. The
   alternative, `load_T: {mem, address} => T`, lets loads of one `mem` share it and be
   reordered, but decision 5 then needs readers (any number, all before the one writer)
   and `convert` must schedule them before the writer. Start with decision 10?
6. **The one-field rule** (decision 6): a struct erased to one field is that field.
   It makes `{mem, value}` an `i32` in LLVM and keeps C signatures for imports and
   `main`, but it also applies to a user's `{mem = 'mem', x = 'i8'}`. The alternative
   keeps `{i8}` and erases only at op results and function signatures.
7. **Names.** `load`, `store`, `alloca` follow LLVM, like the other opcodes. Cranelift
   says `stack_slot` / `stack_addr` for alloca. `'mem'` could be `'world'` or `'state'`.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: the `'ptr'` form

- A, for `'ptr'`.
- Tests:
  - `llvm_translate`: a function with a `'ptr'` param that returns it; an imported
    `malloc = {size = 'i64'} => 'ptr'` called from `main`; a struct form with a `'ptr'`
    field; `[00]: 'ptr'` is `Only integer constants are supported, got ptr.`
  - golden `heap.oymo`: call `malloc`, pass the pointer to `free`.
- `docs/notes.md`: `'ptr'` in the BANF to LLVM table; Overview's Type/Form/Layout table
  gets a pointer row.

Commit: `oymomo: add the ptr form`

### Step 2: the `'mem'` form

- A, for `'mem'` (erasure), and B.
- Tests:
  - `llvm_translate`: `main` with a `mem` param returning `{mem, value}` is
    `define i32 @"main"()`; a `mem` passed from `entry` to a loop block and back adds no
    phi; `malloc = {mem = 'mem', size = 'i64'} => {mem = 'mem', address = 'ptr'}` is
    declared `ptr (i64)`.
  - `banf_terms`: `verify` rejects a `mem` used twice, a `mem` not used, and a branch
    whose targets disagree; it accepts a branch where each target uses it once.
  - golden `heap.oymo` threads `mem` through `malloc` and `free`.
- `docs/notes.md`: the `'mem'` form and erasure in Forms and Translation; the linearity
  message in Error messages; "Reduction keeps the meaning of memory" in Design decisions.

Commit: `oymomo: add the mem form`

### Step 3: `$load_T` and `$store_T`

- C, without alloca, and D.
- Tests:
  - `opcodes`: `load_i32` and `store_ptr` signatures; both tables still have the
    same names.
  - `banf_translate`: two loads stay two lets, in `mem` order;
    `$store_i32 {value = v, mem = m, address = p}` is
    `$store_i32 takes {mem, address, value}, got {value, mem, address}.`;
    `$load_i32 {mem = m, address = args.n}` with `n: 'i32'` is
    `$load_i32 expects address: ptr, got i32.`; a term where full β copied a load
    converts to one load.
  - `llvm_translate`: load, store, and a store's `mem` returned with a value.
  - confluence ([plan_confluence.md](plan_confluence.md)): the goal program and a
    copied load give the same LLVM IR from `t` and from `normalize(t)`.
  - golden `heap.oymo` grows a store and a load through the `malloc` pointer.
- `docs/notes.md`: Opcodes table; "Effects happen in `mem` order" in Translation; the
  byte-order note in Design decisions (decision 13).

Commit: `oymomo: add load and store`

### Step 4: `$alloca_T`

- C (alloca), E.
- Tests:
  - `banf_terms`: `verify` rejects an alloca outside `blocks[0]`.
  - `llvm_translate`: `alloca i32`; a pointer passed from `entry` to a loop block.
  - golden `memory.oymo`: the goal example, and a loop that sums into a stack slot.
- `docs/notes.md`: Opcodes table; the new message in Error messages.

Commit: `oymomo: add alloca`

### Step 5: a data symbol is its address

- F, as decided by open question 2.
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
