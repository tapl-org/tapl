# Plan: memory as in LLVM: the `'ptr'` form, alloca, getelementptr, load and store

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. `$after`: an identity the kernel can't see through orders effects (`oymomo: add $after`)
- [ ] 2. The `'ptr'` form, `'alloca'` and `'getelementptr'` (`oymomo: add the ptr form`)
- [ ] 3. `'load'` and `'store'` (`oymomo: add load and store`)
- [ ] 4. Tests: what full β does to effects without `$after` (`oymomo: test unordered effects`)
- [ ] 5. Arrays, vectors and packed structs as tagged pairs (`{'array', {element, count}}`) (`oymomo: add aggregate forms`)

Step 1 doesn't depend on the others: it orders effects, which memory ops are, as calls
to imports already are. Step 2 makes and moves pointers, but nothing reads or writes
through them until step 3. Step 4 needs step 3: it uses loads and stores to show why
step 1 exists. Step 5 needs only forms, but its tests use step 3's loads and stores.
Steps 2 and 3 build on [plan_vm.md](plan_vm.md) step 3 (done): memory ops are
entries of the opcode table, called as `'name' {...}`, as every opcode is.
The kernel never folds a memory op (decision 13); LLVM does.
No step is breaking.

## Goal

**A program can read and write memory with LLVM's instructions and their operands.**
A pointer is a value of form `'ptr'`, LLVM's opaque `ptr`. `'alloca'` makes one,
`'getelementptr'` moves it, `'load'` reads through it, `'store'` writes through it. Each
is one LLVM instruction with LLVM's operands, in LLVM's order, and where LLVM writes
a type, oymomo passes the form as a value (`form = 'i32'`, `form = {x = 'i32', y =
'i64'}`), as every opcode does ([plan_vm.md](plan_vm.md) decision 10). Nothing more:
no bounds checks, no regions, no tokens.

Memory ops are effects, like calls to imports. The term doesn't order them; a
program orders them by hand with `$after` (decisions 1 to 4), as it orders calls to
imports. [plan_confluence.md](plan_confluence.md)'s guarantee covers the term, not the
order of effects (decision 4).

Today every value is immutable, and the only memory a program touches is a data symbol,
read with `module.errno` (BANF `GetData`).

```
module: {bump = => 'i32'} -> {
  bump = f -> {
    entry = args: {n = 'i32'} ->
      let p = 'alloca' {'i32'} in
      let s = 'store' {args.n, p} in
      let v = 'load' {'i32', $after {p, s}} in
      let w = 'add' {'i32', v, [01000000]} in
      w,
  },
}
```

```
bump: i32
  entry(n: i32):
    p = alloca i32
    s = store n, p
    v = load i32, p
    w = add i32 v, [01000000]:i32
    return w
```

```llvm
define i32 @"bump"(i32 %"n")
{
entry:
  %"p" = alloca i32
  store i32 %"n", ptr %"p"
  %"v" = load i32, ptr %"p"
  %"w" = add i32 %"v", 1
  ret i32 %"w"
}
```

`$after {p, s}` is `p`, but it makes the load wait for the store (decision 1), and
`convert` drops it, so BANF and LLVM never see it. Without it nothing uses `s`, and
full β could drop the store. With `[29000000]: 'i32'` in place of `args.n`, the kernel
still leaves the three memory lets alone (decision 13), and LLVM's `mem2reg` turns the
body into `ret i32 42`.

A struct in memory, and the address of its second field:

```
let q = 'alloca' {{x = 'i32', y = 'i64'}} in
let y = 'getelementptr' {{x = 'i32', y = 'i64'}, q,
                         {[0000000000000000]: 'i64', [01000000]: 'i32'}} in
...
```

```llvm
  %"q" = alloca {i32, i64}
  %"y" = getelementptr {i32, i64}, ptr %"q", i64 0, i32 1
```

`$after` also orders calls to imports:

```
let q = module.putchar {c = [68000000]: 'i32'} in
let r = module.putchar {c = $after {[69000000]: 'i32', q}} in
r
```

```
q = putchar [68000000]:i32
r = putchar [69000000]:i32
return r
```

## Decisions

### Ordering effects (step 1)

