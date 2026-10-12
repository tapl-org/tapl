# Oymo notes

Oymo compiles **oymomo**, a small lambda-calculus kernel language, to LLVM IR. The
kernel knows only byte arrays, structs, lambdas and a few built-ins; everything
else is meant to be built on top of it by higher layers.

```
oymomo source --parse--> terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

New here? Read these sections in order:

1. [Overview](#overview): the big picture, one program through every stage,
   and where the code lives.
2. [oymomo syntax](#oymomo-syntax): how to write oymomo (cheat sheet first).
3. [Programs](#programs): what a whole program must look like.
4. [How to…](#how-to): run the tests and make common changes.

The [Glossary](#glossary) at the end defines words like *form*, *BANF*, *atom* or *whnf*.

## Find an answer

| I want to… | Go to |
|---|---|
| Understand what a word means | [Glossary](#glossary) |
| See a program go from source to LLVM | [Overview › Walkthrough](#walkthrough-one-function-through-every-stage) |
| Know which file does what | [Overview › Where the code lives](#where-the-code-lives) |
| Write a struct, lambda, let, byte array… | [oymomo syntax › Cheat sheet](#cheat-sheet) |
| Know how `f a: t` or `x: A => B` groups | [oymomo syntax › Precedence](#precedence) |
| Know what a form is and how it differs from a type | [The kernel › Forms](#forms) |
| Know how terms reduce (`reduce`, built-ins, `$fix`) | [The kernel](#the-kernel-forms-built-ins-reduction) |
| Declare and define functions, imports and data | [Programs](#programs) |
| Find an opcode or its operand labels | [Opcodes](#opcodes) |
| Read BANF output | [BANF](#banf) |
| Understand how source becomes BANF and LLVM | [Translation](#translation-oymomo--banf--llvm) |
| Fix an error message | [Error messages](#error-messages) |
| Add an opcode, built-in or golden test | [How to…](#how-to) |
| Know *why* something is the way it is | [Design decisions](#design-decisions) |
| See what isn't decided or done yet | [Overview › Not done yet](#not-decided--not-done-yet) |
| See design changes in progress | [plans.md](plans.md) |

## How these notes are written

Each section starts with a one-line answer and an example, then the rules, then a
short **Why** that links to [Design decisions](#design-decisions) for the full story and the
rejected alternatives. When a plan lands, update the section it changes (see
[How to… › Update the notes](#update-the-notes-when-a-plan-lands)).

## Contents

- [Overview](#overview)
  - [Type, Form, Layout](#type-form-layout)
  - [The pipeline](#the-pipeline)
  - [Walkthrough: one function through every stage](#walkthrough-one-function-through-every-stage)
  - [Where the code lives](#where-the-code-lives)
  - [Testing](#testing)
  - [Not decided / not done yet](#not-decided--not-done-yet)
- [oymomo syntax](#oymomo-syntax)
  - [Cheat sheet](#cheat-sheet)
  - [Precedence](#precedence)
  - [Lambda](#lambda)
  - [Apply](#apply)
  - [Let](#let)
  - [Structs](#structs)
  - [Projection and struct apply](#projection-and-struct-apply)
  - [If](#if)
  - [Byte arrays](#byte-arrays)
  - [Function forms](#function-forms)
  - [Names](#names)
  - [Builtins and indices: `$name` and `$0`](#builtins-and-indices-name-and-0)
  - [Comments](#comments)
  - [Printer](#printer)
- [The kernel: forms, built-ins, reduction](#the-kernel-forms-built-ins-reduction)
  - [Forms](#forms)
  - [Built-ins](#built-ins)
  - [`reduce`: one step at the root](#reduce-one-step-at-the-root)
- [Programs](#programs)
  - [The shape of a program](#the-shape-of-a-program)
  - [`module` declares every symbol](#module-declares-every-symbol)
  - [Symbols](#symbols)
  - [Functions are structs of blocks](#functions-are-structs-of-blocks)
  - [One argument, always a struct](#one-argument-always-a-struct)
  - [Return forms are declared](#return-forms-are-declared)
  - [Nested function forms are rejected, for now](#nested-function-forms-are-rejected-for-now)
  - [First-order only](#first-order-only)
- [Opcodes](#opcodes)
  - [Table](#table)
  - [Naming](#naming)
  - [Monomorphic: one op per signature](#monomorphic-one-op-per-signature)
  - [Labels fit the op](#labels-fit-the-op)
- [BANF](#banf)
  - [Module](#module)
  - [Blocks](#blocks)
  - [Ops and their forms](#ops-and-their-forms)
  - [Printer](#printer-1)
- [Translation: oymomo → BANF → LLVM](#translation-oymomo--banf--llvm)
  - [oymomo → BANF](#oymomo--banf)
  - [BANF to LLVM](#banf-to-llvm)
- [Error messages](#error-messages)
  - [Names and resolution (`bruijn.py`)](#names-and-resolution-bruijnpy)
  - [Shaping (`banf_reduce.py`)](#shaping-banf_reducepy)
  - [Program shape (`banf_translate.py`)](#program-shape-banf_translatepy)
  - [Forms (`banf_translate.py`)](#forms-banf_translatepy)
  - [Block bodies (`banf_translate.py`)](#block-bodies-banf_translatepy)
  - [Built-ins](#built-ins-1)
  - [BANF verifier (`banf_terms.py`)](#banf-verifier-banf_termspy)
  - [LLVM (`llvm_translate.py`)](#llvm-llvm_translatepy)
- [How to…](#how-to)
  - [Run the checks](#run-the-checks)
  - [Try a program](#try-a-program)
  - [Add a golden test](#add-a-golden-test)
  - [Add an opcode](#add-an-opcode)
  - [Add a built-in reduction rule](#add-a-built-in-reduction-rule)
  - [Write a design change](#write-a-design-change)
  - [Update the notes when a plan lands](#update-the-notes-when-a-plan-lands)
- [Design decisions](#design-decisions)
  - [Type, Form, Layout are three words](#type-form-layout-are-three-words)
  - [BANF does not depend on LLVM](#banf-does-not-depend-on-llvm)
  - [Flat files with prefixes](#flat-files-with-prefixes)
  - [Brackets have one job each](#brackets-have-one-job-each)
  - [Struct, not record](#struct-not-record)
  - [The name `Project`](#the-name-project)
  - [The lambda arrow](#the-lambda-arrow)
  - [Forms are terms](#forms-are-terms-1)
  - [Omitted forms are `Empty`, with no default](#omitted-forms-are-empty-with-no-default)
  - [`Formed` binds tighter than application](#formed-binds-tighter-than-application)
  - [A byte array is only its bytes](#a-byte-array-is-only-its-bytes)
  - [Byte arrays are bracketed hex](#byte-arrays-are-bracketed-hex)
  - [Byte arrays are always little-endian](#byte-arrays-are-always-little-endian)
  - [Text byte arrays](#text-byte-arrays-1)
  - [Quoted names](#quoted-names)
  - [`$` for built-ins and indices](#-for-built-ins-and-indices)
  - [`let` is sugar](#let-is-sugar)
  - [Function forms are their own term](#function-forms-are-their-own-term)
  - [The printer lives in `printer.py`](#the-printer-lives-in-printerpy)
  - [Built-ins](#built-ins-2)
  - [One `module` binder](#one-module-binder)
  - [Functions are structs of blocks](#functions-are-structs-of-blocks-1)
  - [One argument, always a struct](#one-argument-always-a-struct-1)
  - [Return forms are declared, not inferred](#return-forms-are-declared-not-inferred)
  - [Monomorphic opcodes](#monomorphic-opcodes)
  - [BANF](#banf-1)
  - [Translation only reduces](#translation-only-reduces)
  - [Renaming](#renaming)
  - [LLVM translation converts nothing](#llvm-translation-converts-nothing)
- [Glossary](#glossary)

## Overview

### Type, Form, Layout

Three words for three levels. A type may have several forms, and a form several
layouts.

| Word | Meaning | Who knows about it |
|---|---|---|
| **Type** | Program-level meaning | Higher layers (not the kernel) |
| **Form** | Logical structure: how components are arranged | The kernel (oymomo) and BANF |
| **Layout** | Physical memory representation | The backend (LLVM) |

```
Bool     type: Bool                   form: 'i1'                   LLVM layout: i1
Int32    type: Int                    form: 'i32'                  LLVM layout: i32
Point    type: Point(x: Int, y: Int)  form: {x = 'i32', y = 'i32'}  LLVM layout: { i32, i32 }
```

A form is **not** a type: nothing checks it. `(x: 'Int' -> x) 'hello': 'Str'` is
fine and gives `'hello': 'Int'`. A param's form only replaces the argument's form.
Forms exist so the backend can generate machine code.

Why three words: a backend fact such as "i32 is 4-byte aligned" must not leak into
the kernel, where `[2a000000]: 'i32'` only means "these bytes, read as the form i32".
More in [The kernel › Forms](#forms).

### The pipeline

```
oymomo source --parse--> oymomo terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

