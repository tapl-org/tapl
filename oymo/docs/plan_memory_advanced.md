# Plan: advanced memory: `noalias`, more ops, alignment and byte order

Status: **proposed**, with open questions; 0 of 7 steps.

## Steps

One commit each, each landing when a program needs it. Details are in
[Implementation steps](#implementation-steps).

- [ ] 1. Comparing pointers, and a null pointer: `'icmp_eq'` and friends on `'ptr'`, `'null' {}` (`oymomo: compare pointers`)
- [ ] 2. `'ptrtoint'` and `'inttoptr'` (`oymomo: add pointer casts`)
- [ ] 3. `'memcpy'`, `'memmove'`, `'memset'` (`oymomo: add bulk memory ops`)
- [ ] 4. An optional `align` field on `'load'`, `'store'`, `'alloca'` and `'global'` (`oymomo: add align`)
- [ ] 5. `noalias` on params and results: the tagged form `{'noalias', 'ptr'}` (`oymomo: add noalias`)
- [ ] 6. `'bswap'`, for byte order per access (`oymomo: add bswap`)
- [ ] 7. Scoped aliasing metadata (`!alias.scope`, `!noalias`), if step 5 isn't enough (`oymomo: add alias scopes`)

[plan_memory.md](implemented/plan_memory.md) stops at what a program needs to read
and write memory, with LLVM's defaults: no `noalias`, no `align`, the target's byte
order, LLVM's struct layout (its decisions 10 and 12). This plan designs the rest
once, so each part lands when a program needs it, in any order: no step depends on
another, except that step 7 is only worth doing after step 5. No step is breaking:
each adds an opcode, a field after the existing ones, or a tag.

## Goal

**A program can tell LLVM what it knows about memory, and LLVM uses it.** Each part
has a program whose speed or correctness needs it:

| Part | The program that needs it |
|---|---|
| Comparing pointers, null | A linked list: walk `next` until it is null. Without it, a list needs a separate length or a sentinel cell. |
| `'ptrtoint'`, `'inttoptr'` | A hash table keyed by address, or an allocator that rounds an address up to 16 bytes. |
| `'memcpy'` and friends | Copying a 4 KiB buffer: one `memcpy` that LLVM lowers to `rep movsb` or vector stores, instead of a loop it may or may not recognize. |
| `align` | Vector code over a 32-byte aligned buffer (`load <8 x i32>, align 32`), and reading a packed or unaligned network header without undefined behaviour. |
| `noalias` | `dst[i] = src[i] * 2` over two `'ptr'` params, vectorized with no run-time overlap check. |
| `'bswap'` | Reading a big-endian file format or network protocol on x86. |
| Alias scopes | Two pointers loaded from a struct that the program knows never overlap. |

---

## Aliasing

### What `noalias` promises

`noalias` on a param says: during the call, memory reached through this pointer is
reached through no other pointer that the function uses. It is C's `restrict` and
what Rust emits for `&mut T`. LLVM may assume it, and **breaking it is undefined
behaviour, which nothing checks**: the call is simply miscompiled. That is why
[plan_memory.md](implemented/plan_memory.md) decision 10 emits none, and why this
plan adds it only as something a program writes by hand.

### What LLVM does without it

Measured with llvmlite 0.49 (LLVM 22) and its `-O2` pipeline
(`create_pass_builder(..., speed_level=2)`):

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

And the loop, `dst[i] = src[i] * 2` for `i` below `n`, over `ptr %dst, ptr %src`:

| Params | After `-O2` |
|---|---|
| plain `ptr` | vectorized (`<4 x i32>`), behind a run-time overlap check (`vector.memcheck`), with the scalar loop kept for when they overlap |
| `ptr noalias` | vectorized, no overlap check |

So `noalias` buys little where LLVM can already tell: an `alloca`, a `'global'` (two
globals are distinct), a value that never escapes. It matters where LLVM can't:

- `'ptr'` params of a defined function, as above;
- the result of an import, such as `malloc`: LLVM knows `malloc`'s by name, but not
  a program's own allocator's;
- pointers loaded from memory (`'load' {'ptr', p}`), such as two fields of a struct.

### Options

1. **A param marker: the tagged form `{'noalias', 'ptr'}`.** Allowed as the form of
   an entry block's param, of an import's param, and of an import's or a definition's
   result (`malloc = {size = 'i64'} => {'noalias', 'ptr'}`). Everywhere else, and to
   every rule but LLVM's attribute, it counts as `'ptr'`: `atom_form` gives `'ptr'`,
   and a jump may pass it to a `'ptr'` block param. LLVM: `ptr noalias %dst`,
   `noalias ptr @malloc(...)`. Like the tags of plan_memory.md decision 8, only BANF
   and LLVM read it, and `'noalias'` becomes a reserved tag.
2. **Scoped metadata on each access** (`!alias.scope`, `!noalias`): says two
   specific accesses don't alias, anywhere, loaded pointers included. Each access
   names a scope, so a program needs a way to name scopes: a new field on `'load'`
   and `'store'`, and a new module-level declaration of the scopes. More power, much
   more surface.
3. **A `noalias` field on `'load'`/`'store'`.** Rejected: LLVM has no per-access
   `noalias` flag; it would have to be compiled to option 2's scopes anyway.
4. **Infer it.** Rejected: whether two pointers alias is the question LLVM's own
   analysis already answers as well as it can; anything more is a promise only the
   program can make.

**Recommended: option 1 now (step 5), option 2 only for a program that needs it
(step 7).** Option 1 covers the loop and `malloc`, the two cases measured above, with
one tag and no new syntax.

---

## More ops

Each is an entry of the opcode table, with `form_of`, `evaluate` (a fold, if any)
and an LLVM lowering, as plan_memory.md decision 7 does for the first four.

### Comparing pointers (step 1)

`'icmp_eq' {'ptr', p, q}`, and the other nine predicates, as on `iN`
([plan_vm.md](plan_vm.md)). LLVM's `icmp` takes `ptr` operands as it takes
integers. Today `_binary` already accepts any byte array as `form`, and `evaluate`
gives nothing for a non-integer form, so this is only the LLVM lowering, which reads
`form` as an integer form today. The ordered predicates (`icmp_ult`, ...) compare
addresses; LLVM defines them, and the result means something only within one object.

### A null pointer (step 1)

| Option | Written | Notes |
|---|---|---|
| a `'null'` opcode | `'null' {}` | gives `'ptr'`; pure; LLVM `ptr null`. Needs no target width |
| a literal exception | `[0000000000000000]~'ptr'` | breaks decision 6, and the width is the target's pointer width, which BANF doesn't know |
| a cast | `'inttoptr' {'i64', [0000000000000000]~'i64', 'ptr'}` | needs step 2; LLVM folds it to `null`, but it reads as a trick |

**Recommended: `'null' {}`.** What reduction may fold: `'icmp_eq' {'ptr', n, n}`
with both `'null' {}` could fold to `[01]~'i1'`, but nothing else about pointers
can, so `evaluate` stays empty, and LLVM folds it. An open question.

### `'ptrtoint'` and `'inttoptr'` (step 2)

Conversions, in the shape of `'zext'`: `'ptrtoint' {'ptr', p, 'i64'}` and
`'inttoptr' {'i64', n, 'ptr'}`, as LLVM writes `ptrtoint ptr %p to i64`.

- **Which integer form:** any, as in LLVM, which truncates or zero-extends to the
  pointer width of the data layout. BANF doesn't know the target, so it can't insist
  on the pointer width; `'i64'` is right on every 64-bit target. A program that needs
  the width could read it from the target, an open question shared with byte order.
- **Provenance:** LLVM's rules apply: a pointer made by `'inttoptr'` may only be used
  to reach the object whose address the integer came from. Rounding an address up
  within its object is fine; making up an address is undefined. Nothing checks it.
- Pure, with no fold: no pointer is a literal.

### `'memcpy'`, `'memmove'`, `'memset'` (step 3)

LLVM's intrinsics, in their operand order:

| Opcode | Fields | LLVM |
|---|---|---|
| `'memcpy'` | `{dst, src, len}` | `call void @llvm.memcpy.p0.p0.iN(ptr dst, ptr src, iN len, i1 false)` |
| `'memmove'` | `{dst, src, len}` | `@llvm.memmove...`, overlapping allowed |
| `'memset'` | `{dst, byte, len}` | `@llvm.memset.p0.iN(ptr dst, i8 byte, iN len, i1 false)` |

- `len` brings its own form, any integer form, which picks the intrinsic's `iN`.
- `memcpy`'s regions must not overlap: undefined otherwise, unchecked.
- Impure; the result is `{}`, which only `$seq` may use, as a `'store'`'s
  (plan_memory.md decision 11).
- **The `volatile` flag:** LLVM's last operand. Left `false`, with no field, until
  volatile loads and stores exist (memory-mapped I/O); then one `volatile` field for
  all of them, an open question.
- llvmlite declares the intrinsic by its mangled name, as an ordinary function.

---

## Alignment, byte order and layout

### `align` (step 4)

LLVM's `align N` on `load`, `store`, `alloca` and a global. Without it, LLVM assumes
the type's ABI alignment (plan_memory.md decision 12). With it:

- **below** ABI alignment: an access to packed or unaligned data, such as a field of a
  packed struct (decision 8) or a network header at an odd offset. Without it, such an
  access is undefined behaviour, and on some targets traps.
- **above** it: a promise LLVM uses for wide vector accesses, and a request on an
  `alloca` or a global (a 64-byte aligned buffer).

A wrong `align`, larger than the address really has, is undefined behaviour,
unchecked.

**How it fits positional fields.** LLVM writes `align` last
(`load i32, ptr %p, align 4`), so it is one more field, last, a literal integer,
read unsigned, a power of two:

| Opcode | Fields |
|---|---|
| `'load'` | `{form, ptr}`, `{form, ptr, align}` |
| `'store'` | `{value, ptr}`, `{value, ptr, align}` |
| `'alloca'` | `{form}`, `{form, count}`, `{form, count, align}`: `count` must be written to give `align` |
| `'global'` | `{form}`, `{form, init}`, `{form, init, align}`: `init` must be written, zeros if need be |

Rejected: a field labelled `align` (labels are ignored everywhere else, plan_vm.md
decision 7); separate opcodes (`'load_aligned'`), which double the table.

### Byte order (step 6)

Memory uses the target's byte order (decision 12). A portable format needs a fixed
one per access, as Cranelift's `little`/`big` flags give. LLVM has no such flag: a
big-endian read on a little-endian target is a load and `llvm.bswap`.

- **The op:** `'bswap' {'i32', x}`, LLVM's intrinsic, pure, and folded by reduction
  like every pure opcode (reverse the bytes). Useful on its own.
- **Big-endian access** then needs to know whether the target is big-endian, which
  oymomo doesn't. Options: a library function that takes the target's byte order as a
  module-level value; or opcodes `'load_be'` and `'load_le'` that BANF lowers knowing
  the target's data layout. An open question; the recommendation is the op first, and
  the library once a format needs it.

### Struct layout

A struct's padding and field offsets are LLVM's for the target (decision 12). A
program that needs an exact layout writes a packed struct (decision 8) with explicit
padding, `{'packed', a = 'i8', pad = {'array', [03000000]~'i32', 'i8'}, b = 'i32'}`,
and an over-aligned one with `align` on its `alloca` or `'global'`. **Recommended: no
layout feature beyond these.** C interop needs the target's C layout, which is LLVM's
for a literal struct; that is [plan_c_interop.md](plan_c_interop.md)'s concern.

---

## Open questions

1. Should `'icmp_eq'` of two `'null' {}` fold in reduction, or is `'null'` never
   folded, as no other pointer is?
2. How does a program learn the target's pointer width and byte order: a module-level
   value, a form (`'iptr'`), or not at all?
3. One `volatile` field for `'load'`, `'store'` and the bulk ops, or `volatile`
   variants? Not needed until memory-mapped I/O.
4. Is `{'noalias', 'ptr'}` allowed on a block param other than the entry block's? LLVM
   has no such attribute there; the recommendation is no.
5. For alias scopes (step 7): are scopes declared in `module`, or written inline on
   each access?

---

## Implementation steps

Each step is one commit, leaves `hatch run full-check` green, and updates
`docs/notes.md` for its part. Each adds tests at every stage it touches, and a golden
for its goal program.

### Step 1: comparing pointers, and null

- `llvm_opcodes.py`: the `icmp_*` lowering accepts `'ptr'` as its form.
- `opcodes.py`: `'null'`, `{}` giving `'ptr'`, pure, no fold; `llvm`: `ir.Constant(ptr, None)`.
- Goal program: the length of a linked list, `next` loaded until `'icmp_eq'` with `'null' {}`.

### Step 2: `'ptrtoint'` and `'inttoptr'`

- `opcodes.py`: two conversions `{form, value, to}`, pure, no fold.
- Goal program: round an address up to 16 bytes within an `alloca` of 32 bytes.

### Step 3: `'memcpy'`, `'memmove'`, `'memset'`

- `opcodes.py`: three impure entries giving `{}`; the BANF verifier's store-result rule
  covers them.
- `llvm_opcodes.py`: declare `llvm.memcpy.p0.p0.iN` and friends by name, call them with
  `i1 false`.
- Goal program: copy an array of 1024 `'i32'`; under `-O2`, one `memcpy` call remains.

### Step 4: `align`

- `opcodes.py`, `banf_terms.py`, `llvm_opcodes.py`, `llvm_translate.py`: the optional
  last field, a power of two; `load.align`, `store.align`, `alloca(..., align)`,
  `GlobalVariable.align`.
- Goal program: an unaligned `'i32'` read from a packed struct, with `align 1`.

### Step 5: `noalias`

- `opcodes.py`: `'noalias'` in the tags; `banf_translate.py`: allowed only on entry
  block params and signature params and results; elsewhere an error.
- `banf_terms.py`: `atom_form` and the verifier read it as `'ptr'`.
- `llvm_translate.py`: the `noalias` attribute on the argument or the return.
- Goal program: the loop of [What LLVM does without it](#what-llvm-does-without-it);
  a test checks that `-O2` leaves no `vector.memcheck`.

### Step 6: `'bswap'`

- `opcodes.py`: pure, folds; `llvm_opcodes.py`: `llvm.bswap.iN`.
- Goal program: read a big-endian `'i32'` header field on a little-endian target.

### Step 7: alias scopes

Designed when a program needs it; see open question 5.

---

## Verification

After every step:

```
hatch run full-check
```
