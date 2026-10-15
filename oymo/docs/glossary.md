# Oymo glossary

Words used across the docs and code, in alphabetical order. Code names are in `code`.
The **More** column links to [notes.md](notes.md).

> **Kernel or reduction?** The *kernel* is the oymomo language as a whole: its terms,
> syntax and rules. *Reduction* is how kernel terms compute, implemented in
> `reduction.py`. So "the kernel folds `'add'`" and "reduction folds `'add'`" say the
> same thing; prefer "reduction" when pointing at the code.

| Word | Meaning | More |
|---|---|---|
| **apply** | `f a`: a function applied to one argument. `Apply` term. | [oymomo syntax](notes.md#apply) |
| **args** | Fixed name of a block's param binder after renaming; `args.n` is the param `n`. | [Programs](notes.md#functions-are-structs-of-blocks) |
| **atom** | A BANF operand: a constant (`[01]~'i8'`), a let name, or `args.label`, optionally with a form. | [Translation](notes.md#what-the-shape-is) |
| **BANF** | *Block-based ANF*. The first-order IR between oymomo and LLVM: SSA with block params instead of phi nodes. | [BANF](notes.md#banf) |
| **beta** | The reduction `(x -> body) e` → `body` with `e` put in for `x`. `reduction.beta`. | [The kernel](notes.md#reduce-one-step-at-the-root) |
| **binder** | Anything that introduces a name: a lambda param or a let. | |
| **block** | A BANF basic block: params, lets, one terminator. In oymomo, a lambda `args~{...} -> ...` in a function's struct. | [BANF](notes.md#blocks) |
| **blocker** | The part of a term that must reduce before the term can: an apply's callee, a projection's struct, an `if`'s condition… | [Translation](notes.md#blockers) |
| **blocks** | Fixed name of a function's self-binder after renaming; `blocks.then0 {}` jumps to block `then0`. | [Programs](notes.md#functions-are-structs-of-blocks) |
| **BruijnIndex** | A variable written by position, `$0` = nearest binder. `reduction.resolve` turns names into these. | [oymomo syntax](notes.md#builtins-and-indices-name-and-0) |
| **built-in** | A global constant written `$name` (`$fix`) with a reduction rule. | [The kernel](notes.md#built-ins) |
| **byte array** | The only literal: `[2a000000]` or `'text'`. Has no form unless one is written. | [oymomo syntax](notes.md#byte-arrays) |
| **convert** | Last pass of oymomo → BANF: reads a shaped term into BANF. Never reduces. | [Translation](notes.md#4-convert-read-the-shaped-term) |
| **Empty** | `terms.Empty`: a form that was *not written*. Not void, not a default. | [The kernel](notes.md#omitted-forms-are-empty) |
| **field** | One entry of a struct, with an optional label. Opcodes read their fields by position. | [oymomo syntax](notes.md#structs) |
| **fold** | Reduce an opcode call whose fields are literals to its result, the bytes LLVM would compute. `reduction.fold_opcode`. | [Opcodes](notes.md#folding) |
| **form** | The logical structure of a value: `'i32'`, `{x = 'i32'}`, `{c = 'i8'} => 'i32'`. Not a type; never checked. | [The kernel](notes.md#forms) |
| **Formed** | The term `e~F`, "`e` formed as `F`". | [The kernel](notes.md#formed-any-term-with-a-form) |
| **function form** | `P => R`, the form of a function. `FunctionForm` term. | [oymomo syntax](notes.md#function-forms) |
| **golden test** | `tests/goldens/name.oymo` compiled and compared to approved `.shaped.oymo`, `.banf` and `.ll` files. | [How to…](notes.md#add-a-golden-test) |
| **kernel** | The oymomo language itself: terms (`terms.py`), syntax (`grammar.py`) and reduction rules (`reduction.py`). Not one module. | [The kernel](notes.md#the-kernel-forms-built-ins-reduction) |
| **kernel-only** | What every built-in is (`$fix`): it must reduce away before BANF. | [The kernel](notes.md#built-ins) |
| **label** | A struct field's name. Optional (`''` = none), may repeat. | [oymomo syntax](notes.md#structs) |
| **lambda** | `x -> body`: a function of one param. `Lambda` term. | [oymomo syntax](notes.md#lambda) |
| **layout** | The physical memory representation (`{ i32, i32 }` in LLVM). Belongs to the backend. | [Overview](notes.md#type-form-layout) |
| **let** | `let x = e in body`, sugar for `(x -> body) e`. In BANF, one instruction `x = op`. | [oymomo syntax](notes.md#let) |
| **module** | The program's outer binder; its form declares every symbol. `module.fact {...}` calls a function. | [Programs](notes.md#module-declares-every-symbol) |
| **op** | A BANF let's value: `OpcodeCall`, `Call`, `MakeStruct`, `GetField`, `GetIndex`, `GetData`. | [BANF](notes.md#ops-and-their-forms) |
| **opcode** | One LLVM instruction, written `'add' {'i32', a, b}`. Listed in `opcodes.OPCODES`. | [Opcodes](notes.md#opcodes) |
| **oymomo** | The kernel lambda-calculus language. | [oymomo syntax](notes.md#oymomo-syntax) |
| **position** | A place in the program that wants a certain shape (a lambda, a struct, an atom…). | [Translation](notes.md#positions) |
| **project** | `s.x`: pick a field by label. `Project` term. | [oymomo syntax](notes.md#projection-and-struct-apply) |
| **pure** | An opcode with no side effects: it reads only its fields and gives only its result. Only pure opcodes fold. `Opcode.pure`. | [Opcodes](notes.md#folding) |
| **redex** | A term that can take a reduction step at its root. | [The kernel](notes.md#reduce-one-step-at-the-root) |
| **reduce** | `reduction.reduce`: take one reduction step at the root of a term. | [The kernel](notes.md#reduce-one-step-at-the-root) |
| **reduce_until_top_stable** | Fire the root rule or reduce the blocker, until neither changes the term. Its top constructor then can't change. | [Translation](notes.md#blockers) |
| **reduction** | Rewriting a term by the kernel's rules: beta, built-in rules, projection, struct apply, folding. Code in `reduction.py`; rules in [reduction_rules.md](reduction_rules.md). | [The kernel](notes.md#the-kernel-forms-built-ins-reduction) |
| **shape / shaped term** | An oymomo term reduced until every position looks like BANF. Output of `banf_translate.shape`. | [Translation](notes.md#translation-oymomo--banf--llvm) |
| **struct** | `{x = e, y = e}`: ordered fields. Also used as struct forms. | [oymomo syntax](notes.md#structs) |
| **struct apply** | `s [01]`: pick a field by position. | [oymomo syntax](notes.md#projection-and-struct-apply) |
| **symbol** | An LLVM global (`@fact`, `@putchar`, `@errno`). One per `module` declaration. | [Programs](notes.md#symbols) |
| **terminator** | The last instruction of a block: `return`, `jump`, `branch`, `switch`. | [BANF](notes.md#blocks) |
| **type** | Program-level meaning. Belongs to higher layers; the kernel has none. | [Overview](notes.md#type-form-layout) |