`banf_translate` is a pipeline of four passes (details in [Translation](#translation-oymomo--banf--llvm)):

```
terms --bruijn.resolve--> BruijnIndex terms --banf_reduce.shape--> BANF-shaped term
      --banf_rename.rename--> no shadowing --banf_translate.convert--> BANF
```

| Stage | What it is |
|---|---|
| oymomo | The lambda-calculus kernel. Syntax in `grammar.py`, terms in `terms.py`. See [oymomo syntax](#oymomo-syntax). |
| BANF | A first-order IR shaped like LLVM, with block params instead of phi nodes. See [BANF](#banf). |
| LLVM | Generated with llvmlite. See [Translation › BANF to LLVM](#banf-to-llvm). |

### Walkthrough: one function through every stage

A recursive factorial. Each stage below is real output (from the same code the
golden tests run).

**1. oymomo source.** A program is a lambda `module -> {...}` around a struct of
definitions. `fact` is a struct of blocks; each block is a lambda over its params.

```
module: {fact = => 'i32'} -> {
  fact = f -> {
    entry = args:{n = 'i32'} ->
      let t0 = $eq_i32 {a = args.n, b = [00000000]:'i32'} in
      if t0 then f.then0 {} else f.else0 {n = args.n},
    then0 = args:{} -> [01000000]:'i32',
    else0 = args:{n = 'i32'} ->
      let t1 = $sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'} in
      let t2 = module.fact {n = t1} in
      let t3 = $mul_i32 {a = args.n, b = t2} in
      t3,
  },
}
```

- `fact = => 'i32'` declares a function returning `i32` that the body defines.
- `$eq_i32`, `$sub_i32`, `$mul_i32` are opcodes. `module.fact {...}` is a call.
- `f.then0 {}` jumps to the sibling block `then0`.

**2. Shaped term** (`banf_translate.shape`). Reduced until it has BANF's shape, and
the structural binders renamed to `module`, `blocks`, `args`. This program was
already in shape, so only `f` → `blocks` changed.

```
module: {fact= ⇒ 'i32'} → {
  fact= blocks → {
    entry= args: {n= 'i32'} →
      let t0 = $eq_i32 {a= args.n, b= [00000000]: 'i32'} in
      if t0 then blocks.then0 {} else blocks.else0 {n= args.n},
    then0= args: {} → [01000000]: 'i32',
    else0= args: {n= 'i32'} →
      let t1 = $sub_i32 {minuend= args.n, subtrahend= [01000000]: 'i32'} in
      let t2 = module.fact {n= t1} in
      let t3 = $mul_i32 {a= args.n, b= t2} in t3,
  },
}
```

**3. BANF** (`banf_translate.convert`). One line per let; the `args` struct became
block params; the `if` became a `branch`.

```
fact: i32
  entry(n: i32):
    t0 = eq_i32 n, [00000000]:i32
    branch t0, then0(), else0(n)
  then0():
    return [01000000]:i32
  else0(n: i32):
    t1 = sub_i32 n, [01000000]:i32
    t2 = call fact(t1)
    t3 = mul_i32 n, t2
    return t3
```

**4. LLVM IR** (`llvm_translate.translate`). One BANF block → one LLVM block, one
let → one instruction. Byte arrays became numbers.

```llvm
define i32 @"fact"(i32 %"n")
{
entry:
  %"t0" = icmp eq i32 %"n", 0
  br i1 %"t0", label %"then0", label %"else0"
then0:
  ret i32 1
else0:
  %"t1" = sub i32 %"n", 1
  %"t2" = call i32 @"fact"(i32 %"t1")
  %"t3" = mul i32 %"n", %"t2"
  ret i32 %"t3"
}
```

### Where the code lives

Everything is flat in `src/oymo/oymomo/`. A file's prefix says its stage, and each
module has a test of the same name in `tests/oymomo/`.

| File | Role |
|---|---|
| [`grammar.py`](../src/oymo/oymomo/grammar.py) | Parser: oymomo source → terms |
| [`rule_names.py`](../src/oymo/oymomo/rule_names.py) | Names of the grammar rules |
| [`terms.py`](../src/oymo/oymomo/terms.py) | oymomo term classes (`Lambda`, `Apply`, `Struct`, `Formed`…) |
| [`printer.py`](../src/oymo/oymomo/printer.py) | Prints terms, compact or pretty |
| [`bruijn.py`](../src/oymo/oymomo/bruijn.py) | `resolve`, `shift`, `substitute`, `reduce`, `BUILTIN_RULES` |
| [`banf_reduce.py`](../src/oymo/oymomo/banf_reduce.py) | Reduces a term until it has BANF's shape |
| [`banf_rename.py`](../src/oymo/oymomo/banf_rename.py) | Renames binders so none shadow each other |
| [`banf_translate.py`](../src/oymo/oymomo/banf_translate.py) | `shape`, `convert`, `translate`: oymomo → BANF |
| [`banf_terms.py`](../src/oymo/oymomo/banf_terms.py) | BANF classes, `form_of`, verifier, BANF printer |
| [`banf_opcodes.py`](../src/oymo/oymomo/banf_opcodes.py) | Opcode signatures (`OPCODES`), no LLVM |
| [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py) | llvmlite code for each opcode (`DEFAULT_OPCODES`) |
| [`llvm_translate.py`](../src/oymo/oymomo/llvm_translate.py) | BANF → LLVM IR, `Target` |

Import rules:
- Only `llvm_*.py` imports llvmlite.
- No `banf_*.py` imports an `llvm_*.py`. BANF depends only on `oymomo.terms`.

Anything LLVM needs that BANF doesn't have is passed to the LLVM translator:

```python
Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=DEFAULT_OPCODES)
```

- `opcodes` maps each opcode name to the LLVM instructions for it. BANF only names
  the opcode (`add_i32`); the target supplies the implementation.
- There is no `byte_order` field: byte arrays are always little-endian, and the
  target's byte order comes from `data_layout` (`e` or `E`). A separate field could
  disagree with it.

Why flat files: the stages are small, and a prefix shows the stage as clearly as a
subpackage, without extra `__init__.py` files and import paths.

### Testing

- Unit tests per stage: `grammar_test.py`, `printer_test.py`, `banf_opcodes_test.py`,
  `banf_terms_test.py`, `bruijn_test.py`, `banf_reduce_test.py`,
  `banf_rename_test.py`, `banf_translate_test.py`, `llvm_translate_test.py`.
- BANF tests build modules by hand, so they don't depend on the translator.
- Every LLVM test parses the IR with `llvmlite.binding` and verifies it.
- Golden tests (`tests/goldens/`): each `name.oymo` produces approved
  `name.shaped.oymo`, `name.banf` and `name.ll` files. See
  [How to… › Add a golden test](#add-a-golden-test).

### Not decided / not done yet

- Nested function forms (in data forms, or as a function form's param or result).
  See [Programs](#nested-function-forms-are-rejected-for-now).
- Closures and higher-order functions.
- Struct constants in LLVM, including struct data initializers.
- The `language oymomo` header at the top of `.oymo` files is checked and stripped
  by the golden test; the parser doesn't handle layers yet.
- Void functions: every function returns a value.

## oymomo syntax

The surface syntax of the oymomo kernel, parsed by
[`grammar.py`](../src/oymo/oymomo/grammar.py) into the terms in
[`terms.py`](../src/oymo/oymomo/terms.py). What terms *mean* is in
[The kernel](#the-kernel-forms-built-ins-reduction); what a whole program looks like is in
[Programs](#programs).

### Cheat sheet

```
x: 'i32' -> body             Lambda (also x -> body, and → for ->)
f a b                        Apply: (f a) b
{x = e1, y = e2}             Struct
{e1, y = e2}                 Struct with an unlabeled field
s.x                          Project: field by label
s [00]                       Apply on a struct: field by position
if c then a else b           Sugar for {b, a} c
let x = e in body            Sugar for (x -> body) e
$add_i32, $fix g             Builtin, applied like a function
$0                           BruijnIndex
[2a 00 00 00]                Byte array (hex)
'Hello'                      Byte array (text)
e: 'i32'                     Formed: e with a form
{c = 'i8'} => 'i32'          Function form (also ⇒)
"a b"                        Quoted name
// comment                   Line comment
```

#### Brackets: one job each

```
{}  structs (ordered fields): {x = e}, also struct forms {x = 'i32'}
()  grouping only
[]  byte arrays [2a 00 00 00]
''  text byte arrays 'Hello'
""  quoted names "a b"
```

Why: the parser never has to guess. `(` always groups, `{` is always a struct, `[`
is always bytes.

#### Reserved words

`if then else let in`. Nothing else: `fix`, `prim`, `module`, `args` are ordinary
names.

### Precedence

Highest first. The rule: **values bind tighter than things that reduce**. `Formed`
and `FunctionForm` never reduce, so `:` and `=>` bind tighter than application;
`.` binds tighter still, since `module.T` and `args.n` read as paths.

| Level | Syntax | Associativity |
|---|---|---|
| 1 | atoms: names, `$name`, `$0`, `[..]`, `'..'`, `{..}`, `(..)` | |
| 2 | project `s.x` | left |
| 3 | function form `P => R` | right |
| 4 | formed `e: F` | right |
| 5 | apply `f a` | left |
| 6 | `x -> body`, `if`, `let` | extend as far right as possible |

Examples:

| Source | Means |
|---|---|
| `f a b` | `(f a) b` |
| `f a.x b` | `(f a.x) b` |
| `a -> b -> a b` | `a -> (b -> (a b))` |
| `f [01]: 'u8' [02]` | `f ([01]: 'u8') [02]` |
| `f a: g b` | `f (a: g) b` |
| `$fix f: t` | `$fix (f: t)` |
| `y: f a` | `(y: f) a`; write `y: (f a)` |
| `a: b: c` | `a: (b: c)` |
| `x: A => B` | `x: (A => B)` |
| `A => B: C` | `(A => B): C` |
| `f a => g b` | `f (a => g) b` |
| `{a = 'i8'} => {b = 'i8'} => 'i32'` | `{a = 'i8'} => ({b = 'i8'} => 'i32')` |
| `[00]: 'i8' => 'i32'` | `[00]: ('i8' => 'i32')`; write `([00]: 'i8') => 'i32'` |
| `s [00] [01]` | `(s [00]) [01]` |
| `f s [00]` | `(f s) [00]` |
| `s [00] : t` | `s ([00] : t)` |
| `$add_i32 {...}.a` | `$add_i32 ({...}.a)` |
| `f $fix g` | `(f $fix) g` |
| `let x = e in a b` | `let x = e in (a b)` |

Things that need parentheses:
- A lambda, `if` or `let` as an argument: `f (x -> x)`; `f x -> x` is a syntax error.
- An application inside `:`: `y: (f a)`, `(f a): t`.
- A param with a form on the left of `=>`: `([00]: 'i8') => 'i32'`.

Why `:` is above application, unlike Haskell, OCaml and Lean: see
[Design decisions](#formed-binds-tighter-than-application).

### Lambda

`x: form -> body`, or `x -> body` with no form. One parameter, always.

```
x: 'i32' -> x
a -> b -> a b               same as  a -> (b -> (a b))
x: {c = 'i8'} => 'i32' -> x
```

- `->` and `→` (U+2192) are the same.
- The param's form is an ordinary expression at the formed level (see
  [Forms are terms](#forms-are-terms)). It ends at the first `->`:
  `x: a -> b -> c` is the lambda `x: a` with body `b -> c`. A lambda or an
  application in it needs parentheses: `x: (a -> b) -> c`, `x: (f a) -> x`.
- The form may be left out; then it is `Empty` (see
  [The kernel](#omitted-forms-are-empty)).
- A lambda is tried before `:`, so `x: F -> body` is a lambda with a param form,
  not `x: (F -> body)`.

### Apply

`f a`: one argument. Left-associative: `f a b` is `(f a) b`.

Every built-in and every function takes one argument; several operands go in a
struct: `$add_i32 {a = x, b = y}`. See
[Programs › One argument, always a struct](#one-argument-always-a-struct).

### Let

`let x = e in body` is sugar for `(x -> body) e`. No new term.

```
let t0: 'i1' = $eq_i32 {a = args.n, b = [00000000]: 'i32'} in t0
```

- The optional form goes on the name, as on a lambda param.
- Extends as far right as possible: `let x = e in a b` is `let x = e in (a b)`. As
  an argument it needs parens: `f (let x = e in x)`.
- The printer prints *every* apply of a lambda as a `let`.

Why: in `(t0 -> rest) (op)` the value comes after the whole rest of the block, far
from its name. With `let`, a chain of lets reads top to bottom, like BANF.

### Structs

`{label = value, ...}`: an ordered list of fields.

```
{x = e1, y = e2}
{'1', b = '2'}               unlabeled field, then field b
{x = 'i32', y = 'i8'}        a struct used as a form
```

- **Order matters**: `{x = 'i32', y = 'i8'}` and `{y = 'i8', x = 'i32'}` are
  different forms (`{i32, i8}` vs `{i8, i32}` in LLVM). That is why it's called a
  struct, not a record.
- **Every field has a value.**
- **Labels are optional**, so a struct can be a tuple. The labeled form is parsed
  first, so `{a}` is an unlabeled field holding the variable `a`, not a field named
  `a`.
- An unlabeled field's label is `''`. A written name is never empty (`{"" = x}` is
  a parse error), so `''` only means "no label". The printer prints such a field as
  its value alone.
- **Labels may repeat.** `s.a` picks the first: `{a = '1', a = '2'}.a` gives `'1'`.
- In BANF, unlabeled fields are fine in value structs and data forms, but not where
  a label names something; see
  [Translation › Labels](#labels-name-params-declarations-and-blocks).

### Projection and struct apply

Two ways to pick a field:

| Syntax | Picks by | Example | Gives |
|---|---|---|---|
| `s.a` | label written in the source | `{a = '1', a = '2'}.a` | `'1'` |
| `s i` | position, `i` is a term | `{a = '1', a = '2'} [01]` | `'2'` |

- `s.a` is a `Project` term. `s.` can't be written, so projection never reaches an
  unlabeled field.
- `s i` is an ordinary `Apply` with a reduction rule (see
  [The kernel](#reduce-one-step-at-the-root)). It ignores labels, so every
  field is reachable, unlabeled and duplicate ones included. `i` can be computed at
  run time.
- An index is an unsigned little-endian integer of any length, starting at 0:
  `[01]`, `[0100]` and `[01000000]` are all 1; `[0001]` is 256. A form on the index
  is ignored.
- A missing field is stuck (no reduction): an index past the last field, `''`, or
  an argument that isn't a byte array.
- Labels stay static: no `s.(e)`, no `{(e) = v}`.
- In BANF, `s i` on a value struct is the op `GetIndex`, and the index must be a
  literal. See [Translation](#what-the-shape-is).

Why `Project` and not `Select`/`FieldAccess`: see
[Design decisions](#the-name-project).

### If

`if c then a else b` is sugar for `{b, a} c`: a struct applied to the condition. `c`
reduces to `[01]` (field 1, then) or `[00]` (field 0, else), read as any
[struct apply](#structs) index: any length, a form ignored. Extends as far right as
possible.

```
if c then t else e           parses to   {e, t} c
{e, t} c                     prints as   if c then t else e
{'1', '2'} [01]              prints as   if [01] then '2' else '1'
{x = e, t} c                 prints as   {x = e, t} c       labeled: not an if
{e, t, d} c                  prints as   {e, t, d} c        3 fields: not an if
```

- There is no `If` term. The printer prints every struct with two unlabeled fields,
  applied to anything, as `if` (`bruijn.branch`), so the output parses back to the
  same term.
- In BANF, `{e, t} c` in tail position is a branch, labeled or not. See
  [Translation](#if-only-in-tail-position-jumping-to-two-different-blocks).
- Design: [plan_if_as_struct_apply.md](plan_if_as_struct_apply.md).

### Byte arrays

The kernel has no numbers, only bytes.

```
[2a000000]: 'i32'            42, as an i32
[2a00 0000]                  same bytes
[2a 00 00 00]                same bytes
[]                           empty
[deadbeef cafebabe
 00112233 44556677]: {lo = 'i64', hi = 'i64'}
```

- Inside `[]`: groups of hex digits separated by whitespace (newlines included). A
  group may hold any number of bytes but must have an even number of digits.
- No comments inside the brackets.
- **Always little-endian, on every target**: `[2a000000]: 'i32'` is 42 everywhere.
  See [Design decisions](#byte-arrays-are-always-little-endian).
- The `: form` is optional and is an ordinary `Formed`, not part of the literal: the
  same bytes `[01000000]` could be `'i32'` 1 or `{a = 'i16', b = 'i16'}`.

#### Text byte arrays

`'Hello'` is the same term as `[48656c6c 6f]`.

- Allowed characters: `0x20..0x7e` except `'` and `\`. No escapes (room for them
  later). Single line. `''` is the empty array.
- Bytes with `'`, `\`, or non-printable characters are written in hex.
- A named form such as `'i32'` is a text byte array.

### Function forms

`P => R` (or `P ⇒ R`, U+21D2): the form of a function with param form `P` and
result form `R`. A `FunctionForm(param, result)` term.

```
{c = 'i8'} => 'i32'          takes {c: i8}, returns i32
=> 'i32'                     param left out: FunctionForm(Empty, 'i32')
{putchar = {c = 'i8'} => 'i32'}   a function form as a field value
```

- One param, matching one-argument lambdas, and no param name: callers use the
  struct form's labels (`module.putchar {c = [41]: 'i8'}`).
- `=> R` is not `{} => R`: the first has no param, the second a struct with no
  fields. In `module`, `=> R` declares a function the body defines (see
  [Programs](#module-declares-every-symbol)).
- `=> => R` is `=> (=> R)`. With something on its left, `=>` takes it as the param,
  so `f => b` is `(f) => b`; as an argument it needs parentheses, `f (=> b)`.
- A different arrow from `->` tells a form from a lambda at a glance: in
  `module: {putchar = {c = 'i8'} => 'i32'} -> {...}`, `=>` is in a form and `->`
  binds a lambda. It also means a binder's form safely ends at `->`.

Why a dedicated term instead of a tagged struct: see
[Design decisions](#function-forms-are-their-own-term).

### Names

Plain identifiers match `[A-Za-z_][A-Za-z0-9_]*`, except reserved words. Any other
non-empty string is written in double quotes: `"a b"`, `"if"`, `"main.1"`.

- `"x"` and `x` are the same name; the parser stores the decoded string.
- Escapes: `\"`, `\\`, `\u{hex}`. No raw newlines. `""` is rejected.
- Quotes work wherever a name appears: variables, lambda params, struct labels,
  projection labels (`s."a b"`). Form names are byte arrays (`'a b'`), not names.
- Printers quote a name only when needed, BANF's too
  (`Data('my data', ...)` prints `"my data": i8`).
- Plain identifiers are ASCII only.

Why: LLVM does the same (`@main` vs `@"foo bar"`), so names map straight to
symbols, including mangled names from higher layers. More in
[Design decisions](#quoted-names).

### Builtins and indices: `$name` and `$0`

`$` marks a reference no user name binds.

| Syntax | Term | Bound by |
|---|---|---|
| `$0`, `$1`… | `BruijnIndex` | position (`$0` = nearest binder) |
| `$add_i32`, `$fix` | `Builtin` | the kernel |

- An identifier can't start with a digit, so the two never overlap.
- No space after `$`, and no quotes: `$ fix` and `$"fix"` are errors.
- Nothing is reserved after `$`; the parser accepts any `$name`.
- `$name` is an atom, like a variable.

What built-ins do: [The kernel › Built-ins](#built-ins).

### Comments

`// comment` to the end of the line. (`#` is unused.)

### Printer

[`printer.py`](../src/oymo/oymomo/printer.py) prints terms for any stage:
`printer.show(term)` and `printer.show_form(form)`. Both print `→` for lambdas and
`⇒` for function forms.

| Mode | Use | Output |
|---|---|---|
| compact (default) | tests | One line, parens only where needed: `a → b → a b`, `f (x → x)`, `(f a).x`. Forms without a space: `x:'i32' → x`. |
| `pretty=True` | people, goldens | Source that parses back to the same term (tested). Bytes in groups of four (`[deadbeef cafebabe]`) or as `'text'`. |
| `name_indices=True` | either mode | Prints a `BruijnIndex` as its binder's name, so resolved terms read like source. |

Rules in both modes:
- An omitted form is not shown. Names are quoted when needed (`"if"`, `"a b"`).
- An apply of a lambda prints as `let`: compact `let x:'i8' = e in body`, pretty
  `let x: 'i8' = e in body`.
- `BruijnIndex` prints as `$0`, `Builtin` as `$add_i32`, `Variable` as its name.
  `$0` parses back as a `BruijnIndex`, so a resolved term round-trips.
- With `name_indices=True`, `$i` is kept where an inner binder shadows the name
  (`x → x → $1`) or no binder is in scope, so the output still resolves to the
  same term. The shaped golden and the rename tests use it.
- Text form `'...'` is used only for a byte array with no form, all text bytes,
  at most 128 bytes; otherwise hex. (A written form usually means a number; long
  blobs read better as hex; the limit is fixed so output doesn't depend on `width`.)

Pretty mode breaks a term wider than `width` (default 80), indenting by `indent`
(default 2):
- a struct puts one field per line, with a trailing comma;
- a lambda's body goes on the next line, indented, unless the body is a struct or
  another lambda (so `module: {...} → {` stays together);
- an apply's argument goes on the next line, indented;
- a `let` puts its body on the next line at the `let`'s own indentation, so a chain
  reads one let per line:
  ```
  entry = args: {n = 'i32'} →
    let t0 = $eq_i32 {a = args.n, b = [00000000]: 'i32'} in
    if t0 then f.then0 {} else f.else0 {n = args.n},
  ```
- an `if` puts `then` and `else` on their own lines.

Compact mode lets grammar tests check nesting by comparing with parenthesized
source: `show(parse('f a b')) == show(parse('(f a) b'))`.

## The kernel: forms, built-ins, reduction

What oymomo terms mean. Syntax is in [oymomo syntax](#oymomo-syntax).

### Forms

A **form** is a value's logical structure (`'i32'`, `{x = 'i32'}`), used to generate
machine code. It is **not a type**: nothing checks one form against another.

```
(x: 'Int' -> x) 'hello': 'Str'      gives  'hello': 'Int'
```

A param's form is only used to replace the passed argument's form. See also
[Overview › Type, Form, Layout](#type-form-layout).

#### Forms are terms

There is no separate form syntax or form class. A form is an ordinary term:

| Form | Written | Term |
|---|---|---|
| named | `'i32'` | `ByteArray(b'i32')` (a bare `i32` is a variable) |
| struct | `{x = 'i32', y = 'i8'}` | `Struct` |
| function | `{c = 'i8'} => 'i32'` | `FunctionForm(param, result)` |

- Any term may be a form. A binder's form (`x: F -> b`, `let x: F = v in b`) is the
  same kind of expression as the `F` of `e: F`: `x: i32 -> x`,
  `x: module.T -> x`, `x: 'i8' => 'i32' -> x`, `x: [00]: 'i8' -> x`.
- Forms are resolved like other terms: a variable in a lambda param's form is looked
  up *outside* the lambda, so in `x: (x) -> x` the form refers to an outer `x`.
- BANF translation needs **literal** forms (named forms and structs of them) and
  rejects others with "form must be a literal".
- Locations are left out of `==` on every term, so a parsed form equals the same
  form built in code (`terms.ByteArray(b'i32')`, `terms.struct_form(...)`).

Why: one syntax and one set of terms for values and forms; later stages can compute
forms with the same machinery as values.

#### Omitted forms are `Empty`

Every binder's `: form` may be left out (`x -> body`, `let x = e in ...`). An omitted
form is `terms.Empty`, meaning **not written**.

- `Empty` is not a void form. There is no void form; `: 'void'` is just the form
  named void.
- `Empty` has no default meaning. Each position says what it means there, or rejects
  it. A BANF let takes its op's form, so `let t0 = $eq_i32 {...} in t0` needs no
  `t0: 'i1'`. A byte array with nothing giving it a form (`[01]` alone) is rejected:
  "form must be written".
- A byte array has no form of its own: `[2a]` is just bytes.

Why: quick sketches stay short, and nothing is silently defaulted.

#### `Formed`: any term with a form

`e: F` is the term `Formed(e, F)`, "`e`, formed as `F`". Since `F` is an expression,
a form can come from a variable:

```
(x -> y -> y: x) 'i1' [01]          gives  [01]: 'i1'
```

- A byte array is only its bytes: `[01]: 'i8'` is `Formed(ByteArray([01]), 'i8')`,
  just as `y: 'i8'` is `Formed(y, 'i8')`. Every `:` that isn't on a binder is one
  term with one meaning, and beta reduction alone gives a dynamic form.
- `Formed` itself never reduces. `whnf` reduces inside `Formed.term`, and a struct
  apply (so an `if`) sees through a form on its index.
- Precedence: [oymomo syntax › Precedence](#precedence). Design history:
  [plan_annotation.md](plan_annotation.md).

In BANF translation, a formed byte array becomes a constant; any other formed atom
becomes that atom with the written form. **The written form replaces the atom's own
form, unchecked**: `([01]: 'i8'): 'i16'` is the constant `[01]:i16`, and
`args.n: 'i32'` is `n:i32` even when `n` is `i8`. LLVM translation rejects a formed
name whose LLVM type differs from the name's.

### Built-ins

Machine primitives (arithmetic, logic, comparison, conversion) and kernel helpers
are **built-ins**, each a global constant written `$name`:

```
$add_i32 {a = x, b = y}
$fix g
```

- Every built-in takes one argument; several operands go in a struct. A call is
  always `Apply(Builtin(name), arg)`.
- Every built-in is its own constant: there is no `$` struct to project from,
  apply, or unpack.
- No names are reserved for them: `fix -> fix` is an ordinary lambda.

A name can appear in two tables:

| Table | File | Gives |
|---|---|---|
| `BUILTIN_RULES` (`BuiltinRule(name, strict, needs, rule)`) | [`bruijn.py`](../src/oymo/oymomo/bruijn.py) | a reduction rule |
| `OPCODES` / `DEFAULT_OPCODES` | [`banf_opcodes.py`](../src/oymo/oymomo/banf_opcodes.py) / [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py) | machine code (an **opcode**) |

| Name | Rule | Opcode |
|---|---|---|
| `fix` | `$fix g` gives `g ($fix g)` | no: it must reduce away |
| `add_i32` and other opcodes | not yet (see [plan_constant_folding.md](plan_constant_folding.md)) | yes |

- A built-in with a rule and no opcode is **kernel-only**. This follows from the
  tables, with no flag to keep in sync. Reduction must remove it.
- A **strict** rule needs its argument reduced first (to `needs`, e.g.
  `'a struct'`). `$fix` is not strict: `$fix g` unfolds without reducing `g`.
- `convert` is the only gate into BANF: `$name arg` becomes an `OpcodeCall` only if
  `name` is in `OPCODES`. Leftovers are errors: see
  [Error messages › Built-ins](#built-ins-1).
- BANF keeps the split between instructions and symbols: `OpcodeCall` for opcodes,
  `Call` for `module` symbols. `$add_i32` never becomes an LLVM symbol.

Why built-ins instead of `module` names, a `prim` binder, or a `fix` term: see
[Design decisions › Built-ins](#built-ins-2) and
[plan_builtin.md](plan_builtin.md).

### `reduce`: one step at the root

`bruijn.reduce(term)` takes one step if the root is a redex; otherwise it returns
`term` itself, so `reduce(t) is t` means "not a redex". It never looks inside.

| Rule | Before | After |
|---|---|---|
| beta | `(x -> body) e` | `body` with `e` for `x` |
| beta with form | `(x: F -> body) e` | `body` with `e: F` for `x` (`e`'s own form dropped) |
| built-in | `$fix g` | `g ($fix g)` (by `BUILTIN_RULES[name]`, if it fires) |
| projection | `{a = e, ...}.a` | `e` |
| struct apply | `{e0, e1, ...} [01]` | `e1` |
| if (struct apply) | `if [01] then a else b` / `if [00] ...` | `a` / `b` |

Not redexes:
- a built-in with no rule (`$add_i32 {...}`), an unknown one (`$nope g`), or a rule
  that doesn't fire;
- a projection with a missing label;
- a struct apply with an index past the end, `''`, or an argument that isn't a byte
  array yet (index read by `bruijn.index_value`: unsigned little-endian, form
  ignored). So `if [02] then a else b` is stuck, and `if [0100] then a else b` is `a`.

Properties:
- **Only the root.** Arguments, lambda bodies, struct fields and `if` arms are not
  touched, nor is a head that isn't a redex yet (`$fix g a`, `{p = {a = e}}.p.a`).
  [`banf_reduce`](#2-banf_reduceshape-reduce-until-each-position-has-its-shape)
  reduces heads.
- **At most one rule applies**, so order doesn't matter: beta needs a `Lambda`
  callee, struct apply a `Struct`, a built-in rule a `Builtin`.
- **Never raises, never recurses.** Loops come from calling it repeatedly, so the
  fuel limit lives in `banf_reduce`.
- **Opcodes are not run** (`$add_i32 {...}` is stuck).
- Helpers: `shift`, `substitute`, `beta`
  (`shift(substitute(body, 0, shift(arg, 1)), -1)`), `project`, `index_value`.

## Programs

What a whole oymomo program must look like to compile to BANF and LLVM. See
[Overview › Walkthrough](#walkthrough-one-function-through-every-stage)
for a full example through every stage.

### The shape of a program

A program is a lambda `module -> {...}` around a struct of definitions:

```
module: {putchar = {c = 'i8'} => 'i32', errno = 'i32', main = => 'i32'} -> {
  main = f -> {entry = args:{} -> let t0 = module.putchar {c = [41]:'i8'} in t0},
}
```

```
module: { declarations } -> {               the program
  name = f -> {                             a function: a struct of blocks
    entry = args: { params } -> body,       a block: a lambda over its params
    other = args: { params } -> body,
  },
  name = [bytes],                           defined data
}
```

The binder names (`module`, `f`, `args`) can be anything in the source; shaping
renames them to `module`, `blocks`, `args` (see
[Translation](#3-banf_renamerename-fixed-names-and-no-shadowing)).

### `module` declares every symbol

`module`'s form declares every symbol of the module, imported or defined, in one
struct. The body is passed back in as `module`, so functions call each other and
imports the same way: `module.fact {n = t1}`, `module.putchar {c = [41]:'i8'}`,
`module.errno`.

The shape of each declaration says what it is:

| Declaration | Defined in the body? | Result |
|---|---|---|
| `=> R` | yes, as a function | `banf.Function`: params from its entry block, return form `R` |
| `=> R` | no | error: "'main' declares no params, so it must be defined." |
| `{...} => R` | no | imported function, `banf.Signature`: `declare i32 @putchar(i8 %c)` |
| `{...} => R` | yes | error: "'putchar' declares its params; a definition takes them from its entry block." |
| data form `F` | no | imported data, `banf.Data`: `@errno = external global i32` |
| data form `F` | yes, as a byte array | defined data, `banf.Data` with a value: `@answer = global i32 42` |

Rules:
- A body label must be declared: "'f' is defined but not declared."
- A definition must fit its declaration: `=> R` needs `blocks -> {...}`; a data
  declaration needs a byte array ("'answer' is declared as data, so its definition
  must be a byte array.").
- The body field is taken to whnf, so `answer = (x -> x) [2a]` is fine. A data
  definition's form is the declared one; a form written on the byte array
  (`[2a]: 'i16'`) is dropped.
- Every parameter list is written **once**: a defined function's only in its entry
  block, an imported function's only in its declaration.
- Every return form is written, in the declaration (see
  [Return forms are declared](#return-forms-are-declared)).
- A forgotten definition (declared `=> R`, not defined) is a translation error, not
  a link error.
- A module with no symbols writes `module: {}`. The form is required.
- BANF bindings come out in declaration order.
- Recursion needs no `$fix`: functions call each other by projection on `module`,
  as LLVM functions call each other by symbol. A `$fix` in the source is only
  unfolded during shaping; it never becomes a loop or call.
- Every external symbol is declared in `module`, so a module lists everything it
  needs from outside, and the linker resolves it.

Why one binder instead of `decls` + `defs`: see
[Design decisions](#one-module-binder).

### Symbols

Every declaration in `module` becomes one LLVM symbol, named after its label
(`@fact`, `@putchar`, `@errno`).

### Functions are structs of blocks

```
fact = f -> {
  entry = args:{n = 'i32'} ->
    let t0 = $eq_i32 {a = args.n, b = [00000000]:'i32'} in
    if t0 then f.then0 {} else f.else0 {n = args.n},
  then0 = args:{} -> [01000000]:'i32',
  else0 = args:{n = 'i32'} ->
    let t1 = $sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'} in
    let t2 = module.fact {n = t1} in
    let t3 = $mul_i32 {a = args.n, b = t2} in
    t3,
}
```

- The function's binder (`f`, renamed `blocks`) is its own struct of blocks, so
  `f.then0 {}` jumps to a sibling block. Same self-reference trick as `module`, one
  level down.
- Each block is a lambda over one struct (`args:{n = 'i32'} -> ...`); the binder
  (`args`) is the block's param struct.
- **The first field is the entry block**, whatever its name. It can't be jumped to
  (see [BANF](#the-entry-block-cannot-be-jumped-to)).
- A block body is a chain of lets ending in a terminator:
  - return an atom: `[01000000]:'i32'`, `args.n`, or a let name;
  - jump: `f.label {...}`;
  - branch: `if c then f.a {...} else f.b {...}`.

Why: it is plain oymomo (lambdas, structs, application), so blocks and jumps
needed no new syntax, and every name in the BANF output comes from the source.

### One argument, always a struct

A lambda takes exactly one argument. In a program, every block's, opcode's and
imported function's argument must be a **struct**, with labels naming the
arguments: `{minuend = x, subtrahend = y}`.

Translation expands the struct **one level** into params, one-to-one with LLVM:

```
oymomo: fact = f -> {entry = args:{n = 'i32'} -> ...}
BANF:   entry(n: i32)
LLVM:   define i32 @fact(i32 %n)
```

- Only one level: `args:{p = {x = 'i32', y = 'i32'}}` gives one param `p` whose form
  is a struct, i.e. one LLVM argument `{i32, i32} %p`.
- A call or jump argument is a struct literal of atoms whose labels match the
  callee's params in order, or the block's own `args` forwarded as-is:
  `module.add args`, `f.body args`.
- The expansion happens in oymomo → BANF, so BANF → LLVM stays one-to-one.

Why: the kernel stays a one-argument lambda calculus, and labels at every call site
stop arguments being mixed up silently. A deeper expansion would have to invent
names like `p.x`, and LLVM passes struct values anyway.

### Return forms are declared

Every function's return form, imported or defined, is written in its `module`
declaration (`main = => 'i32'`). Each return is checked against it. Recursion needs
nothing special:

```
module: {loop = => 'i8'} -> {
  loop = f -> {
    entry = args:{c = 'i1'} -> if args.c then f.a {} else f.b {},
    a = args:{} -> let t = module.loop {c = [00]:'i1'} in t,
    b = args:{} -> [07]:'i8',
  },
}
```

Why declare instead of infer: the form is written once, where the symbol is
declared. Inference had to iterate over the module to a fixed point, and a function
with no base case (`entry = args:{} -> let t = module.g {} in t`) had no return form
at all.

### Nested function forms are rejected, for now

A function form is accepted only as a `module` declaration's whole form. Rejected
until their meaning is decided:
- inside a data form: `module: {libc = {putchar = {c = 'i8'} => 'i32'}}`;
- as a param or result: `module: {g = {c = 'i8'} => {d = 'i8'} => 'i32'}`,
  `main = => => 'i32'`;
- with a non-struct param: `module: {g = 'i8' => 'i32'}`.

`Empty` forms inside a declaration are rejected too ("form must be written"), since
nothing infers a form. `Empty` alone (`main = `) can't be written: a struct field
needs a value.

### First-order only

No closures and no escaping lambdas. After reduction, the only lambdas left are the
program, function, block and let binders. A helper lambda that reduction inlines is
fine; one left over is an error.

## Opcodes

An **opcode** is a built-in with machine code: `$add_i32 {a = x, b = y}`.
Signatures are plain data in [`banf_opcodes.py`](../src/oymo/oymomo/banf_opcodes.py)
(`OPCODES`, no LLVM); their LLVM code is in
[`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py) (`DEFAULT_OPCODES`). A test
checks that both tables have the same names.

### Table

`T` is one of `i1 i8 i16 i32 i64`.

| Ops | Signature | Includes `i1`? | LLVM |
|---|---|---|---|
| `add mul` | `{a: T, b: T} => T` | no | `add`, `mul` |
| `and or xor` | `{a: T, b: T} => T` | yes (boolean logic) | `and`, `or`, `xor` |
| `sub` | `{minuend: T, subtrahend: T} => T` | no | `sub` |
| `sdiv udiv srem urem` | `{dividend: T, divisor: T} => T` | no | same names |
| `shl lshr ashr` | `{value: T, amount: T} => T` | no | same names |
| `eq ne` | `{a: T, b: T} => i1` | yes | `icmp eq/ne` |
| `slt sle sgt sge ult ule ugt uge` | `{lhs: T, rhs: T} => i1` | no | `icmp` signed / unsigned |
| `zext sext` | `{value: F} => T`, `T` wider than `F` | yes | `zext`, `sext` |
| `trunc` | `{value: F} => T`, `T` narrower than `F` | yes | `trunc` |

There are no same-width conversions.

### Naming

- Same-form ops: `<op>_<form>`: `add_i32`, `eq_i8`.
- Conversions name both forms, from then to: `zext_i8_i32`, `trunc_i64_i32`.
- No opcode may be named `call`, `jump`, `branch` or `return` (they'd read as BANF
  keywords); `banf_opcodes.py` asserts this.

### Monomorphic: one op per signature

There is no generic `add`; each signature is its own op (`add_i32`, `add_i64`…).

- An `OpcodeCall`'s result form is a table lookup, like a `Call`'s comes from its
  callee's signature. No width inference; conversions need no stored target form
  (`zext_i8_i32` always returns `i32`).
- Widths are strict: `$add_i32 {a = [01]:'i8', b = ...}` is an error
  (`$add_i32 expects a: i32, got i8.`). Convert explicitly with `zext_i8_i32`.
- Cost: many names. They're generated from templates, not written by hand.

### Labels fit the op

For non-commutative ops the label says the operand's role, so
`$sub_i32 {minuend = x, subtrahend = y}` can't be read the wrong way round.
Commutative ops use `a`/`b`.

Adding an opcode: [How to… › Add an opcode](#add-an-opcode).

## BANF

**BANF** (block-based ANF) is the first-order IR between oymomo and LLVM: SSA with
**block parameters instead of phi nodes**, as in MLIR and Cranelift. Classes,
`form_of`, the verifier and the printer are in
[`banf_terms.py`](../src/oymo/oymomo/banf_terms.py). It does not depend on LLVM.

```
fact: i32
  entry(n: i32):
    t0 = eq_i32 n, [00000000]:i32
    branch t0, then0(), else0(n)
  then0():
    return [01000000]:i32
  else0(n: i32):
    t1 = sub_i32 n, [01000000]:i32
    t2 = call fact(t1)
    t3 = mul_i32 n, t2
    return t3
```

### Module

```python
Module(bindings: list[Function | Signature | Data])
Function(name, return_form, blocks)       # blocks[0] is the entry block
Signature(name, params, return_form)       # imported function
Data(name, form, value=None)               # imported (None) or defined (bytes)
```

- `name` is the LLVM symbol (`@fact`, `@putchar`, `@errno`). It lives on the binding
  rather than in `(name, binding)` tuples, which is simpler to carry and print.
- `Signature` has its own `params` because it has no entry block to hold them.
- `Data` is read-only in oymomo (no assignment), but re-read on every use with
  `GetData`, since a value like `errno` can change outside the program. Defined data
  is read the same way (`module.answer`). Not named `Global`, because every binding
  becomes an LLVM global.

### Blocks

A block has params, lets, and one terminator (`return`, `jump`, `branch`).

Why basic blocks: lowering is one BANF block → one LLVM block, one let → one
instruction.

Why block params instead of phi: a join block declares what it receives, and each
jump passes it, so each edge says what flows along it.

```
then0(x: i32, z: i32):
  jump join0(x, z)
else0(y: i32, z: i32):
  jump join0(y, z)
join0(v: i32, z: i32):
  t0 = add_i32 v, z
```

The LLVM translator turns these back into phis where needed (see
[Translation › BANF to LLVM](#banf-to-llvm)).

#### Blocks are closed

A block can use only its own params and lets. A value from another block must be
passed as a jump or branch argument: in `fact`, `else0` needs `n`, so `entry` passes
it with `branch t0, then0(), else0(n)`.

- Why: each block reads on its own, with no dominance or live-in analysis. Names are
  scoped to their block, so a passed value can keep its name (`else0(n: i32)`).
- In oymomo this holds by construction: a block lambda only sees its `args`, its
  lets, and the outer binders `blocks` and `module`; built-ins are global.

#### The entry block cannot be jumped to

The entry block's params are the function's params, as in Cranelift. LLVM's entry
block can't have predecessors, and its params are the function's arguments, not
phis. A loop jumps to a separate header block:

```
entry(n: i32):
  jump loop(n)
loop(n: i32):
  ...
  jump loop(t1)
```

### Ops and their forms

A let's value is one of these ops. Forms are stored only where they can't be worked
out; `form_of(op, forms, module)` computes the rest:

| Op | oymomo source | Result form |
|---|---|---|
| `OpcodeCall` | `$add_i32 {...}` | the op's result form from `banf_opcodes.py` |
| `Call` | `module.g {...}` | the callee's `return_form` (`Function` or `Signature`) |
| `MakeStruct` | `{x = a, y = b}` | each label paired with its field atom's form |
| `GetField` | `args.p.x` | that field's form inside the struct's form |
| `GetIndex` | `args.p [01]` | the form of the field at that position, labeled or not (`Form {x: i32} has no field at index 2.`) |
| `GetData` | `module.errno` | the `Data` binding's form |

Where forms **are** stored:

| On | Why |
|---|---|
| each `Const` | the same bytes can have many forms |
| each block param | a block must declare what its jumps pass in |
| each function's and signature's return form | calls read them, recursive calls included; they come from `module` |
| each `Data` | |
| a `Let`, only if the source wrote one | otherwise `form_of` computes it; a stored `MakeStruct` form would repeat a full struct form on every line |

Ops carry no form, as in Cranelift (`v0 = iadd v1, v2`). A written let form
(`Let.form`; `Empty` when not written) replaces the op's form. The verifier and the
LLVM translator use `let_form` while walking a block: the let's written form, or
else `form_of` its op. They add it to the block's name table.

### Printer

| Prints | Example | Note |
|---|---|---|
| a let | `t0 = eq_i32 n, [00000000]:i32` | no `let` keyword, no form (unless written: `t0: i32 = ...`) |
| an opcode | `t3 = mul_i32 n, t2` | assembly style: no parens, no `$` |
| a call | `t2 = call fact(t1)` | keyword `call`, parens, commas |
| a data read | `t0 = errno` | bare name (an opcode always has operands) |
| a `GetIndex` | `y = p.1` | a digit label would need quotes (`p."1"`), so never a `GetField` |
| an unlabeled field | `{i32, i8}`, `{n, y = [01]:i8}` | value alone |
| a function form with no param | `(=> R)` | |
| a `Signature` | `putchar(c: i8): i32` | |
| imported `Data` | `errno: i32` | |
| defined `Data` | `answer: i32 = [2a000000]` | |
| a `Function` | `fact: i32` then its blocks | blank line around each function |

- Lets need no keyword: a block holds only lets plus one terminator, and every
  terminator starts with a keyword (`jump`, `branch`, `return`).
- Calls and data reads use the symbol, not `module.`.
- Bindings print in declaration order.
- Block labels are indented 2 spaces, instructions 4, so the column tells a line's
  kind. At column 0, `entry(a: i32):` would look like the signature
  `putchar(c: i8): i32`, and nothing would mark where a function ends.
- Names are quoted when needed: `"my data": i8`.

## Translation: oymomo → BANF → LLVM

### oymomo → BANF

`banf_translate.translate(term)` runs four passes. `shape(term)` runs the first three
and returns an oymomo term in BANF's shape; `convert(shaped)` runs the last.

| # | Pass | Does |
|---|---|---|
| 1 | `bruijn.resolve` | Each `Variable` becomes a `BruijnIndex`. Names stay on `Lambda.param_name`. Unbound name → error. |
| 2 | `banf_reduce.shape` | Reduces only where the term doesn't have BANF's shape yet. |
| 3 | `banf_rename.rename` | Renames binders: fixed structural names, no shadowing. |
| 4 | `banf_translate.convert` | Reads the shaped term into BANF; `TranslationError` with a source location on any mismatch. |

The golden tests approve the shaped term as `name.shaped.oymo`, next to the BANF and
LLVM output, and check that it translates to the same BANF.

#### The principle: translation only reduces

`shape` runs term reductions (beta, built-in rules such as `$fix`, projection, `if`)
until each position has BANF's shape. `convert` only reads the result. So:

- **No defaults.** An omitted form is `Empty`, never read as `void` or anything else.
  A position that needs a form rejects it ("form must be written").
- **Nothing inferred.** Every form BANF stores is written in the source, return
  forms included, and every parameter list and form is written once.
- **Unneeded forms are dropped.** A form where BANF has no slot (on the `blocks`
  binder, on a data definition) is dropped, not rejected.
- **A form is not a type.** A written form is never checked against a computed one;
  it replaces it (a let's form, a formed atom). `banf.verify` still checks arguments,
  branch conditions and returns against the forms they're *required* to have, and
  `llvm_translate` rejects a replaced form whose LLVM type differs.

A term without BANF's shape after reduction is rejected, and the source fixes it
explicitly. Background: [plan_banf_explicit.md](plan_banf_explicit.md).

#### 1. `bruijn.resolve`

Turns names into indices by counting enclosing lambdas. See
[The kernel › reduce](#reduce-one-step-at-the-root) for the one-step
reducer the next pass uses.

#### 2. `banf_reduce.shape`: reduce until each position has its shape

Each [position](#positions) wants certain constructors. The term there is reduced
until it has one, then its own positions are visited. Forms and binder kinds aren't
checked here (except `args`, through `k`); `convert` does that, so this pass needs
no context.

##### Heads

Some roots become a redex only after their **head** is reduced: in `$fix g a`,
`$fix g` must unfold to a lambda first.

| Term | Head |
|---|---|
| `{...} i` (callee already a struct) | `i` |
| `$name a`, with `name`'s rule strict | `a` |
| `f a`, otherwise (including `$fix g`) | `f` |
| `s.l` | `s` |
| `if c then ...`, which is `{e, t} c` | `c` |
| `t: F` | `t` |
| anything else | none |

- So `step` reduces an apply's callee to a struct, then the index, then the root:
  in `{a = x} ((y -> y) [00])` the index must become a byte array first.
- An argument is reduced only when the callee is a struct or a strict built-in, so
  ordinary applications stay lazy: `f ((x -> x) a)` keeps its argument.
- A strict rule reads its argument, so in `$unpack ((x -> x) {...})` the argument
  is reduced to a struct before the rule fires. `banf_reduce` reads the flag on the
  rule, so a new built-in needs no change here. `$fix` is not strict.

```
step(t) = reduce(t)        if reduce(t) is not t                        -- a step at the root
        = t with head h'   if t has a head h, and h' = whnf(h) is not h   -- else reduce the head
        = t                otherwise

whnf(t) = whnf(step(t))    if step(t) is not t
        = t                otherwise
```

`whnf` stops at every Lambda, Struct, ByteArray, BruijnIndex and Builtin, and at
stuck terms such as `$add_i32 {...}`, `args.n`, `blocks.done {...}` or
`if t0 then a else b`.

- "Reduce `t` until it is X" means take `whnf(t)`, *then* look at its constructor.
  Looking first is wrong: `{f = x -> ...}.f args.n` is already an apply, but its
  callee must be reduced before it is a call such as `$add_i32 {...}`.
- A position that already has a wanted constructor isn't reduced further, since
  `whnf` stops there. So a let-bound struct stays a `MakeStruct`.

##### Positions

As numbered in [`banf_reduce.py`](../src/oymo/oymomo/banf_reduce.py):

1. The term, until a Lambda: `module -> <body>`.
2. `<body>`, until a Struct: `{label = <func>, ...}`.
3. `<func>`, until a Lambda: `blocks -> <func_body>`.
4. `<func_body>`, until a Struct: `{label = <block>, ...}`.
5. `<block>`, until a Lambda: `args -> <block_body>`.
6. `<block_body>`, a chain of lets ending in a terminal:
   ```
   block_body := terminal | (x -> block_body) <value>      -- a let
   terminal   := [bytes]                                    -- return a constant
               | args.label                                 -- return a param
               | $i, where i < k                            -- return a let
               | blocks.label <op_arg>                      -- jump
               | {<jump>, <jump>} <atom>                    -- branch: if <atom> then ... else ...
   ```
   `k` counts the lets since the block's `args` binder, so `args` is `$k`; it tells
   `args.label` from other projections. A let isn't reduced with `whnf`, since it is
   a redex that must be kept. Repeat:
   1. For a let `(x -> rest) <value>`, take `whnf(<value>)`. If it is an op (an
      apply, a struct, or a projection other than `args.label`), keep the let, visit
      the op (7), and go on with `rest`. Otherwise beta-reduce the let and go on.
   2. Else, if `step` changes the body, go on with that. This can make a let: in
      `(x -> y -> rest) a b` the head reduces and leaves `(y -> rest') b`.
   3. Else visit the terminal's positions and stop.
7. `<value>`, a let's op: an apply's `<op_arg>` becomes a struct of atoms or a
   BruijnIndex (forwarding `args`); a struct's fields become atoms; a projection's
   struct is a head, already reduced.
8. `<jump>`, a branch arm (a field of `{e, t} c`): until `blocks.label <op_arg>`.
9. `<atom>`: until a ByteArray, `$i` with `i < k`, or `args.n`. `args` itself is not
   an atom: BANF passes a block's params one by one.

##### Consequences

- A let whose value isn't an op is beta-reduced, so helpers are inlined,
  `let t = args.n in t` becomes `args.n`, and a let-bound `if` lands in tail
  position.
- A term that can't get its shape is left as is, for `convert` to report. This pass
  has no errors except running out of fuel.
- **Fuel**: each step costs one unit, out of 10,000. A term that keeps reducing,
  such as `$fix (self -> self)`, fails with "ran out of reduction steps".
- Nothing is flattened: a nested call stays nested and is an error, since
  flattening would mean inventing names.

#### 3. `banf_rename.rename`: fixed names and no shadowing

**Structural binders get fixed names.** Positions 1, 3 and 5 are renamed so every
shaped program reads `module -> {main = blocks -> {entry = args -> ...}}`.

- `convert` checks each position by name; a wrong name means a wrong shape.
- On any path from the root the three names appear once each, so they never clash.
- A position `banf_reduce` left without its shape isn't structural: its binder
  follows the let rule below, and `convert` reports the shape error.
- The fixed names don't reach BANF: `blocks.label` becomes a jump target and
  `args.n` becomes `banf.Var('n')`.

**Other binders keep their names unless they clash.** A let keeps its name `x`
unless `x` is *visible*: the name of an enclosing binder (after renaming, so the
three fixed names count) or a param label of its block. Then it becomes `x_L`, else
`x__L`, and so on, where `L` is its level (number of enclosing binders; a block's
first let is level 3).

| Lets | Become |
|---|---|
| `let t = ... in let t = ... in let t = ... in t` | `t, t_4, t_5` |
| two lets `n` with `args: {n = 'i8'}` | `n_3, n_4` (param labels become BANF `Var`s) |
| user's `t_4` after a renamed `t_4` | `t_4_5` |
| `t, t_5, t` | `t, t_5, t__5` |
| a let named `args` | `args_3` |
| a let named `prim` | `prim` |

- Labels (struct, field, block, function, param) are never renamed, and only param
  labels count as visible. The others are separate namespaces in oymomo and BANF
  (`Jump.target`, `Call.function`, `GetData.name` are plain strings, not `Var`s), so
  a let `n` used as `{n = n}` keeps its name.
- Visible names are per path, so sibling blocks can both have a `t` (LLVM adds a
  `.1` suffix, which is fine).
- Idempotent: a second run changes nothing.
- Linear: one set, add on the way down, remove on the way up.

Rejected alternatives: [Design decisions](#renaming).

#### 4. `convert`: read the shaped term

##### Binders are found by index

Inside a block body with `k` lets so far, the binders above are always, inside out:
the lets (`$0` … `$k-1`), then `args` (`$k`), `blocks` (`$k+1`), `module` (`$k+2`).
So `convert` classifies each `BruijnIndex` by arithmetic and keeps no names of its
own. A let reference becomes a `banf.Var` named after the BANF let already built.

##### What the shape is

- **Let**: `let x = op in rest`, i.e. `(x -> rest) (op)`. With no form, the let's
  form is the op's. A written form must be a literal and **replaces** the op's form
  unchecked: `let t0: 'i32' = $eq_i32 {...} in t0` gives `t0` the form `i32`
  (`eq_i32` gives `i1`). BANF prints `t0: i32 = eq_i32 ...`; LLVM translation then
  rejects it, since the LLVM types differ.
- **Atom**: a byte array with a literal form (`[01]: 'i8'`), a let name, or
  `args.label`. Any atom can be given a literal form, which replaces its own
  (`args.n: 'i32'`, `t: 'i8'`). `let m: 'i32' = args.n in m` isn't a BANF let (its
  value isn't an op), so it's beta-reduced to `args.n: 'i32'`.
- **Op**, only as a let's value:

  | Source | BANF op |
  |---|---|
  | `$opcode {...}` | `OpcodeCall` |
  | `module.g {...}` (imported or defined) | `Call` |
  | struct literal of atoms | `MakeStruct` |
  | projection on an atom: `args.p.x` | `GetField` |
  | atom applied to an index: `args.p [01]` | `GetIndex` |
  | `module.errno` | `GetData` |

- **`GetIndex`** `s i`: `s` is an atom with a struct form (a let-bound struct or a
  param such as `args.p`). `i` is read by `bruijn.index_value`: any byte array
  literal, unsigned little-endian, form ignored (`[01]`, `[0100]`, `[01]: 'i8'` are
  all 1). It's reduced first like any op argument, so `args.p ((i -> i) [01])` and
  `let i = [01] in args.p i` work. A run-time value (`args.n`, a let bound to an op)
  or `''` is an error ("An index must be a byte array literal, such as [01]."),
  since LLVM's `extractvalue` needs a constant. Past the last field: "Form {i32, i8}
  has no field at index 2.". Binders are read only by label, so `args [00]` is an
  error.
- **Terminators**, only in tail position: `f.label {...}` (jump);
  `if c then f.a {...} else f.b {...}`, which is `{f.b {...}, f.a {...}} c` (branch,
  both arms jumps, labels ignored); an atom (return).

##### Labels name params, declarations and blocks

BANF reads `module`, `blocks` and `args` only by label, so every field needs a label
in: the module form, a signature's param form, the module body, a definition's
blocks, the top level of a block's param form, and the argument struct of a call,
jump or opcode ("The module form needs a label on every field.").

Elsewhere (a value struct, a nested data form such as `args: {p = {'i32', 'i8'}}`) a
field may be unlabeled, and several unlabeled fields aren't duplicates. BANF prints
an unlabeled field alone (`{i32, i8}`), and LLVM names its `insertvalue` by index
(`%"q.0"`).

##### Operands must be atoms

`$add_i32 {a = $add_i32 {...}, b = ...}` is an error; bind the inner call with a let
first. Allowing it would mean flattening, i.e. inventing temporary names.

##### An op in tail position must be bound first

Write `args:{} -> let t0 = module.putchar {c = [41]:'i8'} in t0`, not
`args:{} -> module.putchar {c = [41]:'i8'}`. A BANF `Return` takes an atom, and the
explicit `let t0` keeps every name in the source.

##### `if` only in tail position, jumping to two different blocks

`if c then [01]:'i8' else f.b {}` is an error. A let-bound `if` is substituted, so
`let t = if c then f.a {} else f.b {} in t` is fine, but an `if` that ends up as an
operand is an error. All of this holds for `{e, t} c`, which is the same term.
- Only two fields: `{f.a {}, f.b {}, f.c {}} c` is "A branch needs two fields, {else,
  then}.". An N-way switch is a later plan.
- A BANF `Branch` is a terminator with two targets. An `if` whose value is used
  needs a join block, which the source writes explicitly.
- `if c then f.a {} else f.a {}` is rejected: `a` would get two edges from the same
  block, and an LLVM phi can't tell them apart.

##### Binders can't be used as values

`blocks`, `args` and `module` alone are errors ("'args' cannot be used as a
value."; the message uses the fixed name), except `args` forwarded as a whole call
or jump argument. So are `module.g` and `$add_i8` without an argument
("$add_i8 must be applied."). They have no runtime value.

### BANF to LLVM

[`llvm_translate.py`](../src/oymo/oymomo/llvm_translate.py) maps BANF one-to-one onto
LLVM:

```llvm
define i32 @fact(i32 %n) {
entry:
  %t0 = icmp eq i32 %n, 0
  br i1 %t0, label %then0, label %else0
then0:
  ret i32 1
else0:
  %t1 = sub i32 %n, 1
  %t2 = call i32 @fact(i32 %t1)
  %t3 = mul i32 %n, %t2
  ret i32 %t3
}
```

| BANF | LLVM |
|---|---|
| form `iN` | `iN` |
| struct form | literal struct type, fields in order (other form names rejected) |
| `[2a000000]:i32` | `i32 42` (little-endian bytes → number) |
| block param, one predecessor | the value that predecessor passes (no phi) |
| block param, several predecessors | `phi`, one incoming value per edge: `%v = phi i32 [%x, %a], [0, %b]` |
| `GetData` | `load` from the global |
| `GetField`, `GetIndex` | `extractvalue` (`args.p [00]` gives the same IR as `args.p.x`) |
| `MakeStruct` | one `insertvalue` per field, named `%q.x` after the let and field |
| defined `Data` | writable `global` with initializer: `@answer = global i32 42` |
| imported `Data` | `external global` |

- Every symbol is declared first, so functions can call each other in any order.
- Unreachable blocks are not emitted, so phis only list blocks that exist.
- Value names are the BANF let names (`%t0`), so IR is easy to match against BANF.
- Constants: an `iN` constant needs `(N + 7) // 8` bytes, so `i1` is one byte
  holding 0 or 1. LLVM stores the number in the data layout's byte order, so a
  big-endian target (`E-...`) needs no swap. Struct constants aren't supported yet.
- Data initializers follow the constant rules ("A i32 constant needs 4 bytes.");
  struct data forms are rejected for now. Constness will come later with the data's
  form.
- **No conversions.** A formed name or a let with a written form is used as-is if
  its LLVM type equals the original (e.g. a struct form with other labels and the
  same field types). Otherwise it's rejected: "'n' is formed as i32, but its LLVM
  type is i8.", "Let 't0' is formed as i32, but its op gives i1.". No `bitcast`, no
  widening, no narrowing.

## Error messages

What common error messages mean and how to fix them. Messages are grouped by the
stage that raises them. `<…>` marks a part that varies.

Every translation error carries a source location. Search the source for the
message text to find where it's raised.

### Names and resolution (`bruijn.py`)

| Message | Cause | Fix |
|---|---|---|
| `Unknown name '<x>'.` | A variable that no lambda or let binds. | Bind it, or check spelling. Built-ins need `$` (`$add_i32`). |

### Shaping (`banf_reduce.py`)

| Message | Cause | Fix |
|---|---|---|
| `Did not reach BANF shape: ran out of reduction steps.` | More than 10,000 steps, usually a term that never stops reducing, e.g. `$fix (self -> self)`. | Make sure recursion goes through `module.f` calls, not `$fix` loops. See [Translation](#consequences). |

### Program shape (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `Expected a program of the shape module: {...} -> {...}.` | The top level isn't a lambda around a struct. | See [Programs](#the-shape-of-a-program). |
| `The module binder needs a struct form, such as module: {}.` | `module -> {...}` without a form. | Declare every symbol: `module: {main = => 'i32'} -> ...`. |
| `'<f>' is defined but not declared.` | A body field with no `module` declaration. | Add `f = => R` (function) or `f = 'iN'` (data) to the module form. |
| `'<f>' declares no params, so it must be defined.` | Declared `=> R` but missing from the body. | Define it, or declare it with params to import it. |
| `'<f>' declares its params; a definition takes them from its entry block.` | Declared `{...} => R` and also defined. | Declare a defined function as `=> R`; params go on its entry block. |
| `'<x>' is declared as data, so its definition must be a byte array.` | A data declaration defined as something else. | Define it as bytes: `answer = [2a000000]`. |
| `<what> needs a label on every field.` | An unlabeled field where a label names something (module form, blocks, params, call/jump/opcode arguments). | Add labels. See [Translation](#labels-name-params-declarations-and-blocks). |
| `<what>: function forms nested inside other forms are not supported.` | A function form inside a data form, or as a param/result. | Not supported yet. See [Programs](#nested-function-forms-are-rejected-for-now). |
| `<what>: a function form needs a struct form as its param.` | e.g. `g = 'i8' => 'i32'`. | Use `{c = 'i8'} => 'i32'`. |

### Forms (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `<what>: form must be written.` / `Byte array: form must be written.` | A form is needed but omitted (`Empty`); nothing infers one. | Write it: `[01]: 'i8'`, `args: {n = 'i32'}`. See [The kernel](#omitted-forms-are-empty). |
| `<what>: form must be a literal, got <form>.` | A form that didn't reduce to a named form or struct of them. | Use a literal like `'i32'` or `{x = 'i32'}`, or make sure it reduces to one. |

### Block bodies (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `Expected an atom: a byte array, a let name, or args.label.` | An operand that is an op, e.g. a nested call. | Bind it first: `let t = $add_i32 {...} in ... t ...`. See [Translation](#operands-must-be-atoms). |
| `A let's value must be an op, not an atom.` | A let in BANF position whose value is an atom. | Use the atom directly. |
| `An if must be in tail position.` | An `if` used as a value. | Branch to blocks and join explicitly. See [Translation](#if-only-in-tail-position-jumping-to-two-different-blocks). |
| `Both branches of an if jump to the same block.` | `if c then f.a {} else f.a {}`. | Use two blocks (LLVM phis can't tell the edges apart). |
| `A jump must be in tail position.` | `f.label {...}` used as a value. | Put the jump last. |
| `Cannot jump to the entry block.` | `f.entry {...}`. | Jump to a separate loop header. See [BANF](#the-entry-block-cannot-be-jumped-to). |
| `'<args>' cannot be used as a value.` | `blocks`, `args` or `module` used alone. | Use `args.n`, `module.f {...}`, `blocks.b {...}`; `args` may only be forwarded whole as a call/jump argument. |
| `module.<g> must be applied.` | A function symbol used without arguments. | Call it: `module.g {...}`. |
| `module.<x> is data, so it cannot be applied.` | `module.errno {}`. | Read data without an argument: `module.errno`. |
| `'<x>' is not declared.` | `module.x` with no declaration. | Declare it in the module form. |
| `Unknown block '<b>'.` / `Block has no param '<n>'.` | A jump to a missing block, or `args.n` for a missing param. | Check the block's name and param form. |
| `The argument to <what> must be a struct literal or the block param.` | e.g. `module.f x`. | Pass `{n = x}` or forward `args`. |
| `<what> takes {a, b}, got {b, a}.` | Argument labels don't match the callee's params in order. | Match labels and order. |
| `An index must be a byte array literal, such as [01].` | `args.p i` with a run-time `i`. | Use a literal; LLVM's `extractvalue` needs a constant. |
| `Duplicate …` (`declaration`, `definition`, `block`, `name`, `field labels`) | Two items with one name where names must be unique. | Rename one. |

### Built-ins

| Message | Cause | Fix |
|---|---|---|
| `$fix must be applied.` / `$<name> must be applied.` | A built-in used without an argument. | Apply it: `$add_i8 {...}`. |
| `$<name> has no opcode, so it must reduce away: its argument must reduce to <needs>.` | A kernel-only built-in whose rule didn't fire. | Make its argument reduce to what the rule needs (e.g. a struct). |
| `Unknown built-in '$<name>'.` | In neither `BUILTIN_RULES` nor `OPCODES`. | Check spelling against [Opcodes](#opcodes). |
| `Target has no implementation of $<name>.` | The LLVM `Target.opcodes` lacks the op. | Add it to `llvm_opcodes.py`. |

### BANF verifier (`banf_terms.py`)

| Message | Cause | Fix |
|---|---|---|
| `$add_i32 expects a: i32, got i8.` (`<what> expects <label>: <form>, got <form>.`) | Argument form doesn't match. Widths are strict. | Convert explicitly, e.g. `$zext_i8_i32`. |
| `<what> takes <n> arguments, got <m>.` | Wrong argument count. | Match the callee's params. |
| `Branch condition must be i1, got <form>.` | `if` on a non-`i1` value. | Compare first, e.g. `$ne_i32`. |
| `Function '<f>' returns <form>, got <form>.` | A return value's form differs from the declared return form. | Fix the value's form or the declaration. |
| `Form <form> has no field at index <i>.` | `GetIndex` past the last field. | Use a smaller index. |

### LLVM (`llvm_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `'<n>' is formed as i32, but its LLVM type is i8.` | A formed atom whose form maps to a different LLVM type. | Forms don't convert; use an opcode such as `$zext_i8_i32`. |
| `Let '<t0>' is formed as i32, but its op gives i1.` | A let's written form differs in LLVM type from its op. | Remove the form, or convert explicitly. |
| `A i32 constant needs 4 bytes.` | Wrong byte count for an `iN` constant (`(N + 7) // 8` bytes). | Write the right number of bytes: `[2a000000]`. |
| `Constant does not fit in <form>.` | e.g. an `i1` byte that isn't `00` or `01`. | Fix the bytes. |
| `Only integer constants are supported, got <form>.` | A struct constant. | Not supported yet. |

## How to…

### Run the checks

From `oymo/`:

```bash
hatch run full-check          # checks and tests, the pre-commit check
hatch check --fix             # lint, format, and type check
hatch test                    # all tests
hatch test tests/hello_test.py::test_hello_default   # a single test
```

### Try a program

Run a snippet through the whole pipeline (this is what the golden test does):

```python
import llvmlite.binding as llvm
from oymo.oymomo import banf_terms, banf_translate, grammar, llvm_opcodes, llvm_translate, printer

target = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=llvm_opcodes.DEFAULT_OPCODES)
shaped = banf_translate.shape(grammar.parse(source))
print(printer.show(shaped, pretty=True, name_indices=True))   # shaped oymomo
module = banf_translate.convert(shaped)
print(banf_terms.show(module))                                 # BANF
ir = str(llvm_translate.translate(module, target))
llvm.parse_assembly(ir).verify()
print(ir)                                                      # LLVM IR
```

Run it with `hatch run python your_script.py`. If it fails, look the message up in
[Error messages](#error-messages).

### Add a golden test

1. Write `tests/goldens/<name>.oymo`, starting with the header line
   `language oymomo`.
2. Add `run_golden_test('<name>')` to `test_goldens` in
   [`golden_test.py`](../tests/golden_test.py).
3. Run `hatch test tests/golden_test.py`. The first run writes
   `<name>.shaped.oymo.received`, `<name>.banf.received` and `<name>.ll.received`
   (approvaltests). Review them and rename them to drop `.received` to approve.

The test also rewrites the `.oymo` source into its pretty-printed form (checking it
gives the same BANF), and checks the shaped output compiles to the same BANF.

### Add an opcode

1. In [`banf_opcodes.py`](../src/oymo/oymomo/banf_opcodes.py), add the template to
   `_generate()` (same-form ops with `_same_form`, conversions with `_conversions`).
   Pick labels that say each operand's role (see
   [Opcodes](#labels-fit-the-op)).
2. In [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py), map the template to
   its llvmlite builder method in `_BINARY`, `_COMPARE` or `_CONVERT`.
3. Don't name it `call`, `jump`, `branch` or `return`.
4. Add tests in `banf_opcodes_test.py` and `llvm_translate_test.py`; a test checks
   both tables have the same names.
5. Update [Opcodes](#opcodes).

### Add a built-in reduction rule

1. In [`bruijn.py`](../src/oymo/oymomo/bruijn.py), write
   `rule(call, arg) -> Term | None` (return `None` when it doesn't fire yet) and add
   `BuiltinRule(name, strict, needs, rule)` to `BUILTIN_RULES`.
   - `strict=True` if the rule reads its argument (`banf_reduce` will reduce the
     argument first); `needs` names what it must reduce to (`'a struct'`), for the
     error message.
2. Nothing else needs to change: the parser accepts any `$name`, `banf_reduce` reads
   `strict`, and `convert` rejects a leftover kernel-only built-in with a message
   built from `needs`.
3. Add tests in `bruijn_test.py` and `banf_reduce_test.py`; update
   [The kernel › Built-ins](#built-ins).

### Write a design change

Larger changes are written as a plan first: `docs/plan_<name>.md`, carried out in
steps of one commit each, and listed in [plans.md](plans.md) (open until every step
is done, then closed).

### Update the notes when a plan lands

Each step updates the section of `docs/notes.md` it changes:

| Change to | Update |
|---|---|
| syntax, precedence, printer | [oymomo syntax](#oymomo-syntax) |
| forms, built-ins, `reduce` | [The kernel](#the-kernel-forms-built-ins-reduction) |
| program shape, `module`, declarations | [Programs](#programs) |
| opcodes | [Opcodes](#opcodes) |
| BANF classes, ops, printer | [BANF](#banf) |
| shaping, renaming, `convert`, LLVM | [Translation](#translation-oymomo--banf--llvm) |
| a new or changed error message | [Error messages](#error-messages) |
| the reason for a choice, rejected alternatives | [Design decisions](#design-decisions) |
| a new word | [Glossary](#glossary) |

## Design decisions

Why things are the way they are, and what was rejected. The topic files state the
rules; this file keeps the reasoning. Detailed history of larger changes is in the
`plan_*.md` files listed in [plans.md](plans.md).

### Type, Form, Layout are three words

The kernel (oymomo) and BANF only know forms. Types belong to higher layers, layouts
to the backend (LLVM). Keeping the words apart stops a backend detail like "i32 is
4-byte aligned" from leaking into the kernel, where `[2a000000]: 'i32'` only says
"these bytes, read as the form i32". → [Overview](#type-form-layout)

### BANF does not depend on LLVM

How each opcode becomes LLVM instructions is a backend detail, so BANF only names
the opcode (`add_i32`) and the `Target` supplies the implementation. `Target` has no
`byte_order` field because `data_layout` already says it, and two sources could
disagree. → [Overview](#where-the-code-lives)

### Flat files with prefixes

The stages are small, and a prefix (`banf_`, `llvm_`) shows the stage as clearly as a
subpackage, without extra `__init__.py` files and import paths.

### Brackets have one job each

`{}` structs, `()` grouping, `[]` bytes, `''` text bytes, `""` names. The parser
never has to guess. Structs moved from the earlier plan of `[]` to `{}` (as in C and
Rust), which freed `[]` for byte arrays. → [oymomo syntax](#brackets-one-job-each)

### Struct, not record

Fields keep their declaration order, and the order sets the layout:
`{x = 'i32', y = 'i8'}` is `{i32, i8}` in LLVM, `{y = 'i8', x = 'i32'}` is
`{i8, i32}`. "Struct" says that; "record" suggests an unordered set of labels.
→ [oymomo syntax](#structs)

### The name `Project`

`s.x` is the term `Project`. It is a one-word verb like `Apply`, and it is TAPL's
name for `t.l` on records (projection, E-ProjRcd); the reducer already called its
step `project`.

History: we first chose `Select`, then `FieldAccess` (it pairs with the `Field`
class and is what C, Rust and Java call `s.x`), and rejected `Project` as
type-theory jargon. We came back to it because this is a lambda calculus, and every
other term is named after its operation, not its look.

Rejected:
- `Select`: unclear.
- `FieldAccess`: names the syntax and breaks the verb pattern.
- `Access`, `Read`: sound like memory operations next to LLVM.
- `Field`: taken by the `Field` class.
- `Member`: C++ flavored, suggests methods.
- `Get`: reads like a function call.
- `Dot`: names the syntax, not the meaning.
- `Projection`: a noun among verbs.
- `Pick`, `Take`, `Pluck`, `Extract`, `Lookup`, `Focus`.

`Project` stays its own term next to struct apply (`s [00]`), because BANF's shapes
and the printer match on it. Struct apply needed no new syntax or term: `s i` is
already an `Apply`. → [oymomo syntax](#projection-and-struct-apply),
[plan_struct_apply.md](plan_struct_apply.md)

### The lambda arrow

`->` is easy to type on any keyboard; `→` reads like the math notation. Both are
accepted. The printer prints `→`.

### Forms are terms

One syntax and one set of terms for values and forms, so later stages can compute
forms with the same machinery as values. → [The kernel](#forms-are-terms),
[plan_term_as_form.md](plan_term_as_form.md)

### Omitted forms are `Empty`, with no default

Quick sketches stay short, and `Empty` has no default meaning: each position says
what it means there or rejects it. It used to mean `void`; that was dropped so that
translation never fills in a value the source didn't write.
→ [The kernel](#omitted-forms-are-empty),
[plan_banf_explicit.md](plan_banf_explicit.md)

### `Formed` binds tighter than application

The rule is "values bind tighter than things that reduce". `Formed` and
`FunctionForm` never reduce, so `:` and `=>` bind tighter than application, and
`.` tighter still since `module.T` and `args.n` read as paths.

Rejected: `:` below application, as in Haskell, OCaml and Lean
(`f a: g b` = `(f a): (g b)`). It made `:` the only value operator looser than
application. → [oymomo syntax](#precedence),
[plan_annotation.md](plan_annotation.md)

### A byte array is only its bytes

`[01]: 'i8'` is `Formed(ByteArray([01]), 'i8')`, not a literal with a built-in form.
So every `:` not on a binder is one term with one meaning, and beta reduction alone
gives a dynamic form. The same bytes can have many forms (`[01000000]` could be
`'i32'` 1 or `{a = 'i16', b = 'i16'}`).

### Byte arrays are bracketed hex

The kernel has only byte arrays, so literals are written as bytes, not numbers.
`[]` was freed when structs took `{}`, and the brackets bound the literal, so no
prefix or quotes are needed.

Rejected:
- a prefix sigil (`#2a000000`, also `%`, `$`, `@`): needed `_` separators and a `_`
  line continuation;
- `0x...`: reads as an integer and hides the byte order;
- backticks: look like quoting;
- juxtaposing literals: juxtaposition is already application.

### Byte arrays are always little-endian

`[2a000000]: 'i32'` is 42 on every target.
- Fixed, not a default: oymomo has no integer literals, so the byte order is what
  gives a literal its number. With an overridable default, one source would mean
  two numbers. Same idea as WebAssembly memory and the `.bc` encoding: the encoding
  is fixed; the machine's byte order is a target detail.
- An evaluator (beta reduction plus opcodes) can run `add_i32` without a target and
  agree with compiled code, so constant folding is safe.
- A big-endian target still gets big-endian bytes in memory: the LLVM translator
  emits the number (`i32 42`) and LLVM lays it out per `data_layout`.
- Cost, later: once opcodes can reinterpret memory (store an `i32`, read bytes), a
  big-endian target sees bytes in a different order than the literal. Then either
  byte-swap loads and stores (as WebAssembly does) or call those opcodes
  target-dependent.

### Text byte arrays

`'` was unused, and `"` is taken by quoted names. No escapes, and `\` is kept out of
the allowed characters to leave room for escapes later.

The printer uses `'...'` only for a byte array with no form, all text bytes, at most
128 bytes. A written form (`[41]: 'i8'`) usually means a number, so hex stays; a
long blob reads better as grouped hex. The limit is fixed, not `width`, so output
doesn't depend on layout settings.

### Quoted names

LLVM does the same (`@main` vs `@"foo bar"`), so kernel names map directly to
symbols, including mangled names from higher-level languages. SQL also uses `"..."`.
Plain identifiers stay ASCII, which avoids Unicode identifier rules and confusable
characters.

Cost: `"` is not available for string literals; the kernel has none.
Rejected: Zig-style `@"..."`, only worth it if strings come.

### `$` for built-ins and indices

`$` marks a reference that no user name binds: `$0` by position, `$add_i32` by the
kernel. User names are always written bare. `#` stays unused (comments kept `//`
after byte arrays moved to `[]`).

### `let` is sugar

No new term: the parser builds `Apply(Lambda(x, body), e)`. In the applied-lambda
form `(t0 -> rest) (op)`, the value comes after the whole rest of the block, far
from its name; with `let`, a chain reads top to bottom, as BANF does.

### Function forms are their own term

`FunctionForm(param, result)` used to be a tagged struct
`{tag = ' => ', param = P, result = R}`. Then every consumer had to tell it from a
plain struct (shape, field order and tag checks), a hand-written struct could turn
into a function form by accident, and BANF output and errors showed the encoding.
Now a struct is always a struct.

Rejected: a tag member on `Struct` (nominal typing; maybe later), and `Lambda` as a
Π type (keeps `Lambda` free for form constructors). Named `FunctionForm`, not
`Arrow`: it names the meaning and leaves room for a separate function type.

Why `=>` and not `->`: a different arrow tells a form from a term at a glance, and a
binder's form safely ends at the first `->`.

### The printer lives in `printer.py`

Not in the tests, so any stage can print terms. Compact mode keeps tests short and
reading like source; pretty mode round-trips, so goldens are valid source.

### Built-ins

`$add_i32` is a global constant, not a name in `module` and not a binder.
- **Not in `module`**: machine instructions and symbols are different things.
  `$add_i32` never becomes an LLVM symbol, while every `module` entry does (`@putchar`,
  `@fact`). BANF keeps the split: `OpcodeCall` vs `Call`.
- **Not a binder**: a binder's index depends on depth (the program used to start
  with `prim ->`, and `prim` was `$3` under three lambdas), so `reduce`, which sees
  only the term, couldn't recognize `prim.fix`. A `Builtin` is the same at any depth.
- **Separate constants**, not fields of one global struct: there is no `$` value to
  project from, apply or unpack.
- **`fix` is a built-in, not its own term**: a new kernel built-in is one table entry,
  instead of a term, a grammar rule, a reserved word and cases in five modules.
- **Kernel-only comes from the tables**: a rule and no opcode, with no flag to keep
  in sync. Each built-in's `needs` gives its own error message.

→ [The kernel](#built-ins), [plan_builtin.md](plan_builtin.md)

### One `module` binder

One binder declares every symbol, imported or defined, instead of `decls` for
imports and `defs` for definitions. With two:
- a defined function's return form had nowhere to be written, so it was inferred;
- calls went through `decls.f` or `defs.f` depending on where `f` lived;
- a name in both was an extra error.

With one, the form lists every symbol with its return form, and the declaration's
shape says which are imported.

Rejected: an empty byte array as a "no body" sentinel for imports. It needs a magic
value; the declaration's shape says the same thing.

Not done: cross-module calls by name. Every external symbol is declared in `module`,
so a module lists everything it needs from outside, and the linker resolves it.
→ [Programs](#module-declares-every-symbol)

### Functions are structs of blocks

Plain oymomo (lambdas, structs, application), so no new syntax for blocks and jumps,
and every name in the BANF output comes from the source.

### One argument, always a struct

The kernel stays a plain one-argument lambda calculus, and labels name the arguments
at every call site (`{minuend = x, subtrahend = y}`), so argument order can't be
mixed up silently. The struct is expanded one level, in oymomo → BANF, so BANF stays
LLVM-shaped and BANF → LLVM has no expansion of its own. A deeper expansion would
invent names like `p.x`, and LLVM passes struct values anyway.

### Return forms are declared, not inferred

Written once, where the symbol is declared; nothing is computed. Inference had to
iterate over the whole module to a fixed point, and a function with no base case had
no return form at all.

### Monomorphic opcodes

A result form is a table lookup; nothing needs width inference; conversions need no
stored target form. Cost: many names, generated from templates. Labels that name the
operand's role make non-commutative ops impossible to read backwards.
→ [Opcodes](#opcodes)

### BANF

- **Basic blocks**: one BANF block → one LLVM block, one let → one instruction.
- **Block params instead of phi**: each edge says what flows along it.
- **Closed blocks**: no dominance or live-in analysis to know what's in scope.
- **Entry block can't be jumped to**: LLVM's entry block can't have predecessors.
- **Forms only where needed**: ops carry no form, as in Cranelift; a stored
  `MakeStruct` form would repeat a full struct form on every line.
- **`name` on the binding**, not in `(name, binding)` tuples: simpler to carry and
  print.
- **Printer**: no `let` keyword (every terminator starts with a keyword), assembly
  style opcodes, `call` with parens so it doesn't read like oymomo application,
  indentation instead of braces.
→ [BANF](#banf)

### Translation only reduces

No defaults, nothing inferred, unneeded forms dropped, a written form replaces a
computed one. A term not in shape is rejected, and the source fixes it explicitly,
so every name and form in BANF comes from the source.
→ [Translation](#the-principle-translation-only-reduces),
[plan_banf_explicit.md](plan_banf_explicit.md)

Consequences:
- **Operands must be atoms**: allowing nested calls means flattening into lets,
  which means inventing temporary names. That is normalization.
- **A tail op must be bound first**: a BANF `Return` takes an atom; accepting a tail
  op would make the translator invent a name.
- **`if` only in tail position**: a BANF `Branch` is a terminator; an `if` whose
  value is used needs a join block, which the source writes explicitly. Two
  different targets because an LLVM phi can't tell two edges from one block apart.
- **Binders aren't values**: they have no runtime value; `module` is not a struct
  anything could build.

### Renaming

Structural binders get fixed names (`module`, `blocks`, `args`) so `convert` can
check shape by name. Other binders keep their name unless it's visible, then get a
level suffix.

Rejected:
- one set per function, to avoid LLVM's `.1`: renames lets that clash only with a
  sibling block, and LLVM names don't matter;
- checking every label: they are separate namespaces, and collecting them needs an
  extra pass;
- renaming params: param labels appear in the block's form, in `args.n` and in every
  jump's `{n = ...}`, so renaming means rewriting labels in many places;
- `_<level>_<original>` for every binder: unique without a set, but renames every
  let, even ones that clash with nothing;
- `name$level` (`n$3`): needs quotes, and `$` now starts a BruijnIndex or Builtin.

→ [Translation](#3-banf_renamerename-fixed-names-and-no-shadowing)

### LLVM translation converts nothing

A formed name or let with a written form is used as-is only if its LLVM type
matches; otherwise it's rejected. No `bitcast`, no widening, no narrowing, because a
form is not a type and conversions are explicit opcodes.

## Glossary

Words used across the docs, in alphabetical order. Code names are in `code`.

| Word | Meaning | More |
|---|---|---|
| **apply** | `f a`: a function applied to one argument. `Apply` term. | [oymomo syntax](#apply) |
| **args** | Fixed name of a block's param binder after renaming; `args.n` is the param `n`. | [Programs](#functions-are-structs-of-blocks) |
| **atom** | A BANF operand: a constant (`[01]: 'i8'`), a let name, or `args.label`, optionally with a form. | [Translation](#what-the-shape-is) |
| **BANF** | *Block-based ANF*. The first-order IR between oymomo and LLVM: SSA with block params instead of phi nodes. | [BANF](#banf) |
| **beta** | The reduction `(x -> body) e` → `body` with `e` put in for `x`. | [The kernel](#reduce-one-step-at-the-root) |
| **binder** | Anything that introduces a name: a lambda param or a let. | |
| **block** | A BANF basic block: params, lets, one terminator. In oymomo, a lambda `args: {...} -> ...` in a function's struct. | [BANF](#blocks) |
| **blocks** | Fixed name of a function's self-binder after renaming; `blocks.then0 {}` jumps to block `then0`. | [Programs](#functions-are-structs-of-blocks) |
| **BruijnIndex** | A variable written by position, `$0` = nearest binder. `bruijn.resolve` turns names into these. | [oymomo syntax](#builtins-and-indices-name-and-0) |
| **built-in** | A global constant written `$name` (`$add_i32`, `$fix`). Has a reduction rule, an opcode, or both. | [The kernel](#built-ins) |
| **byte array** | The only literal: `[2a000000]` or `'text'`. Has no form unless one is written. | [oymomo syntax](#byte-arrays) |
| **convert** | Last pass of oymomo → BANF: reads a shaped term into BANF. Never reduces. | [Translation](#4-convert-read-the-shaped-term) |
| **Empty** | `terms.Empty`: a form that was *not written*. Not void, not a default. | [The kernel](#omitted-forms-are-empty) |
| **form** | The logical structure of a value: `'i32'`, `{x = 'i32'}`, `{c = 'i8'} => 'i32'`. Not a type; never checked. | [The kernel](#forms) |
| **Formed** | The term `e: F`, "`e` formed as `F`". | [The kernel](#formed-any-term-with-a-form) |
| **function form** | `P => R`, the form of a function. `FunctionForm` term. | [oymomo syntax](#function-forms) |
| **golden test** | `tests/goldens/name.oymo` compiled and compared to approved `.shaped.oymo`, `.banf` and `.ll` files. | [How to…](#add-a-golden-test) |
| **head** | The part of a term that must reduce before the term can: an apply's callee, a projection's struct, an `if`'s condition… | [Translation](#heads) |
| **kernel-only** | A built-in with a reduction rule but no opcode (`$fix`). Must reduce away before BANF. | [The kernel](#built-ins) |
| **label** | A struct field's name. Optional (`''` = none), may repeat. | [oymomo syntax](#structs) |
| **layout** | The physical memory representation (`{ i32, i32 }` in LLVM). Belongs to the backend. | [Overview](#type-form-layout) |
| **let** | `let x = e in body`, sugar for `(x -> body) e`. In BANF, one instruction `x = op`. | [oymomo syntax](#let) |
| **module** | The program's outer binder; its form declares every symbol. `module.fact {...}` calls a function. | [Programs](#module-declares-every-symbol) |
| **op** | A BANF let's value: `OpcodeCall`, `Call`, `MakeStruct`, `GetField`, `GetIndex`, `GetData`. | [BANF](#ops-and-their-forms) |
| **opcode** | A built-in with machine code (`add_i32`). Listed in `banf_opcodes.OPCODES`. | [Opcodes](#opcodes) |
| **oymomo** | The kernel lambda-calculus language. | [oymomo syntax](#oymomo-syntax) |
| **position** | A place in the program that wants a certain shape (a lambda, a struct, an atom…). | [Translation](#positions) |
| **project** | `s.x`: pick a field by label. `Project` term. | [oymomo syntax](#projection-and-struct-apply) |
| **redex** | A term that can take a reduction step at its root. | [The kernel](#reduce-one-step-at-the-root) |
| **shape / shaped term** | An oymomo term reduced until every position looks like BANF. Output of `banf_translate.shape`. | [Translation](#translation-oymomo--banf--llvm) |
| **struct** | `{x = e, y = e}`: ordered fields. Also used as struct forms. | [oymomo syntax](#structs) |
| **struct apply** | `s [01]`: pick a field by position. | [oymomo syntax](#projection-and-struct-apply) |
| **symbol** | An LLVM global (`@fact`, `@putchar`, `@errno`). One per `module` declaration. | [Programs](#symbols) |
| **terminator** | The last instruction of a block: `return`, `jump`, `branch`. | [BANF](#blocks) |
| **type** | Program-level meaning. Belongs to higher layers; the kernel has none. | [Overview](#type-form-layout) |
| **whnf** | *Weak head normal form*: reduce the root and its head until neither can step. | [Translation](#heads) |