1. **`$after {x, d1, ..., dn}` is `x`, and the kernel can't see that.** Field 0 is
   the value; the others are what it waits for. Fields are positional, and labels are
   ignored, as in a branch. `after` has no rule and is not an opcode, so `reduce`
   never fires on it (a built-in with no rule is already not a redex): no kernel
   change. It keeps its `$` because `convert` treats it specially. Since `x`
   now uses every `dᵢ`, full β can't drop a `dᵢ`, and a let that uses `$after` comes
   after every let it waits for:

   ```
   let q = module.putchar {c = [68000000]: 'i32'} in
   let r = module.putchar {c = $after {[69000000]: 'i32', q}} in
   r
   ```

   Without `$after`, nothing uses `q`, so full β drops the first call and the program
   prints `i`. `$after` orders calls to imports and memory ops
   (`'load' {'i32', $after {p, s}}`).
2. **`$after` may be an operand.** With atoms as fields it is an atom: an op argument,
   a jump argument, a branch condition, a return, or a let's value. This is one
   exception to [notes.md › Operands must be atoms](notes.md#operands-must-be-atoms),
   because it stands for its field 0, which is an atom. (The other is a form field of
   an opcode, such as `form` ([plan_vm.md](plan_vm.md) decision 10).)
3. **`convert` drops it.** `$after {x, ...}` becomes the atom `x`, and
   `let c = $after {...}` binds no BANF let: `c` is an alias of `x`. So BANF, the
   verifier, `form_of` and LLVM never see it, and it needs no form. After `convert`,
   order is let order alone, which BANF keeps: no BANF pass reorders or removes a let,
   and LLVM keeps calls to imports and memory ops in order.
4. **Ordering is by hand and unchecked.** An effect that nothing uses, directly or
   through `$after`, can still be dropped by full β; two effects with no chain between
   them have no order; a let used twice can be copied, so a load can run twice, once
   on each side of a store. `$after` gives a program a way to order effects, not a
   guarantee. A check is open question 1.

### Pointers and memory ops (steps 2, 3)

5. **A pointer is a value of form `'ptr'`: LLVM's opaque `ptr`.** It says nothing
   about what it points to; the op that reads or writes says that. A pointer is a
   value like any other: a block param, a function param or result, a struct field,
   a let, and a param or result of an imported function, where it is C's `T *` (a
   step toward [plan_c_interop.md](plan_c_interop.md) 1.1).
6. **A pointer can't be a literal.** The kernel's byte arrays have no address to
   name, and a null pointer is open question 3. The verifier rejects
   `[0000000000000000]: 'ptr'`: `A pointer can't be a literal.`
