# Plan: advanced memory: `noalias`, more ops, alignment and byte order

**Status:** proposed, with open questions · 0 of 7 steps · no breaking changes
· follows [plan_memory.md](implemented/plan_memory.md)

## Goal

- **A program can tell LLVM what it knows about memory, and LLVM uses it.**
- Each part lands when a program needs it, in any order.
- [plan_memory.md](implemented/plan_memory.md) stops at LLVM's defaults (its decisions
  10 and 12); this plan designs the rest once.

| Part | The program that needs it |
|---|---|
| Comparing pointers, null | A linked list: walk `next` until null (no separate length or sentinel) |
| `'ptrtoint'`, `'inttoptr'` | A hash table keyed by address; an allocator rounding up to 16 bytes |
| `'memcpy'` and friends | Copying a 4 KiB buffer as one `memcpy` (`rep movsb` or vector stores) |
| `align` | Vector code over a 32-byte aligned buffer; an unaligned network header without UB |
| `noalias` | `dst[i] = src[i] * 2` over two `'ptr'` params, vectorized with no overlap check |
| `'bswap'` | Reading a big-endian file format or protocol on x86 |
| Alias scopes | Two pointers loaded from a struct that never overlap |

## Steps

One commit each; each leaves `hatch run full-check` green, updates `docs/notes.md`, and
adds tests and a golden for its goal program. No step depends on another, except that
step 7 is only worth doing after step 5.

- [ ] 1. Comparing pointers, and a null pointer: `'icmp_eq'` and friends on `'ptr'`, `'null' {}` (`oymomo: compare pointers`)
- [ ] 2. `'ptrtoint'` and `'inttoptr'` (`oymomo: add pointer casts`)
- [ ] 3. `'memcpy'`, `'memmove'`, `'memset'` (`oymomo: add bulk memory ops`)
- [ ] 4. An optional `align` field on `'load'`, `'store'`, `'alloca'` and `'global'` (`oymomo: add align`)
- [ ] 5. `noalias` on params and results: the tagged form `{'noalias', 'ptr'}` (`oymomo: add noalias`)
- [ ] 6. `'bswap'`, for byte order per access (`oymomo: add bswap`)
- [ ] 7. Scoped aliasing metadata (`!alias.scope`, `!noalias`), if step 5 isn't enough (`oymomo: add alias scopes`)

## Proposal

### Aliasing (steps 5, 7)

- **Step 5: the tagged form `{'noalias', 'ptr'}`** (option 1 below).
  - Allowed on: an entry block's param, an import's param, an import's or definition's
    result (`malloc = {size = 'i64'} => {'noalias', 'ptr'}`).
  - Everywhere else it counts as `'ptr'` (`atom_form` gives `'ptr'`; a jump may pass it
    to a `'ptr'` param).
  - LLVM: `ptr noalias %dst`, `noalias ptr @malloc(...)`.
  - Only BANF and LLVM read it; `'noalias'` becomes a reserved tag.
  - Breaking the promise is **undefined behaviour, unchecked**; written only by hand.
- **Step 7: scoped metadata**, only for a program that needs it (open question 5).

### More ops (steps 1–3)

Each is an opcode table entry with `form_of`, `evaluate` (fold, if any) and an LLVM
lowering, as plan_memory decision 7.

- **Comparing pointers:** `'icmp_eq' {'ptr', p, q}` and the other nine predicates, as
  on `iN`. Only the LLVM lowering changes. Ordered predicates compare addresses;
  meaningful only within one object.
- **Null:** `'null' {}`, gives `'ptr'`, pure, LLVM `ptr null`, needs no target width.
  No fold (open question 1).
- **Casts:** `'ptrtoint' {'ptr', p, 'i64'}`, `'inttoptr' {'i64', n, 'ptr'}`, shaped
  like `'zext'`.
  - Any integer form, as in LLVM (truncates or zero-extends); `'i64'` fits every
    64-bit target.
  - LLVM's provenance rules: an `'inttoptr'` pointer may only reach the object its
    integer came from. Unchecked.
  - Pure, no fold.
- **Bulk ops**, LLVM's intrinsics in their operand order:

  | Opcode | Fields | LLVM |
  |---|---|---|
  | `'memcpy'` | `{dst, src, len}` | `call void @llvm.memcpy.p0.p0.iN(ptr dst, ptr src, iN len, i1 false)` |
  | `'memmove'` | `{dst, src, len}` | `@llvm.memmove...`, overlapping allowed |
  | `'memset'` | `{dst, byte, len}` | `@llvm.memset.p0.iN(ptr dst, i8 byte, iN len, i1 false)` |

  - `len`'s integer form picks `iN`.
  - `memcpy` overlap is undefined, unchecked.
  - Impure; result `{}`, usable only by `$seq` (plan_memory decision 11).
  - `volatile` is `false`, no field (open question 3).

