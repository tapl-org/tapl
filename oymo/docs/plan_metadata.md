# Plan: metadata as in LLVM: a separate table, referred to by index

**Status:** proposed · 0 of 6 steps · steps 1–3 for oymo 0.8, 4 (line tables) for 0.12,
6 for 0.28, 4–5 (full DWARF) for 0.29 · see [roadmap](roadmap.md#stage-a--the-bootstrap-set-in-python)

## Goal

- Metadata lives in a **table separate from the code**, as in LLVM; code and nodes
  refer to a node by index, `!4`.
- An oymomo program carries all a full LLVM file needs besides code: provenance,
  source locations, debug info, module flags.
- `llvm_translate` writes the file clang would write.
- **oymomo never reads metadata**: removing every attachment gives the same code.

## Steps

One commit each.

- [ ] 1. The metadata table: `!n = ...` lines after the code, in LLVM's syntax (`oymomo: add metadata table`)
- [ ] 2. Attachments: `e !dbg !4`, a new term `Attached` (`oymomo: add attachments`)
- [ ] 3. Reduction and BANF keep attachments (`oymomo: keep attachments`)
- [ ] 4. `llvm_translate` writes the table and the attachments (`oymomo: emit metadata`)
- [ ] 5. `meta_build.py`: helpers that build common nodes (`oymomo: add metadata helpers`)
- [ ] 6. `c_import` origins and debug types from a ctype (`oymomo: c_import metadata`)

## Decisions

1. **A program is code plus a table.** `terms.Program(code, meta)`: `code` is today's
   `module~{...} -> {...}`; `meta` holds numbered nodes, named metadata, module
   properties. `translate` also takes a bare term (empty table).
2. **A reference is a term only inside an attachment**: `terms.Attached(term,
   attachments)`, a tuple of `(kind, index)`. No free-standing `!n` in code, so
   nothing computes a reference and reduction needs no rule for one.
3. **An attachment sticks to its term's result** through reduction:
   - Not a blocker: `(f !dbg !4) x` reduces as `f x`.
   - A redex keeps it on its result: `(x -> g x) y !dbg !4` gives `g y !dbg !4`;
     a folded opcode keeps its call's attachments.
   - Inside a folded operand it goes: `'add' {'i32', [01] !dbg !4, [02]}` → `[03]~'i32'`.
   - Substitution copies it (an index, never a node), so inlined code keeps its
     location, as LLVM does.
   - On a literal in tail position it stays, so `ret` gets its `!dbg`.
4. **`convert` puts attachments where LLVM wants them**: a declaration's on the BANF
   symbol, a let value's on the let, a terminator's on the terminator; elsewhere
   (operands, call argument fields) dropped. BANF carries the table unchanged, prints
   attachments after their target (`t0 = icmp_eq 'i32', n, 0, !dbg !4`), and never
   looks into a node.
5. **`llvm_translate` writes nodes as they are, interpreting nothing**:
   `add_debug_info`, `add_metadata`, `add_named_metadata`, `set_metadata`. Whether a
   node makes sense is LLVM's verifier's business. oymomo checks only that every
   reference has a line.
6. **Generators fill the table**, with `meta_build.py` (step 5): `file`,
   `subprogram`, `location`, `compile_unit`, each adds a node (reusing an equal one)
   and returns its index. `c_import` gives each `CDecl` an `origin`.

## Design

### Example

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
!0 = distinct !DICompileUnit(language: DW_LANG_C11, file: !2, producer: 'tenon 0.1')
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
!0 = distinct !DICompileUnit(language: DW_LANG_C11, file: !2, producer: "tenon 0.1")
...
```

### Table syntax (step 1)

One entry per line after the code, LLVM's metadata syntax with oymomo's text literals:

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
| integer field | `line: 3` | same |
| typed integer, in a tuple | `i32 2` | same |
| enum token | `DW_LANG_C11`, `DIFlagPrototyped` | same |
| reference | `!2` | same |
| null | `null` | same |

- Decimal integers and bare type names exist only in metadata.
- Indexes are unique, not necessarily dense, usable before their line.
- `distinct` is written, never inferred.
- A program with no table is unchanged.

### Attachments: `e !kind !n` (step 2)

Postfix and repeatable (`e !dbg !4 !origin !1`). Kind is a name (`dbg`, `origin`,
`tbaa`); `!n` must be in the table.

| Where | Example | LLVM |
|---|---|---|
| declaration in `module`'s form | `puts = {s = 'ptr'} => 'i32' !origin !1` | `declare i32 @puts(ptr) !origin !1` |
| defined function's declaration | `main = => 'i32' !dbg !3` | `define i32 @main() !dbg !3` |
| let value | `let r = module.puts {...} !dbg !4 in` | `%r = call ..., !dbg !4` |
| terminator | `[00000000]~'i32' !dbg !6`, `f.done {} !dbg !7` | `ret i32 0, !dbg !6`, `br label %done, !dbg !7` |

Precedence: new level 5½, between apply (5) and `->`/`if`/`let` (6).

| Source | Means |
|---|---|
| `f a b !dbg !4` | `(f a b) !dbg !4` |
| `{s = 'ptr'} => 'i32' !origin !1` | `({s = 'ptr'} => 'i32') !origin !1` |
| `let r = g x !dbg !4 in r` | `let r = (g x !dbg !4) in r` |
| `x -> f x !dbg !4` | `x -> ((f x) !dbg !4)` |
| `(f a !dbg !4) b` | parentheses needed to apply further |

Tokens: `!` + digits is a reference; `!` + name is a kind in code, or named metadata
at the start of a table line. `!` has no other use.

### Per step

| Step | Change | Tests |
|---|---|---|
| 1 | `terms.Program`, table grammar, printer; `translate` takes a `Program` | round trip; no table → unchanged |
| 2 | `terms.Attached`, postfix syntax, printer | precedence examples; unknown index is an error with location |
| 3 | decision 3 in `reduction`, `banf_shape`; decision 4 in `convert`, BANF | in `banf_shape_test.py`, `banf_translate_test.py`: survives beta and substitution; folded opcode keeps its call's; returned literal keeps its own; stripping attachments gives the same BANF |
| 4 | `llvm_translate` writes nodes, named entries, module properties, attachments | golden IR; passes `llvm-as` and `opt -passes=verify`; `gdb`/`lldb` breaks on a source line (binaries from plan_c_interop Phase 2) |
| 5 | helpers: compile unit with module flags, file, subprogram, location, basic and composite types | |
| 6 | `CDecl(form, ctype, origin)`; ctype → `DIBasicType`/`DIDerivedType`/`DICompositeType`, exact for C (`unsigned`, `const`, typedefs) | |

## Open questions

1. **Metadata strings:** `'text'`, or LLVM's `"text"` so a table line is exactly LLVM's?
   (In oymomo code, `"a b"` is a quoted name.)
2. **llvmlite:** does its `ir` API allow every needed attachment (function
   declarations, globals), or must `llvm_translate` write some metadata as text?
3. **Locals:** is a location enough, or do `alloca`s need `#dbg_declare` records
   (referencing a `DILocalVariable`) from the start?
4. **Node checks:** check well-formedness before LLVM for better errors, or rely on
   LLVM's verifier?

## Dependencies

- [plan_c_interop.md](plan_c_interop.md): Phase 2 (binaries) for the debugger test
  in step 4; `c_import` (Phase 5) for step 6.

## Background (for agents)

Context kept for reference; not needed to follow the plan.

### Rejected options

- **`#include` in oymomo:** oymomo is a generated IR and must mean the same on every
  machine, with no header search paths or libclang
  ([plan_c_interop.md › Phase 5](plan_c_interop.md#phase-5--c-headers-to-oymomo-declarations)).
  A header's name is kept as metadata: where a declaration came from, not what it is.

### Notes on the decisions

- 2–3: reduction sees only indexes; only `llvm_translate` looks into the table.
- 3: a folded operand has no instruction left to carry its attachment.
- 4: BANF still doesn't depend on LLVM
  ([notes.md › BANF does not depend on LLVM](notes.md#banf-does-not-depend-on-llvm)).
- 5: e.g. a `DILocation` needing a `scope` is not checked by oymomo
  ([notes.md › no checks](notes.md#a-generated-ir-no-checks-for-user-mistakes)).
- 6: a generator turns a `CDecl`'s `origin` into a node.