7. **Memory ops are LLVM's instructions, with the form as an operand.** LLVM's
   `alloca`, `getelementptr` and `load` take a type, and the type can be any type:
   `i32`, `{i32, i64}`, `[16 x i8]`. So they take it as a `form` field, as every
   opcode does after [plan_vm.md](plan_vm.md) step 3 (`'add' {'i32', a, b}`),
   and as forms are terms ([notes.md › Forms are terms](notes.md#forms-are-terms)).
   They are four impure entries of the opcode table, named as in LLVM, with
   fields in LLVM's operand order:

   | Symbol | Fields | Gives | LLVM |
   |---|---|---|---|
   | `'alloca'` | `form`, and `count` if not 1 | `ptr` | `alloca F` / `alloca F, iN count` |
   | `'getelementptr'` | `form`, `ptr`, `indices` | `ptr` | `getelementptr F, ptr ptr, iN i0, ...` |
   | `'load'` | `form`, `ptr` | `F` | `load F, ptr ptr` |
   | `'store'` | `value`, `ptr` | `{}` | `store F value, ptr ptr` |

   - `form` must reduce to a literal form (a named form, a struct, or a tagged pair of
     decision 8, of literal forms), as a binder's form must for BANF; it is a form,
     not an operand, so it stays in place and is never let-bound. `'ptr'` is a literal
     form too, so a pointer can be stored and loaded.
   - `'store'` has no `form`: LLVM's `store F value` names the value's own type, and an
     oymomo value carries its form (`form_of`).
   - `count` and each index may be any integer form, as in LLVM. An index into a
     struct or packed struct must be a literal `'i32'` inside its field count, as in
     LLVM: `'getelementptr': index 1 into {x: i32} must be a literal 'i32' below 1.`
     Struct fields are indexed by position, not label, as in LLVM. An index into an
     array or a vector may be known only at run time.
   - The first index of `'getelementptr'` steps by whole `F`s, so a byte offset is
     `'getelementptr' {'i8', p, {o}}`. It is not `inbounds`.
   - Fields are positional and labels are ignored, as for every opcode
     ([plan_vm.md](plan_vm.md) decision 7): `'store' {v, p}` stores `v` at `p`, as
     LLVM's `store F v, ptr p`.
8. **LLVM's other aggregate types are tagged pairs.** A plain struct form stays
   LLVM's struct, as today. Every other LLVM type that is not a named form is a
   two-field struct: a tag, a byte array naming the type, then a struct of its
   parts, positional and in the order LLVM writes them, as for opcodes:

   | Form | LLVM | Parts |
   |---|---|---|
   | `{x = 'i32', y = 'i64'}` | `{i32, i64}` | the fields, as today |
   | `{'packed', {x = 'i8', y = 'i32'}}` | `<{i8, i32}>` | the fields, as for a struct; no padding |
   | `{'array', {[03000000]: 'i32', 'i32'}}` | `[3 x i32]` | `count`, `element` |
   | `{'vector', {[04000000]: 'i32', 'i32'}}` | `<4 x i32>` | `count`, `element` |
   | `{'scalable_vector', {[04000000]: 'i32', 'i32'}}` | `<vscale x 4 x i32>` | `count`, `element` |

   - **Only BANF and LLVM read the tag.** To the kernel a tagged pair is a struct like
     any other: no rule, no built-in, no kernel change. β builds them as it builds
     any struct: `let bytes = n -> {'array', {n, 'i8'}} in ...`.
     BANF needs them literal, as every form.
   - **The tag can't be mistaken for a field's form.** The named forms LLVM accepts
     are a closed set (`'i1'` to `'i64'`, and `'ptr'` from step 2), so `'array'` is
     never a data form, and no plain struct that reaches LLVM has it as field 0.
     `{'i32', {x = 'i8'}}` is still a plain struct,
     `{i32, {i8}}`. The four tags are reserved names: a later plan that lets a
     program name its own forms can't use them.
   - The pair has exactly two fields; anything else whose field 0 is a reserved tag
     is an error: `'array' form must be {'array', {count, element}}.` Labels are
     ignored, in the pair and in its parts (a packed struct's own field labels
     excepted, as a struct's).
   - `count` is a literal of any integer form, read unsigned; a vector's is above 0.
     `element` is a literal form; a vector's is an integer form or `'ptr'`. A
     scalable vector can't be inside a struct, a packed struct or an array, as in
     LLVM.
   - `'alloca'`'s `count` stays: `'alloca' {{'array', {[10000000]: 'i32', 'i32'}}}` is
     a `[16 x i32]` slot, and `'alloca' {'i32', n}` is `n` slots, where `n` may be known only at run time, as in LLVM.
   - Rejected:
     - a tag field (`{tag = 'array', element = 'i32', ...}`): it reserves the label
       `tag`, so `{tag = 'i8', data = ...}`, an ordinary struct, would read as a
       tagged form; or every struct writes `{tag = 'struct', ...}`, which breaks
       every program. The pair's tag is a position, not a label, and its value is a
       name no data form has.
     - `$array {...}` and friends: a `$` built-in is for something with special
       behaviour, and these have none.
     - `'array' {...}`, a byte array applied to a struct: that shape is kept for
       calls to virtual machine symbols ([plan_vm.md](plan_vm.md)).
     - `{...}: 'array'`: `:` means a value with a form, and here there is no value.
   - Not here: LLVM's named (identified) structs (`%T = type {...}`), which allow
     recursive types, and opaque structs. Floating-point forms are their own plan;
     once they exist, a vector's element may be one.
9. **An `alloca` may be in any block, as in LLVM.** One in a loop block grows the
   stack on each pass, and only entry-block ones are promoted by `mem2reg`. Its memory
   dies with the function, and a pointer to it used after that is undefined, as in
   LLVM; nothing checks it.
10. **Two different pointers may alias.** LLVM's own alias analysis is all there is:
    it knows two `alloca`s are distinct, and that an `alloca` that doesn't escape
    isn't reached through a param. Saying more (`noalias`, `!alias.scope`) is open
    question 4.
11. **A store gives `{}`, which only `$after` may use.** LLVM's `store` gives no
    value, and oymomo has no `void` yet ([plan_c_interop.md](plan_c_interop.md) 1.2).
    The result form is the empty struct, so the let has a name to wait for, and the
    verifier rejects any other use: `'s' is the result of a store; only $after can
    use it.` In LLVM the let binds nothing.
12. **Accesses are as LLVM's defaults: target byte order, ABI alignment, no checks.**
    A load or store carries no `align`, so LLVM assumes the type's ABI alignment, and
    an access through a misaligned or dangling pointer is undefined, as in C. Byte
    order is the target's: on a big-endian target, storing `[2a000000]: 'i32'` and
    loading `'i8'` at the same pointer gives `[00]`. This is unlike byte array
    literals, which are little-endian everywhere
    ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)),
    but memory has no literals, so the two never meet. A struct's layout (padding,
    field offsets) is LLVM's for the target. See open question 2.
