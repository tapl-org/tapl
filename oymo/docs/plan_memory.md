# Plan: mutable memory as linear regions: the `'mem'` form, load and store

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. The `'mem'` form and region literals: a stack slot is a value (`oymomo: add the mem form`)
- [ ] 2. `$load_T` and `$store_T` opcodes, each taking and giving a region (`oymomo: add load and store`)
- [ ] 3. Load and store fold on literal regions (`oymomo: fold load and store`)
- [ ] 4. Module regions: a data symbol of form `'mem'` is a heap at a fixed symbol (`oymomo: add module regions`)
- [ ] 5. Alias scopes: LLVM learns that regions never overlap (`oymomo: regions never alias`)

Step 1 gives regions but nothing reads or writes them until step 2. Step 3 makes the
kernel run memory ops on literals. Step 4 adds heaps that outlive a function call.
Step 5 only adds metadata. No step is breaking.

## Goal

**A program can read and write memory**, and three things hold at once:

1. **Reduction keeps the meaning of memory.** A memory op takes the region it acts on
   as a value of form `'mem'` and gives the new region back, so it is a pure function
   of its operands. Full β may drop or copy any let without changing what the program
   does, and [plan_confluence.md](plan_confluence.md)'s guarantee covers programs, not
   only terms.
2. **Regions are separate.** The stack, each heap, and each global are different
   regions, and an op can only touch the region it is given. Two live regions never
   overlap, so ops on different regions commute, in the kernel and (step 5) in LLVM.
3. **The kernel can run memory.** A region literal is a byte array formed as `'mem'`,
   and a load or store on a literal region folds, like `$add_i32` on literal operands.

Today every value is immutable, and the only memory a program touches is a data symbol,
read with `module.errno` (BANF `GetData`).

```
module: {bump = => 'i32'} -> {
  bump = f -> {
    entry = args: {n = 'i32'} ->
      let m1 = $store_i32 {mem = [00000000]: 'mem', offset = [0000000000000000]: 'i64', value = args.n} in
      let r = $load_i32 {mem = m1, offset = [0000000000000000]: 'i64'} in
      let v = r.value in
      let w = $add_i32 {a = v, b = [01000000]: 'i32'} in
      w,
  },
}
```

```
bump: i32
  entry(n: i32):
    m1 = store_i32 [00000000]:mem, [0000000000000000]:i64, n
    r = load_i32 m1, [0000000000000000]:i64
    v = r.value
    w = add_i32 v, [01000000]:i32
    return w
```

```llvm
define i32 @"bump"(i32 %"n")
{
entry:
  %"m1.mem" = alloca [4 x i8]
  store [4 x i8] zeroinitializer, ptr %"m1.mem"
  store i32 %"n", ptr %"m1.mem", align 1
  %"r" = load i32, ptr %"m1.mem", align 1
  %"w" = add i32 %"r", 1
  ret i32 %"w"
}
```

The literal `[00000000]: 'mem'` is a 4-byte region: a stack slot. The literal offset
on a literal region needs no bounds check and no `gep`, and `v` is the value `r`
loaded (design E). With `[29000000]: 'i32'` in place of `args.n`, the whole body
folds in the kernel, and BANF is `return [2a000000]:i32`:

```
$store_i32 {mem = [00000000]: 'mem', offset = [0000000000000000]: 'i64', value = [29000000]: 'i32'}
    ⇒  [29000000]: 'mem'
$load_i32 {mem = [29000000]: 'mem', offset = [0000000000000000]: 'i64'}
    ⇒  {mem = [29000000]: 'mem', value = [29000000]: 'i32'}
```

## Decisions

### Regions (step 1)

1. **A region is a value of form `'mem'`: some bytes, with a size.** What is at an
   offset is said by the op that reads or writes it (`$load_i32`), not by the region.
   A **region literal** is a byte array formed as `'mem'`: `[00000000]: 'mem'` is a
   region of four zero bytes. A region is a value like any other: a block param, a
   function param or result, a struct field, a let.
