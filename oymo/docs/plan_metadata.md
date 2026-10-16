# Plan: metadata as in LLVM: a separate table, referred to by index

Status: **proposed**, with open questions; 0 of 6 steps.

## Steps

One commit each.

- [ ] 1. The metadata table: `!n = ...` lines after the code, in LLVM's syntax (`oymomo: add metadata table`)
- [ ] 2. Attachments: `e !dbg !4`, a new term `Attached` (`oymomo: add attachments`)
- [ ] 3. Reduction and BANF keep attachments (`oymomo: keep attachments`)
- [ ] 4. `llvm_translate` writes the table and the attachments (`oymomo: emit metadata`)
- [ ] 5. `meta_build.py`: helpers that build common nodes (`oymomo: add metadata helpers`)
- [ ] 6. `c_import` origins and debug types from a ctype (`oymomo: c_import metadata`)

## Goal

**Metadata works, and reads, as in LLVM.** It lives in a table **separate from the
code**; code refers to a node by its index, `!4`; nodes refer to each other the same
way. So an oymomo program carries everything a full LLVM file needs besides code
(provenance, source locations, debug info, module flags), and `llvm_translate` writes
the file clang would write.

```
module~{
  puts = {s = 'ptr'} => 'i32' !origin !1,
  main = => 'i32' !dbg !3,
} -> {
  main = f -> {
    entry = args~{} ->
      let r = module.puts {s = module.msg} !dbg !4 in
      [00000000]~'i32' !dbg !6,
  },
  ...
}

source_filename = 'main.anv'
!0 = distinct !DICompileUnit(language: DW_LANG_C11, file: !2, producer: 'anvil 0.1')
!1 = !{'stdio.h', i32 690}
!2 = !DIFile(filename: 'main.anv', directory: '/src')
!3 = distinct !DISubprogram(name: 'main', file: !2, line: 3, unit: !0)
!4 = !DILocation(line: 5, column: 7, scope: !3)
!5 = !{i32 2, 'Debug Info Version', i32 3}
!6 = !DILocation(line: 6, column: 3, scope: !3)
!llvm.dbg.cu = !{!0}
!llvm.module.flags = !{!5}
```

gives

```llvm
source_filename = "main.anv"
declare i32 @puts(ptr) !origin !1
define i32 @main() !dbg !3 {
entry:
  %r = call i32 @puts(ptr @msg), !dbg !4
  ret i32 0, !dbg !6
}
!0 = distinct !DICompileUnit(language: DW_LANG_C11, file: !2, producer: "anvil 0.1")
...
```

What it does not do: **oymomo never reads metadata.** A program with every attachment
removed gives the same code; reduction sees only indexes; only `llvm_translate`
looks into the table.