13. **Memory ops never fold in the kernel.** `alloca`, `getelementptr`, `load` and
    `store` are impure opcodes, and the kernel folds only pure ones
    ([plan_vm.md](plan_vm.md) decision 8), so they are stuck: no kernel change. The
    kernel has no memory to run them on. LLVM folds what can be folded (`mem2reg`,
    SROA, `instcombine`).

---

## Design

### A. `$after` (step 1)

| Module | Change |
|---|---|
| `reduction.py` | none: `after` has no rule in `BUILTIN_RULES`, and a built-in with no rule is not a redex |
| `banf_shape.py` | `atom`: for `$after {...}`, each field is reduced as an atom, so `$after {{a = q}.a, r}` reaches `$after {q, r}` |
| `banf_translate.py` | `AFTER = 'after'`, checked in `op` before anything else; `_Translator.atom` reads `$after {x, d1, ..., dn}` as the atom of `x`, after checking `n ≥ 1` and that each `dᵢ` is an atom; `body` binds `let c = $after {...}` as an alias of that atom, not a `Let` |
| `banf_terms.py`, `llvm_translate.py` | none |

`_Block.binder` counts lets to resolve an index, so an alias still takes a binder
slot: `_Block` keeps one entry per let binder, a `Let` it emitted or the atom it
aliases, and `atom` returns the aliased atom for an alias.

### B. Pointers, `'alloca'`, `'getelementptr'` (step 2)

Everything generic is already in plan_vm step 3: the call shape, the `OpcodeCall` op,
form params reduced in place and never let-bound, fields read by position, and
lowering through an entry's `llvm`. What is left is two table entries and their
checks.