2. **An address is an offset into a region, of form `'i64'`.** There is no `'ptr'`
   form in this plan. An op names the region and the byte offset, as a WebAssembly
   memory op does, so an offset can never reach another region, whatever its value.
   Address arithmetic is `$add_i64` and friends, and address comparison is `$eq_i64`.
   Where a region lives is not observable, so it is a layout fact, left to the
   translator (decision 12). Raw C pointers and the bridge between them and regions
   belong to [plan_c_interop.md](plan_c_interop.md) phase 1.1 (open question 2).
3. **A region name is used at most once on every path.** The compiled code updates a
   region in place (decision 12), which is right only if no one reads an old version:

   ```
   let m1 = $store_i32 {mem = args.h, offset = o, value = x} in
   $load_i32 {mem = args.h, offset = o}        -- reads the region before the store
   ```

   A *region name* is a name of form `'mem'`, or a `'mem'` field of a name, by path
   (`r.mem`). A *use* is an op operand, a call or jump argument, a struct field, or a
   return; using a whole name uses every region in it; projecting another field
   (`r.value`) uses none. The verifier counts uses per block, with a branch or switch
   counted per arm: `Region 'h' is used twice; a region is used at most once.`
   At most once, not exactly once: a region nobody uses again is dead, and so is the
   store that made it, which is dead-store elimination for free.

   β keeps this: substituting a value for a binder used at most once uses the value at
   most once, and a copied op is merged back by decision 10. So the check runs once,
   on BANF. A form is not a type, so the kernel can't check it. Only names are
   counted: a literal is a value, and `g {a = [00]: 'mem', b = [00]: 'mem'}` means two
   regions, which is what the compiled code makes.