Why not an `#include` in oymomo instead: oymomo is a generated IR and must mean the same
thing on every machine, with no header search paths or libclang
([plan_c_interop.md › Phase 5](plan_c_interop.md#phase-5--c-headers-to-oymomo-declarations)).
A header's name is kept as metadata: it says where a declaration came from, not what
it is.

## Syntax

### The table: LLVM's metadata syntax

After the code, one entry per line, written as LLVM writes metadata, with oymomo's text
literals:

```
!2 = !DIFile(filename: 'main.anv', directory: '/src')     specialized node
!3 = distinct !DISubprogram(name: 'main', file: !2, ...)  distinct node
!5 = !{i32 2, 'Debug Info Version', i32 3}               generic tuple
!llvm.dbg.cu = !{!0}                                      named metadata
source_filename = 'main.anv'                              module property
```

| Value | Example | LLVM |
|---|---|---|
| string | `'main.anv'` | `"main.anv"`, `!"main.anv"` in a tuple |
| integer field | `line: 3` | `line: 3` |
| typed integer, in a tuple | `i32 2` | `i32 2` |
| enum token | `DW_LANG_C11`, `DIFlagPrototyped` | same |
| reference | `!2` | `!2` |
| null | `null` | `null` |

- Only metadata uses decimal integers and bare type names: the code still has only byte
  arrays and forms.
- Indexes are unique, not necessarily dense, and may be used before their line.
- `distinct` is written, as in LLVM; nothing is inferred.
- A program with no table is today's program, unchanged.

### Attachments: `e !kind !n`

Postfix, as LLVM writes `, !dbg !4` after an instruction. Several may follow each
other: `e !dbg !4 !origin !1`. The kind is a name (`dbg`, `origin`, `tbaa`); `!n` must
be in the table.

| Where | Example | LLVM |
|---|---|---|
| a declaration in `module`'s form | `puts = {s = 'ptr'} => 'i32' !origin !1` | `declare i32 @puts(ptr) !origin !1` |
| a defined function's declaration | `main = => 'i32' !dbg !3` | `define i32 @main() !dbg !3` |
| a let's value | `let r = module.puts {...} !dbg !4 in` | `%r = call ..., !dbg !4` |
| a terminator | `[00000000]~'i32' !dbg !6`, `f.done {} !dbg !7` | `ret i32 0, !dbg !6`, `br label %done, !dbg !7` |

**Precedence:** a new level between apply and `->`/`if`/`let`. So an attachment covers a
whole application, and the body of a lambda or a `let` extends over it:

| Level | Syntax | Associativity |
|---|---|---|
| 5 | apply `f a` | left |
| **5½** | **attach `e !kind !n`** | **postfix, repeatable** |
| 6 | `x -> body`, `if`, `let` | extend as far right as possible |

| Source | Means |
|---|---|
| `f a b !dbg !4` | `(f a b) !dbg !4` |
| `{s = 'ptr'} => 'i32' !origin !1` | `({s = 'ptr'} => 'i32') !origin !1` |
| `let r = g x !dbg !4 in r` | `let r = (g x !dbg !4) in r` |
| `x -> f x !dbg !4` | `x -> ((f x) !dbg !4)` |
| `(f a !dbg !4) b` | parentheses needed to apply further |

Tokens: `!` followed by digits is a reference; `!` followed by a name is an attachment
kind in code, or named metadata at the start of a table line. `!` has no other use in
oymomo.

## Decisions

1. **A program is code plus a table.** `terms.Program(code, meta)`: `code` is today's
   `module~{...} -> {...}`; `meta` holds numbered nodes, named metadata and module
   properties. `translate` also takes a bare term, as a program with an empty table.

2. **A reference is a term only inside an attachment**: `terms.Attached(term,
   attachments)`, `attachments` a tuple of `(kind, index)`. There is no free-standing
   `!n` in code, so no term can compute a reference, and reduction never needs a rule
   for one.

3. **An attachment sticks to its term's result.** Reduction keeps it:
   - **Not a blocker.** `unblock` reduces through it: `(f !dbg !4) x` reduces as `f x`.
   - **A redex keeps it on its result.** `(x -> g x) y !dbg !4` gives `g y !dbg !4`;
     an opcode folded to a literal keeps its call's attachments.
   - **Inside a folded operand, it goes**: `'add' {'i32', [01] !dbg !4, [02]}` folds to
     `[03]~'i32'`; the operand has no instruction left to carry it.
   - **Substitution copies it** with the term, so code inlined by reduction keeps its
     location, as LLVM keeps `!dbg` on inlined instructions. It copies an index, never
     a node.
   - **On a literal in tail position it stays**, so `ret` gets its `!dbg`.

4. **`convert` puts attachments where LLVM wants them**: a declaration's on the BANF
   symbol, a let value's on the let, a terminator's on the terminator. Anywhere else
   (an operand, a field of a call's argument) it drops them. BANF carries the table
   unchanged and prints attachments after what they're on
   (`t0 = icmp_eq 'i32', n, 0, !dbg !4`). BANF still doesn't depend on LLVM
   ([notes.md › BANF does not depend on LLVM](notes.md#banf-does-not-depend-on-llvm)):
   it never looks into a node.

5. **`llvm_translate` writes nodes as they are, interpreting nothing**: a specialized
   node with `add_debug_info`, a tuple with `add_metadata`, named metadata with
   `add_named_metadata`, an attachment with `set_metadata`. Whether a node makes sense
   (a `DILocation` needs a `scope`) is LLVM's verifier's business, not oymomo's
   ([notes.md › no checks](notes.md#a-generated-ir-no-checks-for-user-mistakes)).
   oymomo checks only what it needs to go on: every reference has a line.

6. **Generators fill the table**, helped by `meta_build.py` (step 5): `file(...)`,
   `subprogram(...)`, `location(...)`, `compile_unit(...)`, each adding a node and
   returning its index, reusing an equal node instead of adding a copy. `c_import`
   gives each `CDecl` an `origin`; a generator turns it into a node.

## Implementation steps

### 1. The metadata table

`terms.Program`; a table grammar for the lines above; the printer. `translate` takes a
`Program`. Tests: parse and print round trip; a program without a table is unchanged.

### 2. Attachments

`terms.Attached`; the postfix syntax at level 5½; the printer. Tests: the precedence
examples above; an unknown index is an error with its location.

### 3. Reduction and BANF keep attachments

Decision 3 in `reduction` and `banf_shape`; decision 4 in `convert` and BANF. Tests in
`banf_shape_test.py` and `banf_translate_test.py`: an attachment survives beta and
substitution, a folded opcode keeps its call's, a returned literal keeps its own, and a
program with every attachment removed gives the same BANF otherwise.

### 4. Emit metadata

`llvm_translate` writes every node, named entry, module property and attachment.
Tests: golden LLVM IR; the output passes `llvm-as` and `opt -passes=verify`; on the
host, `gdb` or `lldb` breaks on a source line of a small program (plan_c_interop
Phase 2 gives binaries).

### 5. `meta_build.py`

Helpers for the nodes every generator needs: compile unit with module flags, file,
subprogram, location, basic and composite types.

### 6. `c_import` metadata

`CDecl(form, ctype, origin)`. A helper maps a ctype to debug type nodes
(`DIBasicType`, `DIDerivedType`, `DICompositeType`): exact for C declarations
(`unsigned`, `const`, typedef names).

## Open questions

1. Is `'text'` right for metadata strings, or should the table use LLVM's `"text"`,
   so a table line is exactly LLVM's? In oymomo code, `"a b"` is a quoted name.
2. Does llvmlite's `ir` API allow every attachment needed (on function declarations and
   globals), or does `llvm_translate` write some metadata as text?
3. Locals: is a location enough, or do `alloca`s need `#dbg_declare` records from the
   start, which reference a `DILocalVariable` node?
4. Should a node be checked for well-formedness before LLVM sees it, for a better
   error message, or is LLVM's verifier enough?
