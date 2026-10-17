# Oymo glossary

- Words with an Oymo-specific meaning, alphabetical.
- Standard terms (lambda, beta, redex, basic block, terminator…) keep their usual meaning.
- Code names are in `code`. **More** links to [notes.md](notes.md).

| Word | Meaning | More |
|---|---|---|
| **Alcor** | `language alcor`: the kernel systems language used to write the compiler; in the bootstrap seed. | [story.md](story.md) |
| **args** | Fixed name of a block's param binder after renaming; `args.n` is param `n`. | [Programs](notes.md#functions-are-structs-of-blocks) |
| **atom** | A BANF operand: a constant (`[01]~'i8'`), a let name, or `args.label`, optionally with a form. | [Translation](notes.md#what-the-shape-is) |
| **BANF** | *Block-based ANF*: first-order IR between oymomo and LLVM; SSA with block params instead of phi nodes. | [BANF](notes.md#banf) |
| **block** | A BANF basic block: params, lets, one terminator. In oymomo: a lambda `args~{...} -> ...` in a function's struct. | [BANF](notes.md#blocks) |
| **blocker** | The part of a term that must reduce first: an apply's callee, a projection's struct, an `if`'s condition… | [Translation](notes.md#blockers) |
| **built-in** | A global constant `$name` (`$fix`) with a reduction rule. Must reduce away before BANF. | [oymomo semantics](notes.md#built-ins) |
| **byte array** | The only literal: `[2a000000]` or `'text'`. No form unless one is written. | [oymomo syntax](notes.md#byte-arrays) |
| **convert** | Last pass of oymomo → BANF: reads a shaped term into BANF. Never reduces. | [Translation](notes.md#4-convert-read-the-shaped-term) |
| **Empty** | `terms.Empty`: a form that was *not written*. Not void, not a default. | [oymomo semantics](notes.md#omitted-forms-are-empty) |
| **f** | Fixed name of a function's self-binder (its struct of blocks) after renaming; `f.then0 {}` jumps to block `then0`. | [Programs](notes.md#functions-are-structs-of-blocks) |
| **form** | Logical structure of a value: `'i32'`, `{x = 'i32'}`, `{c = 'i8'} => 'i32'`. Not a type (oymomo has none), not a layout; never checked. | [oymomo semantics](notes.md#forms) |
| **Formed** | The term `e~F`, "`e` formed as `F`". | [oymomo semantics](notes.md#formed-any-term-with-a-form) |
| **function form** | `P => R`, the form of a function. `FunctionForm` term. | [oymomo syntax](notes.md#function-forms) |
| **Mizar** | `language mizar`: the general-purpose language, built as an extension of Alcor. | [story.md](story.md) |
| **module** | The program's outer binder; its form declares every symbol. `module.fact {...}` calls a function. | [Programs](notes.md#module-declares-every-symbol) |
| **op** | A BANF let's value: `OpcodeCall`, `Call`, `MakeStruct`, `GetField`, `GetIndex`, `GetData`. | [BANF](notes.md#ops-and-their-forms) |
| **opcode** | One LLVM instruction, `'add' {'i32', a, b}`. Folds on literal fields when `pure`. Listed in `opcodes.OPCODES`. | [Opcodes](notes.md#opcodes) |
| **oymomo** | The lambda-calculus language: terms (`terms.py`), syntax (`grammar.py`), reduction rules (`reduction.py`). | [oymomo syntax](notes.md#oymomo-syntax) |
| **position** | A place in the program that wants a certain shape (a lambda, a struct, an atom…). | [Translation](notes.md#positions) |
| **reduce_until_top_stable** | Fire the root rule or reduce the blocker until neither changes the term; its top constructor then can't change. | [Translation](notes.md#blockers) |
| **shape / shaped term** | An oymomo term reduced until every position looks like BANF. Output of `banf_translate.shape`. | [Translation](notes.md#translation-oymomo--banf--llvm) |
| **struct apply** | `s [01]`: pick a field by position. | [oymomo syntax](notes.md#projection-and-struct-apply) |