### Alignment, byte order, layout (steps 4, 6)

- **`align`: one more positional field, last**, a literal power of two, read unsigned:

  | Opcode | Fields |
  |---|---|
  | `'load'` | `{form, ptr}`, `{form, ptr, align}` |
  | `'store'` | `{value, ptr}`, `{value, ptr, align}` |
  | `'alloca'` | `{form}`, `{form, count}`, `{form, count, align}`: `count` must be written to give `align` |
  | `'global'` | `{form}`, `{form, init}`, `{form, init, align}`: `init` must be written, zeros if need be |

  - Below ABI alignment: packed or unaligned access. Above: a promise for wide vector
    accesses, or a request on `alloca`/global.
  - A wrong (too large) `align` is undefined behaviour, unchecked.
- **Byte order: `'bswap' {'i32', x}`**, LLVM's intrinsic, pure, folded. Big-endian
  access via a library once a format needs it (open question 2).
- **Struct layout: no new feature.** Stays LLVM's; exact layout = packed struct with
  explicit padding; over-alignment = `align` on `alloca`/`'global'`.

## Implementation steps

| Step | Changes | Goal program |
|---|---|---|
| 1 | `llvm_opcodes.py`: `icmp_*` lowering accepts `'ptr'`. `opcodes.py`: `'null'`, `{}` → `'ptr'`, pure, no fold; LLVM `ir.Constant(ptr, None)` | length of a linked list: load `next` until `'icmp_eq'` with `'null' {}` |
| 2 | `opcodes.py`: two conversions `{form, value, to}`, pure, no fold | round an address up to 16 bytes within a 32-byte `alloca` |
| 3 | `opcodes.py`: three impure entries giving `{}` (the verifier's store-result rule covers them). `llvm_opcodes.py`: declare `llvm.memcpy.p0.p0.iN` and friends by name, call with `i1 false` | copy 1024 `'i32'`; under `-O2` one `memcpy` call remains |
| 4 | `opcodes.py`, `banf_terms.py`, `llvm_opcodes.py`, `llvm_translate.py`: optional last field, power of two; `load.align`, `store.align`, `alloca(..., align)`, `GlobalVariable.align` | unaligned `'i32'` read from a packed struct, `align 1` |
| 5 | `opcodes.py`: `'noalias'` tag. `banf_translate.py`: only on entry block params, signature params and results; elsewhere an error. `banf_terms.py`: `atom_form` and verifier read `'ptr'`. `llvm_translate.py`: `noalias` on argument or return | the loop in [What LLVM does without it](#what-llvm-does-without-it); `-O2` leaves no `vector.memcheck` |
| 6 | `opcodes.py`: pure, folds. `llvm_opcodes.py`: `llvm.bswap.iN` | read a big-endian `'i32'` header field on a little-endian target |
| 7 | designed when a program needs it (open question 5) | — |

## Open questions

1. Should `'icmp_eq'` of two `'null' {}` fold in reduction, or is `'null'` never folded,
   as no other pointer is?
2. How does a program learn the target's pointer width and byte order?
   - a. A module-level value
   - b. A form (`'iptr'`)
   - c. Not at all
3. One `volatile` field for `'load'`, `'store'` and the bulk ops, or `volatile`
   variants? Not needed until memory-mapped I/O.
4. Is `{'noalias', 'ptr'}` allowed on a non-entry block param? Leaning: **no** (LLVM
   has no such attribute there).
5. Alias scopes (step 7): declared in `module`, or written inline on each access?

## Dependencies

- Builds on [plan_memory.md](implemented/plan_memory.md) (decisions 6, 7, 8, 10, 11, 12).
- Step 1 uses the `icmp_*` opcodes of [plan_vm.md](plan_vm.md).
- [plan_c_interop.md](plan_c_interop.md) 1.1 uses steps 1–2; C struct layout is its concern.
- Step 7 only after step 5.

## Background (for agents)

Context kept for reference; not needed to follow the plan.

### What `noalias` promises

During the call, memory reached through this pointer is reached through no other
pointer the function uses. It is C's `restrict` and what Rust emits for `&mut T`. LLVM
may assume it; breaking it miscompiles silently. That is why plan_memory decision 10
emits none, and this plan adds it only by hand.

### What LLVM does without it

Measured with llvmlite 0.49 (LLVM 22), `-O2` (`create_pass_builder(..., speed_level=2)`):

```llvm
define i32 @f(ptr %a, ptr %b) {
  store i32 1, ptr %a
  store i32 2, ptr %b
  %v = load i32, ptr %a
  ret i32 %v
}
```

| `%a` is | After `-O2` |
|---|---|
| a plain `ptr` param | the load stays: `%b` may be `%a` |
| `ptr noalias %a` | `ret i32 1` |
| an `alloca` in `f` | `ret i32 1`: LLVM knows an `alloca` that doesn't escape is reached by no param |

The loop `dst[i] = src[i] * 2` for `i` below `n`, over `ptr %dst, ptr %src`:

| Params | After `-O2` |
|---|---|
| plain `ptr` | vectorized (`<4 x i32>`), behind a run-time overlap check (`vector.memcheck`), scalar loop kept for overlap |
| `ptr noalias` | vectorized, no overlap check |

So `noalias` buys little where LLVM can already tell (an `alloca`, a `'global'` — two
globals are distinct — a value that never escapes). It matters where LLVM can't:

- `'ptr'` params of a defined function;
- the result of an import: LLVM knows `malloc` by name, not a program's own allocator;
- pointers loaded from memory (`'load' {'ptr', p}`), such as two struct fields.

### Aliasing options

1. **Param marker `{'noalias', 'ptr'}`** — chosen for step 5. Like plan_memory decision
   8's tags. Covers the loop and `malloc` with one tag and no new syntax.
2. **Scoped metadata per access** (`!alias.scope`, `!noalias`) — step 7 only if needed.
   Says two specific accesses never alias, loaded pointers included. Needs a new field
   on `'load'`/`'store'` and a module-level scope declaration: more power, much more
   surface.
3. **A `noalias` field on `'load'`/`'store'`** — rejected: LLVM has no per-access flag;
   it would compile to option 2 anyway.
4. **Infer it** — rejected: LLVM's own analysis already answers as well as it can; the
   rest is a promise only the program can make.

### Null pointer options

| Option | Written | Notes |
|---|---|---|
| a `'null'` opcode (chosen) | `'null' {}` | gives `'ptr'`; pure; LLVM `ptr null`. Needs no target width |
| a literal exception | `[0000000000000000]~'ptr'` | breaks decision 6, and the width is the target's pointer width, which BANF doesn't know |
| a cast | `'inttoptr' {'i64', [0000000000000000]~'i64', 'ptr'}` | needs step 2; LLVM folds it to `null`, but it reads as a trick |

`'icmp_eq'` of two `'null' {}` could fold to `[01]~'i1'`, but nothing else about
pointers can, so `evaluate` stays empty and LLVM folds it.

### Notes on the ops

- Comparing pointers: LLVM's `icmp` takes `ptr` like integers. `_binary` already accepts
  any byte array as `form`, and `evaluate` gives nothing for a non-integer form; only
  the LLVM lowering reads `form` as an integer form today. LLVM defines ordered
  pointer predicates.
- Casts: written as LLVM's `ptrtoint ptr %p to i64`. LLVM fits the integer to the data
  layout's pointer width; BANF doesn't know the target, so it can't insist on it
  (open question 2, shared with byte order). Rounding an address up within its object
  is fine; making one up is undefined. No fold: no pointer is a literal.
- Bulk ops: `volatile` is LLVM's last operand; a field comes once volatile loads and
  stores exist (memory-mapped I/O). llvmlite declares the intrinsic by its mangled
  name, as an ordinary function.

### Notes on alignment, byte order, layout

- Without `align`, LLVM assumes the type's ABI alignment (plan_memory decision 12).
  Below-ABI examples: a packed struct field (decision 8), a header at an odd offset;
  without `align` such an access is UB and traps on some targets. Above-ABI example:
  a 64-byte aligned buffer.
- `align` is last because LLVM writes it last (`load i32, ptr %p, align 4`). Rejected:
  a field labelled `align` (labels are ignored everywhere else, plan_vm decision 7);
  separate opcodes (`'load_aligned'`), which double the table.
- Byte order: memory uses the target's (decision 12). Cranelift has per-access
  `little`/`big` flags; LLVM doesn't: big-endian on little-endian is load +
  `llvm.bswap`. `'bswap'` reverses bytes and is useful on its own. Big-endian access
  options: a library function taking the target's byte order as a module-level value,
  or `'load_be'`/`'load_le'` opcodes BANF lowers from the data layout. Recommended: the
  op first, the library once a format needs it.
- Layout example: `{'packed', a = 'i8', pad = {'array', [03000000]~'i32', 'i8'}, b = 'i32'}`.
  C interop needs the target's C layout, which is LLVM's for a literal struct.
- No step is breaking: each adds an opcode, a field after the existing ones, or a tag.