4. **A region literal lives in the frame, in the entry block, and never leaves it.**
   A literal is an `alloca`, so it dies with the function:
   - the verifier rejects a literal outside `blocks[0]`:
     `A region literal must be in the entry block.` In a loop block one slot per
     literal would alias the previous iteration's region, and one slot per pass would
     grow the stack (as LLVM's `alloca` in a loop does);
   - the verifier rejects returning a region that the frame owns:
     `Region 'm1' lives in this function's frame, so it can't be returned.` A literal
     is owned; an entry-block param and a module region are not; a load's or store's
     result owns what its `mem` operand owned; a call's result owns if any region
     passed to it did; a block param owns if any jump to it passes an owned region
     (a fixed point over the blocks). An owned region may still be passed to a call,
     since the callee can't keep it either.
5. **Live regions never overlap.** A region comes from a literal (its own `alloca`), a
   module region (its own global), or a param (the caller's region, used once by
   decision 3). No op makes one region from another. So any two region names in a
   function denote disjoint bytes, which is what step 5 tells LLVM.

### Ops (steps 2, 3)

6. **Load and store are opcodes**, generated from templates like the others, one per
   form (monomorphic, see [notes.md › Opcodes](notes.md#monomorphic-one-op-per-signature)).
   `T` is one of `i1 i8 i16 i32 i64`:

   | Op | Signature | LLVM |
   |---|---|---|
   | `load_T` | `{mem: mem, offset: i64} => {mem: mem, value: T}` | `load T` at `base + offset` |
   | `store_T` | `{mem: mem, offset: i64, value: T} => mem` | `store T` at `base + offset` |

   No new BANF op, term, syntax or reserved word: they are `OpcodeCall`s. There is no
   alloca opcode: a region literal is the slot (decision 4). A load gives its region
   back, though it doesn't change it, so that every op on a region consumes the
   version it reads: let order and data order are then the same thing (decision 11),
   and the verifier needs no special case for readers. The cost is that the kernel
   can't reorder two loads of one region; LLVM can. See open question 5.
7. **An access outside the region traps.** The compiled op checks
   `width ≤ size` and `offset ≤ size − width` and calls `llvm.trap` otherwise, so an
   offset can't reach other memory at run time either. The check is left out when the
   region is a literal and the offset a literal, and the verifier rejects that case
   when it is out of bounds: `$load_i32 at offset 4 reads past a 4-byte region.`
   The kernel never folds an access outside the region (decision 9). An unchecked
   target is open question 4.
8. **Memory is little-endian, like byte arrays, on every target.** `$store_i32` of
   `[2a000000]: 'i32'` writes those four bytes in that order, and `$load_i8` at offset
   0 then gives `[2a]`, so folding (decision 9) and running agree. On a big-endian
   target the translator byte-swaps loads and stores (`llvm.bswap`), as WebAssembly
   does. This settles the "cost, later" in
   [notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian).
   Every access is `align 1`: alignment is a layout fact (open question 3).
9. **Load and store fold on a literal region and a literal offset**, by rules in the
   style of [plan_constant_folding.md](implemented/plan_constant_folding.md):

   ```
   $load_T {mem = [m], offset = [o]}             →  {mem = [m]: 'mem', value = [m[o .. o+n)]: T}
   $store_T {mem = [m], offset = [o], value = [v]}  →  [m with v at o .. o+n]: 'mem'
       n = (N + 7) // 8 for T = iN;  [o] is 8 bytes, read little-endian;  o + n ≤ |m|
       each literal bare or with the param's form;  |v| = n
   ```

   The rules read only byte arrays, which are normal forms, so they meet
   plan_confluence's decision 5. An op on a run-time region or offset stays, and is
   kept as a let by `shape`. A store on a 1 MB literal copies 1 MB per step in the
   kernel; a heap that big is a module region (decision 13), which never folds.
10. **`convert` merges equal ops on a region name.** Full β may copy a let:
    `let r = $load_i32 {mem = h, offset = o} in let s = r in let u = r in ...`
    becomes two lets with the same load, and `h` would count twice. They are the same
    pure function of the same version, so they are one op: `convert` keeps one let for
    each distinct `(opcode, operands)` in a block whose `mem` operand is a name, and
    decision 3 counts uses after that. Ops on a literal region are never merged: each
    literal is a fresh region (decision 3). A copy that lands in operand position
    (`g {a = ($load_i32 {...}).value}`) is already rejected by
    [notes.md › Operands must be atoms](notes.md#operands-must-be-atoms); a term that
    doesn't compile is not a change of meaning.
11. **Effects happen in let order, because the chain is let order.** A let can only
    use earlier names, and each version is used once, so the ops on one region form a
    chain in let order, and ops on different regions are independent. `convert` keeps
    let order as today, with no scheduling. The kernel itself never runs an op on a
    run-time region (`$store_i32 {mem = args.h, ...}` is stuck).

### In LLVM (steps 1, 2, 5)

12. **`'mem'` is the LLVM type `{ptr, i64}`: base and size.** A literal of `N` bytes
    is `alloca [N x i8]` plus a store of the bytes, in the entry block. A store's
    result is its input region, the same two values; a load's result is the loaded
    value with the same region. Inside a function the translator keeps base and size
    as two values and packs `{ptr, i64}` only where a region is one value: a call or
    jump argument, a struct field, a return. So a chain on one region packs nothing,
    and the goal program's IR is what LLVM's `mem2reg` expects. A region param or
    result of an *imported* function is rejected for now:
    `'write' takes a region; regions can't cross to C yet.` (open question 2).

### Module regions (step 4)

13. **A data symbol of form `'mem'`, defined by a byte array, is a module region.**
    `module: {heap = 'mem', ...} -> {heap = [00000000 ...], ...}` is the LLVM global
    `@heap = global [N x i8] ...`: a heap that starts at a fixed symbol, outlives any
    call, and is not on the stack. Several such symbols are several heaps. Other data
    symbols are unchanged: `module.errno` is still a read-only read (`GetData`), and
    no symbol lives inside a heap.

    `module.heap` is the region: a BANF atom `Region('heap')`, `{ptr @heap, i64 N}`,
    with form `'mem'`, usable as an operand. It is the region's current contents, not
    a value the kernel knows, so it never folds. For in-place updates to be right it
    may appear **once in the program, in the entry block of an entry point**: a
    function that no function in the module calls. Then one activation holds it, and
    threads it from there. The verifier checks all three:
    `module.heap is used twice; a module region is used once, in the entry block of an entry point.`
    An imported region (`heap = 'mem'` with no definition) is rejected, since nothing
    gives its size: `'heap' is a region, so it must be defined.` Alternatives are in
    open question 7.

---

## Design

### A. Forms and verifier (step 1)

| Module | Change |
|---|---|
| `llvm_translate.llvm_type` | `'mem'` → `ir.LiteralStructType([ir.PointerType(), ir.IntType(64)])` |
| `llvm_translate` constants | a `Constant` of form `mem` in the entry block: `alloca [N x i8]`, a store of the bytes (`zeroinitializer` when all zero), and the pair `(ptr, N)` |
| `banf_terms._verify_function` | three passes: at-most-once use of region names (decision 3), the escape check (decision 4), literals only in `blocks[0]` (decision 4) |
| `banf_terms`, `banf_translate` | none for the form: a named form is any byte array, and a formed byte array is already a `Constant` |

The use count walks each block's lets and terminal once, with the terminal's arms
counted separately. The escape check is a fixed point over blocks on an `owned` set of
region names. Both read forms through `form_of`, so a `'mem'` field inside a struct
param is found by path.

### B. Opcodes (step 2)

```python
_MEM, _OFFSET = _named('mem'), _named('i64')

def _memory():
    for form in INT_FORMS:
        yield OpcodeSignature(f'load_{form}', 'load', (('mem', _MEM), ('offset', _OFFSET)),
                              _struct(mem=_MEM, value=_named(form)))
        yield OpcodeSignature(f'store_{form}', 'store',
                              (('mem', _MEM), ('offset', _OFFSET), ('value', _named(form))), _MEM)
```

`OpcodeImpl` today gets `(builder, args)`. For a `mem` operand the translator passes
two values, base and size. Load and store need the element type, the module's
`mem.check` and its byte order, so the memory impls close over the form and read the
rest from `builder.module`:

```python
def _load(form):
    def impl(builder, args):
        base, size, offset = args
        _check(builder, offset, width(form), size)          # skipped for literals
        value = builder.load(_address(builder, base, offset), typ=llvm_type(form), align=1)
        return base, size, _swap_if_big_endian(builder, value)
    return impl
```

`mem.check` is one private `alwaysinline` function per module, emitted on first use:
`(i64 offset, i64 width, i64 size)`, a compare, and `llvm.trap` + `unreachable` on
failure. One let stays one LLVM block; the branch is inside the helper.

### C. Merging (step 2)

`banf_translate.convert`: before it adds a let whose value is an `OpcodeCall` with a
`mem` operand that is a name, it looks the op up by `(opcode, atoms)` among the block's
lets so far; on a hit the new name is an alias of the earlier let's name, and later
atoms are rewritten through the alias map. Atoms compare by name, after `rename`.

### D. Folding (step 3)

| Module | Change |
|---|---|
| `opcodes.py` | `FOLDED_TEMPLATES` gains `load store`; `evaluate_memory(name, mem, offset, value)` on bytes, `None` when out of bounds |
| `bruijn.py` | the generated rule reads the `mem` operand as a byte array of any length, the `offset` as 8 bytes, the `value` as `n` bytes; the result of a load is a `Struct` of two `Formed` byte arrays |
| `banf_terms` verifier | a literal region with a literal offset out of bounds is an error (decision 7), since the rule left it stuck |

### E. Translation of results (step 2)

`r = load_i32 m, o` binds `r` to three LLVM values: base, size, value. `r.value` is
the loaded instruction, named `r` in the IR when `r.value` is its only use, and
`r.mem` is the pair. `m1 = store_i32 ...` binds `m1` to the operand's pair. Packing
with `insertvalue` and unpacking with `extractvalue` happen only at the places decision
12 names.

### F. Module regions (step 4)

| Module | Change |
|---|---|
| `banf_terms.py` | atom `Region(name)` with form `'mem'`; `Data` docstring: a `mem` data symbol is writable through its region; verifier: the once-in-an-entry-point rule |
| `banf_translate.py` | `module.x` on data of form `'mem'` is a `Region` atom, not `GetData`; an undefined `mem` data symbol is an error |
| `llvm_translate.py` | `@x = global [N x i8] <bytes>`; `Region(x)` → the pair `(ptr @x, N)` |

### G. Alias scopes (step 5)

`llvm_translate`: each `mem` param of a function gets an `!alias.scope` in a domain for
the function. A load or store through a region derived from param `h` (the escape
check's bookkeeping gives the origin) gets `!alias.scope` with `h`'s scope and
`!noalias` with the other params' scopes. Allocas and globals need no metadata: LLVM
already knows they don't alias each other or params.

---

## Breaking changes

None. `'mem'` is a new named form, a byte array formed as `'mem'` had no meaning
before, `load_*` and `store_*` are new opcode names, and the parser already accepts any
`$name`. A function that uses no memory needs no region. Data symbols of other forms
keep today's meaning.

---

## Open questions

> [!IMPORTANT]
> 1. **Imports and the world.** `module.putchar {...}` still has no token, so full β
>    can drop or copy a call to an import, as today. Memory is now safe from that;
>    calls aren't. The fix in the same style is a token for everything outside the
>    program (`'io'`, as GHC's `RealWorld`): every import takes and gives one, and
>    `module.errno` reads through it. That is a plan of its own, and it decides
>    whether a C-visible global is a module region or part of the world.
> 2. **C pointers.** A raw `'ptr'` and the bridge `$region {address: ptr, size: i64}`
>    (make a region of C memory, unsafe) and `$address {mem} => ptr` (hand a region to
>    C, consuming it) are where regions merge and the guarantees stop. They belong with
>    the `'io'` token in [plan_c_interop.md](plan_c_interop.md) 1.1, since `malloc`
>    and `free` are world effects too.
> 3. **Offsets and alignment.** `'i64'` offsets fit every target; `'i32'` would be
>    shorter to write and is what wasm32 uses. Every access is `align 1`; a later
>    opcode or form could promise alignment, which is a layout fact.
> 4. **An unchecked target.** Decision 7 costs a compare per access with a run-time
>    offset. A `Target(checked=False)` could drop it, at the price of guarantee 2.
> 5. **Loads that don't consume.** `load_T: {mem, offset} => T` would let the kernel
>    reorder loads of one version, but the verifier would then allow many readers
>    before one writer and `convert` would have to schedule them before it. Start with
>    decision 6?
> 6. **More ops.** Each could be a step here or a later plan: `$size {mem} => {mem, size}`;
>    `$split {mem, at} => {low, high}` and `$join`, which keep decision 5 and make
>    arenas; `$copy` between regions (`memcpy`); `$fill`; loads and stores of struct
>    forms (`load_{...}` isn't a name the templates can make, and padding is layout);
>    a repeat syntax for big literals (`[00 x 1024]` isn't oymomo syntax today).
> 7. **Module regions** (decision 13). (a) As decided: a named global, used once in an
>    entry point. (b) No module regions: a heap is an entry-block literal, and the
>    translator may place a literal of an entry point in static storage, so no
>    program-wide rule, but no symbol to name either. (c) Pass the module's regions to
>    `main` as params, which needs a notion of `main`. With function pointers
>    ([plan_c_interop.md](plan_c_interop.md) 1.6) an entry point can be re-entered
>    through a callback, and (a) must be revisited then.
> 8. **Names.** `'mem'` or `'region'`; `offset` or `at`; `load`, `store` follow LLVM.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: the `'mem'` form and region literals

- A.
- Tests:
  - `llvm_translate`: a function with a `'mem'` param that returns it is
    `define {ptr, i64} @"g"({ptr, i64} %"h")`; a literal `[00000000]: 'mem'` in the
    entry block is `alloca [4 x i8]` and a store of zeros; a literal of non-zero bytes
    stores them; a region passed from `entry` to a loop block is a phi of `{ptr, i64}`;
    a struct form with a `'mem'` field; an import with a `'mem'` param is rejected.
  - `banf_terms`: `verify` rejects a region used twice in one block, accepts one used
    in each arm of a branch, rejects a literal outside `blocks[0]`, rejects returning
    a literal, a struct holding one, and a block param fed by one, and accepts
    returning a param.
  - golden `region.oymo`: a region param threaded through a call and returned.
- `docs/notes.md`: `'mem'` in the BANF to LLVM table; Overview's Type/Form/Layout
  table gets a region row; "A region is used at most once" and the escape check in
  BANF; the messages in Error messages.

Commit: `oymomo: add the mem form`

### Step 2: `$load_T` and `$store_T`

- B, C, E.
- Tests:
  - `opcodes`: `load_i32` and `store_i8` signatures; both tables still have the same
    names.
  - `banf_translate`: two loads stay two lets, in order;
    `$store_i32 {value = v, mem = m, offset = o}` is
    `$store_i32 takes {mem, offset, value}, got {value, mem, offset}.`;
    `$load_i32 {mem = args.n, offset = o}` with `n: 'i32'` is
    `$load_i32 expects mem: mem, got i32.`; a term where full β copied a load
    converts to one load; one that copied a store on a literal converts to two.
  - `llvm_translate`: the goal program's IR; a load at a run-time offset calls
    `mem.check`; a store on a region param returns the param's pair; a big-endian
    `data_layout` swaps bytes; `test_fold_matches_llvm`-style: a store then a load of
    each width through LLVM's JIT gives the stored value.
  - confluence ([plan_confluence.md](plan_confluence.md)): the goal program and a
    copied load give the same BANF from `t` and from `normalize(t)`.
  - golden `memory.oymo`: the goal example, and a loop that sums into a slot.
- `docs/notes.md`: Opcodes table; "Effects happen in let order" and merging in
  Translation; byte order in Design decisions (decision 8).

Commit: `oymomo: add load and store`

### Step 3: folding

- D.
- Tests:
  - `bruijn`: the goal's folded chain; a load of each width at offset 1 of a 9-byte
    literal; a store that keeps the other bytes; an out-of-bounds offset stays stuck;
    a run-time offset stays stuck; a bare `[..]` region and offset fold.
  - `banf_translate`: the folded goal gives `return [2a000000]:i32`; an out-of-bounds
    literal access is `$load_i32 at offset 4 reads past a 4-byte region.`
  - `llvm_translate.test_fold_matches_llvm` gains `load_T` and `store_T` samples.
- `docs/notes.md`: Opcodes › Folding; the kernel's reduce table.

Commit: `oymomo: fold load and store`

### Step 4: module regions

- F.
- Tests:
  - `banf_translate`: `module.heap` is a `Region` atom; used twice is an error; used
    in a loop block is an error; used in a function that `main` calls is an error;
    an undefined `mem` symbol is an error.
  - `llvm_translate`: `@heap = global [8 x i8] zeroinitializer`; a store and a load
    through it; a non-zero initializer.
  - golden `heap.oymo`: a heap of 16 bytes, written by `main`, passed to a function
    that reads it.
- `docs/notes.md`: `module` declarations table gets the `mem` row; Symbols; the
  messages.

Commit: `oymomo: add module regions`

### Step 5: alias scopes

- G.
- Tests: `llvm_translate`: a function with two region params emits `!alias.scope` and
  `!noalias` on each access, and LLVM's verifier accepts the module; a function with
  one region param emits none.
- `docs/notes.md`: BANF to LLVM: "regions never overlap".
- Status of this plan: **implemented**.

Commit: `oymomo: regions never alias`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: the goal program's LLVM IR runs under `llvmlite`'s JIT and `bump(41)`
returns 42; the folded goal compiles to `ret i32 42`; a program that writes a module
region in `main` and reads it in a callee returns the written value; a load at offset
4 of a 4-byte region param traps under the JIT.