| Module | Change |
|---|---|
| `reduction.py`, `banf_shape.py` | none (decision 13; form params are plan_vm's) |
| `opcodes.py` | entries `alloca` (form param `form`, optional value param `count` of any integer form, result `'ptr'`) and `getelementptr` (form param `form`, `ptr: 'ptr'`, `indices`, result `'ptr'`), impure, each with a `check` for decision 7's rules and an `llvm`: `builder.alloca(llvm_type(form), size=count)`, `builder.gep(ptr, indices, source_etype=llvm_type(form))` |
| `banf_terms.py` | `show_form` for `'ptr'`; printed `alloca {i32, i64}`, `getelementptr {i32, i64}, q, [00..]:i64, [01000000]:i32`; verifier: a `Const` of form `ptr` is an error (decision 6) |
| `llvm_translate.py` | `llvm_type`: `'ptr'` → `ir.PointerType()` |

### C. `'load'` and `'store'` (step 3)

| Module | Change |
|---|---|
| `opcodes.py` | entries `load` (form param `form`, `ptr: 'ptr'`, result `form`) and `store` (`value` of any form, `ptr: 'ptr'`, result `{}`), impure; `llvm`: `builder.load(ptr, typ=llvm_type(form))`, `builder.store(value, ptr)`, the let binding no LLVM value |
| `banf_terms.py` | verifier: a name bound by a `store` let is used nowhere (decision 11); `$after` is gone by then, so any use is an error |
| `banf_translate.py` | none: `ptr` must have form `'ptr'` is the table's param check: `'load' expects ptr: ptr, got i32.` |

### D. Tagged pairs for arrays, vectors and packed structs (step 5)

| Module | Change |
|---|---|
| `reduction.py`, `terms.py` | none: a tagged pair is a struct |
| `banf_shape.py` | none: a struct form is already reduced to normal form in place |
| `banf_terms.py` | `FORM_TAGS = {'array', 'vector', 'scalable_vector', 'packed'}` and `tagged_form(form) -> (tag, parts) \| None`, the one reader every BANF and LLVM stage uses; `show_form`: `[3 x i32]`, `<4 x i32>`, `<vscale x 4 x i32>`, `<{i8, i32}>`, as LLVM prints them; the verifier compares forms with `==`, which already covers structs |
| `banf_translate.py` | `_check_data_form` reads a struct with `tagged_form` first, and checks a tagged pair by the rules of decision 8, recursively; `count` read as an unsigned little-endian integer |
| `llvm_translate.py` | `llvm_type`: `ir.ArrayType(e, n)`, `ir.VectorType(e, n)`, `ir.LiteralStructType(fs, packed=True)`; a scalable vector raises, as llvmlite has no scalable vector type; `GetElementPtr` accepts a run-time index into an array or vector |

---

## Cranelift's memory model

How Cranelift IR (CLIF) does memory, next to LLVM and this plan.

| | Cranelift | LLVM | Here |
|---|---|---|---|
| Address | no pointer type: an integer of pointer width (`i64` on 64-bit targets) | opaque `ptr` | `'ptr'` (decision 5) |
| Type of an access | a suffix on the opcode (`load.i32`); only scalar and vector types | an operand, any first-class type, aggregates included | `form`, any literal form (decision 7) |
| Load, store | `v = load.i32 flags p+16`, `store flags v, p+16`: an immediate `i32` offset is part of the access; store gives nothing | `load`, `store`; the offset is a separate `getelementptr` | `'load'`, `'store'`, `'getelementptr'` |
| Narrow access | `uload8`, `sload8`, `uload16`, `sload16`, `uload32`, `sload32` extend; `istore8`, `istore16`, `istore32` truncate | `load i8` then `zext`/`sext`; `trunc` then `store i8` | the same as LLVM: `'load' {'i8', p}` then `'zext'` |
| Stack | `ss0 = explicit_slot 8` in the function preamble, sized in bytes; `stack_load`, `stack_store`, `stack_addr`; `dynamic_stack_slot` for scalable vectors | `alloca T` or `alloca T, iN n` anywhere | `'alloca'` (decisions 7 to 9) |
| Field address | integer arithmetic: the frontend computes the offset | `getelementptr` with struct and array indices | `'getelementptr'` with struct indices (decision 7) |
| Globals | `global_value` entities: `symbol` (a linker symbol), `vmctx`, `load` and `iadd_imm` chains; `symbol_value`, `global_value`, `tls_value` instructions | a global is a `ptr` constant | open question 5 |
| Flags on an access | `MemFlags`: can trap or not (`notrap`, trap code), `aligned`, `readonly`, `can_move`, `checked`, byte order `little`/`big` per access, an alias region | `align`, `volatile`, `atomic`; `!noalias`, `!tbaa`, `!invariant.load` metadata; byte order is the target's | none (decision 12) |
| Aliasing | alias regions on `MemFlags`: two accesses in different regions don't alias; regions are named by the frontend | `noalias`, scopes, TBAA, and its own analysis | LLVM's own analysis (decision 10) |
| Atomics | `atomic_load`, `atomic_store`, `atomic_rmw`, `atomic_cas`, `fence`; sequentially consistent only | `load atomic`, `store atomic`, `atomicrmw`, `cmpxchg`, `fence`; every ordering | no |
| Bulk | no instruction: `FunctionBuilder::call_memcpy`, `call_memset`, `call_memmove` call libc, and `emit_small_memory_copy` inlines small ones | `llvm.memcpy`, `llvm.memmove`, `llvm.memset` | no (open question 3) |
| Bounds-checked heaps | there was a `heap` entity and `heap_addr`; it was removed from CLIF, and Wasmtime's translator now emits the checks as plain compares and traps | none | none: the regions of the earlier draft were this, and were dropped |
| Effect order | a block's side-effecting instructions stay in order; the optimizer moves only pure ones, and loads flagged `readonly` and `can_move` | instruction order, then alias analysis | let order after `convert`, set by hand with `$after` (decision 4) |

Two things to take from it. A pointer-width integer address (Cranelift) would save the
`'ptr'` form, but then an imported function's `T *` param and an `i64` would look the
same, and LLVM, which this plan follows, would need `inttoptr` everywhere. And both
IRs keep effects in instruction order; oymomo's term doesn't, which is why `$after`
comes first.

---

## LLVM memory operations

Every LLVM instruction, intrinsic and annotation that reads, writes, allocates or
describes memory, and where it stands in this plan. "Used" means a step emits it.

### Instructions

| LLVM | What it does | Here |
|---|---|---|
| `alloca` | a stack slot in the frame | used, step 2: `'alloca'` |
| `getelementptr` | address arithmetic on a pointer | used, step 2: `'getelementptr'` |
| `load` | read a value at an address | used, step 3: `'load'` |
| `store` | write a value at an address | used, step 3: `'store'` |
| `load volatile`, `store volatile` | an access LLVM may not drop or reorder | no: memory-mapped I/O, later |
| `load atomic`, `store atomic` | an access with a memory ordering | no: no threads |
| `atomicrmw` | atomic read-modify-write (`add`, `xchg`, ...) | no: no threads |
| `cmpxchg` | atomic compare and exchange | no: no threads |
| `fence` | order accesses between threads | no: no threads |
| `ptrtoint`, `inttoptr` | pointer to integer and back | no: open question 3 |
| `icmp` on `ptr` | compare pointers | no: open question 3 |
| `addrspacecast` | change a pointer's address space | no: one address space |

### Intrinsics

| LLVM | What it does | Here |
|---|---|---|
| `llvm.memcpy`, `llvm.memcpy.inline` | copy bytes; source and destination don't overlap | no: open question 3 |
| `llvm.memmove` | copy bytes that may overlap | no: open question 3 |
| `llvm.memset`, `llvm.memset.inline` | fill bytes with one byte | no: open question 3 |
| `llvm.experimental.memset.pattern` | fill bytes with a repeated value | no |
| `llvm.lifetime.start`, `llvm.lifetime.end` | where an `alloca` is live | no |
| `llvm.invariant.start`, `llvm.invariant.end` | memory that doesn't change for a while | no |
| `llvm.launder.invariant.group`, `llvm.strip.invariant.group` | C++ vtable invariants | no |
| `llvm.stacksave`, `llvm.stackrestore` | scope a dynamic `alloca` | no: would bound the stack growth of an `alloca` in a loop (decision 9) |
| `llvm.masked.load`, `llvm.masked.store` | vector access with a lane mask | no: no vector forms |
| `llvm.masked.gather`, `llvm.masked.scatter` | vector access at a vector of addresses | no: no vector forms |
| `llvm.masked.expandload`, `llvm.masked.compressstore` | vector access to consecutive lanes | no: no vector forms |
| `llvm.vp.load`, `llvm.vp.store`, `llvm.vp.gather`, `llvm.vp.scatter`, `llvm.experimental.vp.strided.load`, `llvm.experimental.vp.strided.store` | vector-predicated access | no: no vector forms |
| `llvm.prefetch` | a cache hint | no |
| `llvm.objectsize` | the size of the object behind a pointer | no |
| `llvm.ptrmask` | mask a pointer's bits | no |
| `llvm.threadlocal.address` | the address of a thread-local global | no: no threads |
| `llvm.load.relative` | load a pointer stored as a relative offset | no |
| `llvm.assume` | a fact the optimizer may use | no |

### Metadata and attributes

| LLVM | What it says | Here |
|---|---|---|
| `align` on an access | the address is a multiple of N | not emitted: ABI alignment (decision 12, open question 2) |
| `inbounds` on `getelementptr` | the result stays inside the object | no (decision 7) |
| `!alias.scope`, `!noalias` | which accesses don't alias | no: open question 4 |
| `noalias` on a param | the param's memory is reached only through it | no: open question 4 |
| `dereferenceable(N)`, `nonnull` | the pointer reaches N bytes | no |
| `!tbaa` | type-based alias analysis | no |
| `!invariant.load` | the loaded memory never changes | no |
| `!nontemporal` | the access is not reused soon | no |
| `memory(...)` on a function | what memory a function touches | no |

C's `malloc`, `realloc` and `free` are calls, not LLVM operations: with a `'ptr'`
result, an import declares them (`malloc = {size = 'i64'} => 'ptr'`).

---

## Breaking changes

None here. `'ptr'` is a new named form, and `'alloca'`, `'getelementptr'`, `'load'`
and `'store'` were unknown opcodes, an error in `convert`. (Renaming `$add_i32` to
`'add' {'i32', a, b}` is breaking, but it is [plan_vm.md](plan_vm.md) step 3.)
Data symbols keep today's meaning. `$after` was an unknown built-in, and the parser
already accepts any `$name`. A
plain struct form keeps its meaning; a struct whose field 0 is `'array'`, `'vector'`,
`'scalable_vector'` or `'packed'` had no LLVM type before, so no working program
changes meaning.

---

## Open questions

> [!IMPORTANT]
> 1. **Checking order** (decision 4). `convert` could check, before it drops
>    `$after`, that the effects of a block (memory ops, calls to imports, and calls to
>    functions that make them) form one chain by data dependency, and that the
>    terminator depends on the last: `'store' at line 4 is not ordered after 'load' at
>    line 3; chain them with $after.` A token (`'io'`, as GHC's `RealWorld`) that every
>    effect takes and gives would make the chain part of the signature. Later, or in
>    step 1?
> 2. **Alignment and byte order** (decision 12). An optional `align` field, as LLVM's
>    `align N`, for packed data; a byte order field for portable formats, as
>    Cranelift's per-access `little`/`big`.
> 3. **More ops.** `'ptrtoint'`, `'inttoptr'`, comparing pointers, a null pointer
>    (`'null'` or a literal exception to decision 6), `'memcpy'`, `'memmove'`, `'memset'`.
> 4. **Aliasing** (decision 10). `noalias` on `'ptr'` params, or alias scopes, need a
>    promise the program makes and nothing checks.
> 5. **Globals.** `module.x` reads a data symbol (`GetData`). Writing one needs its
>    address: a data symbol of form `'ptr'`? `'address' {module.x}` as a new reading of
>    `module.x` under one built-in? LLVM's answer is that a global *is* a `ptr`.
> 6. **Names.** `ptr` or `address`; the field `form` or `type` (LLVM says type, oymomo
>    says form).

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: `$after`

- A.
- Tests:
  - `reduction`: `$after {[01], [02]}` is not a redex; normalizing the `hi` program keeps
    the first `putchar`, and normalizing it without `$after` drops it (why the step
    exists).
  - `banf_shape`: a field of `$after` that reduces (`{a = q}.a`) is reduced to `q`.
  - `banf_translate`: `hi` gives two `putchar` lets in order, the second on
    `[69000000]:i32`; `$after` inline in an op argument, as a jump argument, as a
    branch condition and as a return; `let c = $after {...}` makes `c` an alias, and a
    later let still resolves to the right name; labels in `$after` are ignored;
    `$after {x}` is `$after needs a value and at least one field to wait for.`; a field
    that isn't an atom is `$after: every field must be an atom.`
  - `llvm_translate`: `hi`'s IR has both calls, in order, and no trace of `$after`.
  - confluence: `hi` gives the same BANF from `t` and from `normalize(t)`.
  - golden `after.oymo`: `hi`, and a loop that calls `putchar` once per iteration and
    ties the call to the counter with `$after`.
- `docs/notes.md`: a row for `after` in Built-ins (no rule, no opcode, dropped by
  `convert`); `$after` in Translation › oymomo → BANF and in Operands must be atoms;
  the messages in Error messages › Built-ins.

Commit: `oymomo: add $after`

### Step 2: the `'ptr'` form, `'alloca'` and `'getelementptr'`

- B.
- Tests:
  - `reduction`: `'alloca' {'i32'}` is not a redex.
  - `banf_shape`: a `form` that reduces (`{f = 'i32'}.f`) is reduced to `'i32'` and
    not let-bound.
  - `banf_translate`: `'alloca'` without `form`, or with a form that isn't a literal,
    is an error; `'getelementptr'` with a run-time index into a struct is an error;
    fields out of order are an error.
  - `llvm_translate`: a function with a `'ptr'` param that returns it is
    `define ptr @"g"(ptr %"h")`; `'alloca' {'i32'}` is `alloca i32`; with
    `count` it is `alloca i32, i64 16`; a struct form is `alloca {i32, i64}`; the
    struct `'getelementptr'` of the goal; a byte offset is `getelementptr i8`; a
    pointer passed from `entry` to a loop block is a phi of `ptr`; an import with a
    `'ptr'` param and result.
  - `banf_terms`: a `'ptr'` literal is `A pointer can't be a literal.`
  - golden `pointer.oymo`: an `alloca` of a struct, a field address passed to a call.
- `docs/notes.md`: `'ptr'` in the BANF to LLVM table; Overview's Type/Form/Layout
  table gets a pointer row; the memory entries in opcodes (impure, form params);
  the form field in Operands must be atoms; the messages in Error messages.

Commit: `oymomo: add the ptr form`

### Step 3: `'load'` and `'store'`

- C.
- Tests:
  - `reduction`: a store then a load stay stuck (decision 13).
  - `banf_translate`: the goal program gives its BANF, with the load after the store
    (without `$after`: step 4);
    `'store' {v}` is `'store' takes 2 fields, got 1.`;
    `'load' {'i32', args.n}` with `n: 'i32'` is
    `'load' expects ptr: ptr, got i32.`; returning a store's result is
    `'s' is the result of a store; only $after can use it.`
  - `llvm_translate`: the goal program's IR; a store then a load of each integer
    form, of `'ptr'` and of a struct form through LLVM's JIT gives the stored value;
    the goal with `[29000000]: 'i32'` for `args.n` is `ret i32 42` after LLVM's `-O2`
    pipeline.
  - golden `memory.oymo`: the goal example, and a loop that sums into an `alloca`,
    chained with `$after`.
- `docs/notes.md`: memory symbols and `$after` in Translation; byte order,
  alignment and layout in Design decisions (decision 12).

Commit: `oymomo: add load and store`

### Step 4: effects without `$after`

No code change. Memory ops are stuck (decision 13), but the let around them is not:
`let x = e in body` is `(x -> body) e`, a β-redex whatever `e` is. These tests pin
down the three things full β does to effects that `$after` doesn't chain (decision
4), so a later change to the kernel or to `banf_shape` that alters them fails a test.
Each case is checked on `normalize(t)` in `reduction`, and on `convert(t)` in
`banf_translate`, which gives the same BANF as `convert(normalize(t))` (confluence).

- Tests:
  - **Unused effects disappear.**
    `let s = 'store' {args.n, p} in 'load' {'i32', p}`:
    - `reduction`: normalizes to `'load' {'i32', p}`; no `'store'` is left,
      since nothing uses `s`.
    - `banf_translate`: the block is `p = alloca i32`, `v = load i32, p`, with no
      `store`.
    - The same program with `$after {p, s}` as the load's pointer keeps the store (the
      goal program).
  - **Effects get copied.**
    `let v = 'load' {'i32', p} in let s = 'store' {args.n, p} in
    'add' {'i32', $after {v, s}, v}`, one load written before the store:
    - `reduction`: the normal form has two `'load' {'i32', p}` subterms.
    - `banf_translate`: the block is `load`, `store`, `load`, `add`: one load on each
      side of the store.
    - `llvm_translate`: with `p` first stored `[01000000]: 'i32'`, `bump(41)` under
      LLVM's JIT is `42` (`41 + 1`), not `2` (`1 + 1`), what the source order says.
  - **The order is lost.**
    `let s = 'store' {args.n, p} in let v = 'load' {'i32', p}
    in $after {v, s}`, the store written before the load, and both kept:
    - `reduction`: the normal form is `$after {'load' {...}, 'store' {...}}`; no let is
      left.
    - `banf_translate`: the block is `load` then `store`: `banf_shape` lets the fields
      of `$after` in field order, so the load comes first, the reverse of the source.
    - The same program with `ptr = $after {p, s}` in the load gives `store` then
      `load`.
- `docs/notes.md`: under `$after` in Built-ins, the three cases, one line each, with
  a link to these tests.

Commit: `oymomo: test unordered effects`

### Step 5: tagged pairs for arrays, vectors and packed structs

- D.
- Tests:
  - `reduction`: none needed: a tagged pair is a struct. One test that β builds one:
    `(e -> {'array', {element = e, count = ...}}) 'i8'` normalizes to
    `{'array', {element = 'i8', ...}}`.
  - `banf_translate`: each tagged pair as a block param's form, a function param's
    form and a memory op's `form`; nested (an array of packed structs, a struct
    holding an array); `{'i32', {x = 'i8'}}` stays a plain struct; every message of
    decision 8: a reserved tag with labeled or extra fields, missing or extra parts,
    a count that isn't a literal, a vector of a struct, a scalable vector inside a
    struct or an array.
  - `banf_terms`: `show_form` prints `[3 x i32]`, `<4 x i32>`, `<vscale x 4 x i32>`,
    `<{i8, i32}>`.
  - `llvm_translate`: `llvm_type` gives `[3 x i32]`, `<4 x i32>`, `<{i8, i32}>`;
    `'getelementptr'` into an array with a run-time index; through LLVM's JIT, a
    store then a load of an array and of a packed struct gives the stored value, and
    a `{'packed', {a = 'i8', b = 'i32'}}` alloca is 5 bytes (`'getelementptr'` to
    field `b` is offset 1); a scalable vector is
    `Form <vscale x 4 x i32> has no LLVM type in llvmlite.`
  - golden `aggregate.oymo`: a function that sums an array of `'i32'` in memory with
    a loop and a run-time `'getelementptr'` index.
- `docs/notes.md`: tagged pairs in Forms are terms (a row each) and in the BANF to
  LLVM table; the reserved tags; the messages in Error messages.
- Status of this plan: **implemented**.

Commit: `oymomo: add aggregate forms`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: the goal program's LLVM IR runs under `llvmlite`'s JIT and `bump(41)`
returns 42; with a literal 41, the goal keeps its three memory lets in BANF and is
`ret i32 42` after LLVM's optimizer; the `hi` program of step 1 gives the same BANF
from `t` and from `normalize(t)`, with both `putchar` calls, in order.
