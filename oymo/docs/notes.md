# Oymo notes

Oymo compiles **oymomo**, a small core lambda calculus, to LLVM IR. oymomo knows only
byte arrays, structs, lambdas and a few built-ins; higher layers build the rest.

```
oymomo source --parse--> terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

New here? Read in order:

1. [Overview](#overview): big picture, one program through every stage, where the code lives.
2. [oymomo syntax](#oymomo-syntax): how to write oymomo (cheat sheet first).
3. [Programs](#programs): what a whole program must look like.
4. [How to…](#how-to): run the tests, make common changes.

Words like *form*, *BANF*, *atom*, *blocker*: [Glossary](glossary.md).

## Find an answer

| I want to… | Go to |
|---|---|
| Understand what a word means | [Glossary](glossary.md) |
| See a program go from source to LLVM | [Overview › Walkthrough](#walkthrough-one-function-through-every-stage) |
| Know which file does what | [Overview › Where the code lives](#where-the-code-lives) |
| Write a struct, lambda, let, byte array… | [oymomo syntax › Cheat sheet](#cheat-sheet) |
| Know how `f a~t` or `x~A => B` groups | [oymomo syntax › Precedence](#precedence) |
| Know what a form is and how it differs from a type | [oymomo › Forms](#forms) |
| Know why a mistake isn't reported | [Overview › A generated IR](#a-generated-ir-no-checks-for-user-mistakes) |
| Know how terms reduce (`reduce`, built-ins, `$fix`) | [oymomo](#oymomo-forms-built-ins-reduction) |
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

- Each section: a one-line answer, an example, then the rules.
- The reasons and rejected alternatives are in [Design decisions](#design-decisions).
- When a plan lands, update the section it changes
  ([How to… › Update the notes](#update-the-notes-when-a-plan-lands)).

## Contents

- [Overview](#overview)
  - [Type, Form, Layout](#type-form-layout)
  - [A generated IR: no checks for user mistakes](#a-generated-ir-no-checks-for-user-mistakes)
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
- [oymomo: forms, built-ins, reduction](#oymomo-forms-built-ins-reduction)
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
  - [Fields are positional, in LLVM's order](#fields-are-positional-in-llvms-order)
  - [Polymorphic in `form`](#polymorphic-in-form)
  - [Folding](#folding)
- [BANF](#banf)
  - [Module](#module)
  - [Blocks](#blocks)
  - [Ops and their forms](#ops-and-their-forms)
  - [Printer](#printer-1)
- [Translation: oymomo → BANF → LLVM](#translation-oymomo--banf--llvm)
  - [oymomo → BANF](#oymomo--banf)
  - [BANF to LLVM](#banf-to-llvm)
- [Error messages](#error-messages)
  - [Names and resolution (`reduction.py`)](#names-and-resolution-reductionpy)
  - [Shaping (`banf_shape.py`)](#shaping-banf_shapepy)
  - [Program shape (`banf_translate.py`)](#program-shape-banf_translatepy)
  - [Forms (`banf_translate.py`)](#forms-banf_translatepy)
  - [Block bodies (`banf_translate.py`)](#block-bodies-banf_translatepy)
  - [Built-ins](#built-ins-1)
  - [Opcodes](#opcodes-1)
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
  - [`~` binds a term to a form](#-binds-a-term-to-a-form)
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
  - [Opcodes as LLVM writes them](#opcodes-as-llvm-writes-them)
  - [BANF](#banf-1)
  - [Translation only reduces](#translation-only-reduces)
  - [Renaming](#renaming)
  - [Memory as LLVM's defaults](#memory-as-llvms-defaults)
  - [LLVM translation converts nothing](#llvm-translation-converts-nothing)
- [Glossary](glossary.md)

## Overview

### Type, Form, Layout

Three words, three levels. A type may have several forms; a form several layouts.

| Word | Meaning | Known by |
|---|---|---|
| **Type** | Program-level meaning | Higher layers (not oymomo) |
| **Form** | Logical structure: how components are arranged | oymomo and BANF |
| **Layout** | Physical memory representation | The backend (LLVM) |

```
Bool     type: Bool                   form: 'i1'                   LLVM layout: i1
Int32    type: Int                    form: 'i32'                  LLVM layout: i32
Point    type: Point(x: Int, y: Int)  form: {x = 'i32', y = 'i32'}  LLVM layout: { i32, i32 }
Ref      type: Ref Point              form: 'ptr'                  LLVM layout: ptr
```

- A form is **not** a type: nothing checks it. `(x~'Int' -> x) 'hello'~'Str'` gives
  `'hello'~'Int'`.
- A param's form only replaces the argument's form.
- Forms exist so the backend can generate machine code.
- More: [oymomo › Forms](#forms). Why: [Design decisions](#type-form-layout-are-three-words).

### A generated IR: no checks for user mistakes

oymomo is an IR that other compilers generate; no one writes it by hand. Its syntax is
for debugging and tests. It assumes the producer knows what it is doing.

```
'add' {'i32', [01]~'i8', x}        accepted: the i8 operand is not compared with i32
if c then ... else ...             accepted with c~'i8'
g = => 'i32', returning [01]~'i8'  accepted: the return form is not compared
```

- **Forms are never compared**: not argument vs param, opcode operand vs `form`,
  branch condition vs `i1`, nor return value vs declared return form.
- **Only what a pass can't go on without is rejected**: unknown name, wrong argument
  count, missing struct field, an opcode call whose fields don't tell its result form.
- **The backend may still reject** what it can't lower (`llvm_translate`, or LLVM).
- When changing code: add a check only when a pass needs it to produce output, never
  only to guard against a user mistake.

### The pipeline

```
oymomo source --parse--> oymomo terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

`banf_translate` is four passes ([Translation](#translation-oymomo--banf--llvm)):

```
terms --reduction.resolve--> BruijnIndex terms --banf_shape.shape--> BANF-shaped term
      --banf_rename.rename--> no shadowing --banf_translate.convert--> BANF
```

| Stage | What it is |
|---|---|
| oymomo | The lambda-calculus language. Syntax in `grammar.py`, terms in `terms.py`. See [oymomo syntax](#oymomo-syntax). |
| BANF | A first-order IR shaped like LLVM, with block params instead of phi nodes. See [BANF](#banf). |
| LLVM | Generated with llvmlite. See [Translation › BANF to LLVM](#banf-to-llvm). |

### Walkthrough: one function through every stage

A recursive factorial; each stage is real output (same code as the golden tests).

**1. oymomo source.** A program is a lambda `module -> {...}` around a struct of
definitions. `fact` is a struct of blocks; each block is a lambda over its params.

```
module~{fact = => 'i32'} -> {
  fact = f -> {
    entry = args~{n = 'i32'} ->
      let t0 = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in
      if t0 then f.then0 {} else f.else0 {n = args.n},
    then0 = args~{} -> [01000000]~'i32',
    else0 = args~{n = 'i32'} ->
      let t1 = 'sub' {'i32', args.n, [01000000]~'i32'} in
      let t2 = module.fact {n = t1} in
      let t3 = 'mul' {'i32', args.n, t2} in
      t3,
  },
}
```

- `fact = => 'i32'`: a function returning `i32`, defined in the body.
- `'icmp_eq'`, `'sub'`, `'mul'` are opcodes. `module.fact {...}` is a call.
- `f.then0 {}` jumps to the sibling block `then0`.

**2. Shaped term** (`banf_translate.shape`): reduced to BANF's shape, structural
binders renamed to `module`, `f`, `args`. Here only the printing changed.

```
module~{fact= ⇒ 'i32'} → {
  fact= f → {
    entry= args~{n= 'i32'} →
      let t0 = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in
      if t0 then f.then0 {} else f.else0 {n= args.n},
    then0= args~{} → [01000000]~'i32',
    else0= args~{n= 'i32'} →
      let t1 = 'sub' {'i32', args.n, [01000000]~'i32'} in
      let t2 = module.fact {n= t1} in
      let t3 = 'mul' {'i32', args.n, t2} in t3,
  },
}
```

**3. BANF** (`banf_translate.convert`): one line per let; `args` became block
params; the `if` became a `branch`.

```
fact: i32
  entry(n: i32):
    t0 = icmp_eq 'i32', n, [00000000]:i32
    branch t0, then0(), else0(n)
  then0():
    return [01000000]:i32
  else0(n: i32):
    t1 = sub 'i32', n, [01000000]:i32
    t2 = call fact(t1)
    t3 = mul 'i32', n, t2
    return t3
```

**4. LLVM IR** (`llvm_translate.translate`): one BANF block → one LLVM block, one
let → one instruction; byte arrays became numbers.

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

Flat in `src/oymo/oymomo/`; the prefix says the stage. Each module has a test of the
same name in `tests/oymomo/`.

| File | Role |
|---|---|
| [`grammar.py`](../src/oymo/oymomo/grammar.py) | Parser: oymomo source → terms |
| [`rule_names.py`](../src/oymo/oymomo/rule_names.py) | Names of the grammar rules |
| [`terms.py`](../src/oymo/oymomo/terms.py) | oymomo term classes (`Lambda`, `Apply`, `Struct`, `Formed`…) |
| [`printer.py`](../src/oymo/oymomo/printer.py) | Prints terms, compact or pretty |
| [`reduction.py`](../src/oymo/oymomo/reduction.py) | `resolve`, `shift`, `substitute`, `reduce`, `BUILTINS` |
| [`banf_shape.py`](../src/oymo/oymomo/banf_shape.py) | Reduces a term until it has BANF's shape |
| [`banf_rename.py`](../src/oymo/oymomo/banf_rename.py) | Renames binders so none shadow each other |
| [`banf_translate.py`](../src/oymo/oymomo/banf_translate.py) | `shape`, `convert`, `translate`: oymomo → BANF |
| [`banf_terms.py`](../src/oymo/oymomo/banf_terms.py) | BANF classes, `form_of`, verifier, BANF printer |
| [`opcodes.py`](../src/oymo/oymomo/opcodes.py) | The opcodes (`OPCODES`): params, accepted forms, folding; no BANF and no LLVM; shared by reduction, BANF and LLVM |
| [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py) | llvmlite code for each opcode (`DEFAULT_OPCODES`) |
| [`llvm_translate.py`](../src/oymo/oymomo/llvm_translate.py) | BANF → LLVM IR, `Target` |

Import rules:
- Only `llvm_*.py` imports llvmlite.
- No `banf_*.py` imports an `llvm_*.py`; BANF depends only on `oymomo.terms` and `opcodes.py`.
- `opcodes.py` imports only `terms`, so reduction, BANF and LLVM can all import it.

What LLVM needs beyond BANF is passed to the LLVM translator:

```python
Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=DEFAULT_OPCODES)
```

- `opcodes` maps each opcode name to its LLVM instructions; BANF only names it (`add`).
- No `byte_order` field: byte arrays are always little-endian; the target's byte
  order comes from `data_layout` (`e` or `E`).
- Why: [BANF does not depend on LLVM](#banf-does-not-depend-on-llvm),
  [Flat files with prefixes](#flat-files-with-prefixes).

### Testing

- Unit tests per stage: `grammar_test.py`, `printer_test.py`, `opcodes_test.py`,
  `banf_terms_test.py`, `reduction_test.py`, `banf_shape_test.py`,
  `banf_rename_test.py`, `banf_translate_test.py`, `llvm_translate_test.py`.
- BANF tests build modules by hand, so they don't depend on the translator.
- Every LLVM test parses the IR with `llvmlite.binding` and verifies it.
- Golden tests (`tests/goldens/`): each `name.oymo` gives approved
  `name.shaped.oymo`, `name.banf` and `name.ll`. See
  [How to… › Add a golden test](#add-a-golden-test).

### Not decided / not done yet

- Nested function forms (in data forms, or as a function form's param or result).
  See [Programs](#nested-function-forms-are-rejected-for-now).
- Closures and higher-order functions.
- Struct constants in LLVM, including struct data initializers.
- The `language oymomo` header of `.oymo` files is checked and stripped by the golden
  test; the parser doesn't handle layers yet.
- Void functions: every function returns a value.

## oymomo syntax

Parsed by [`grammar.py`](../src/oymo/oymomo/grammar.py) into the terms in
[`terms.py`](../src/oymo/oymomo/terms.py). Meaning:
[oymomo](#oymomo-forms-built-ins-reduction); whole programs: [Programs](#programs).

### Cheat sheet

```
x~'i32' -> body              Lambda (also x -> body, and → for ->)
f a b                        Apply: (f a) b
{x = e1, y = e2}             Struct
{e1, y = e2}                 Struct with an unlabeled field
s.x                          Project: field by label
s [00]                       Apply on a struct: field by position
if c then a else b           Sugar for {b, a} c
let x = e in body            Sugar for (x -> body) e
$fix g                       Builtin, applied like a function
$0                           BruijnIndex
[2a 00 00 00]                Byte array (hex)
'Hello'                      Byte array (text)
e~'i32'                      Formed: e with a form
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

The parser never guesses. Why: [Design decisions](#brackets-have-one-job-each).

#### Reserved words

`if then else let in`. Nothing else: `fix`, `prim`, `module`, `args` are ordinary names.

### Precedence

Highest first. Rule: **values bind tighter than things that reduce**. `Formed` and
`FunctionForm` never reduce, so `~` and `=>` bind tighter than application; `.`
tighter still (`module.T`, `args.n` read as paths).

| Level | Syntax | Associativity |
|---|---|---|
| 1 | atoms: names, `$name`, `$0`, `[..]`, `'..'`, `{..}`, `(..)` | |
| 2 | project `s.x` | left |
| 3 | function form `P => R` | right |
| 4 | formed `e~F` | right |
| 5 | apply `f a` | left |
| 6 | `x -> body`, `if`, `let` | extend as far right as possible |

| Source | Means |
|---|---|
| `f a b` | `(f a) b` |
| `f a.x b` | `(f a.x) b` |
| `a -> b -> a b` | `a -> (b -> (a b))` |
| `f [01]~'u8' [02]` | `f ([01]~'u8') [02]` |
| `f a~g b` | `f (a~g) b` |
| `$fix f~t` | `$fix (f~t)` |
| `y~f a` | `(y~f) a`; write `y~(f a)` |
| `a~b~c` | `a~(b~c)` |
| `x~A => B` | `x~(A => B)` |
| `A => B~C` | `(A => B)~C` |
| `f a => g b` | `f (a => g) b` |
| `{a = 'i8'} => {b = 'i8'} => 'i32'` | `{a = 'i8'} => ({b = 'i8'} => 'i32')` |
| `[00]~'i8' => 'i32'` | `[00]~('i8' => 'i32')`; write `([00]~'i8') => 'i32'` |
| `s [00] [01]` | `(s [00]) [01]` |
| `f s [00]` | `(f s) [00]` |
| `s [00]~t` | `s ([00]~t)` |
| `'add' {'i32', x}.a` | `'add' ({'i32', x}.a)` |
| `f $fix g` | `(f $fix) g` |
| `let x = e in a b` | `let x = e in (a b)` |

Needs parentheses:
- A lambda, `if` or `let` as an argument: `f (x -> x)`; `f x -> x` is a syntax error.
- An application inside `~`: `y~(f a)`, `(f a)~t`.
- A param with a form left of `=>`: `([00]~'i8') => 'i32'`.

Why `~` is above application (unlike Haskell, OCaml, Lean):
[Design decisions](#formed-binds-tighter-than-application).

### Lambda

`x~form -> body`, or `x -> body`. Always one parameter.

```
x~'i32' -> x
a -> b -> a b               same as  a -> (b -> (a b))
x~{c = 'i8'} => 'i32' -> x
```

- `->` and `→` (U+2192) are the same.
- The param's form is an expression at the formed level
  ([Forms are terms](#forms-are-terms)). It ends at the first `->`: `x~a -> b -> c`
  is `x~a` with body `b -> c`. A lambda or application in it needs parens:
  `x~(a -> b) -> c`, `x~(f a) -> x`.
- No form: it is `Empty` ([oymomo](#omitted-forms-are-empty)).
- A lambda is tried before `~`: `x~F -> body` is a lambda with a param form, not
  `x~(F -> body)`.

### Apply

`f a`: one argument, left-associative (`f a b` is `(f a) b`).

Every built-in and function takes one argument; several operands go in a struct:
`'add' {'i32', x, y}` ([One argument, always a struct](#one-argument-always-a-struct)).

### Let

`let x = e in body` is sugar for `(x -> body) e`. No new term.

```
let t0~'i1' = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in t0
```

- Optional form on the name, as on a lambda param.
- Extends as far right as possible: `let x = e in a b` is `let x = e in (a b)`. As an
  argument: `f (let x = e in x)`.
- The printer prints *every* apply of a lambda as a `let`.
- Why: [`let` is sugar](#let-is-sugar).

### Structs

`{label = value, ...}`: an ordered list of fields.

```
{x = e1, y = e2}
{'1', b = '2'}               unlabeled field, then field b
{x = 'i32', y = 'i8'}        a struct used as a form
```

- **Order matters**: `{x = 'i32', y = 'i8'}` ≠ `{y = 'i8', x = 'i32'}` (`{i32, i8}` vs
  `{i8, i32}` in LLVM). See [Struct, not record](#struct-not-record).
- **Every field has a value.**
- **Labels are optional** (tuples). The labeled form is parsed first, so `{a}` is an
  unlabeled field holding variable `a`.
- An unlabeled field's label is `''`. A written name is never empty (`{"" = x}` is a
  parse error), so `''` only means "no label". Printed as its value alone.
- **Labels may repeat.** `s.a` picks the first: `{a = '1', a = '2'}.a` gives `'1'`.
- In BANF, unlabeled fields are fine in value structs and data forms, not where a
  label names something ([Labels](#labels-name-params-declarations-and-blocks)).

### Projection and struct apply

| Syntax | Picks by | Example | Gives |
|---|---|---|---|
| `s.a` | label written in the source | `{a = '1', a = '2'}.a` | `'1'` |
| `s i` | position, `i` is a term | `{a = '1', a = '2'} [01]` | `'2'` |

- `s.a` is a `Project` term. `s.` can't be written, so it never reaches an unlabeled field.
- `s i` is an ordinary `Apply` with a reduction rule
  ([reduce](#reduce-one-step-at-the-root)). It ignores labels, so every field is
  reachable (unlabeled, duplicate). `i` can be computed at run time.
- Index: unsigned little-endian, any length, from 0: `[01]`, `[0100]`, `[01000000]`
  are 1; `[0001]` is 256. A form on the index is ignored.
- Past the last field → the last field: `{a, b, c} [07]` is `c`. So the last field is
  a default, and `if` takes any nonzero index as true.
- Stuck (no reduction): `{} i`, `''`, or an argument that isn't a byte array.
- Labels stay static: no `s.(e)`, no `{(e) = v}`.
- In BANF, `s i` on a value struct is the op `GetIndex`; the index must be a literal
  ([Translation](#what-the-shape-is)).
- Why the name `Project`: [Design decisions](#the-name-project).

### If

`if c then a else b` is sugar for `{b, a} c`: a struct applied to the condition. `c`
reduces to `[01]` (then) or `[00]` (else), read as any [struct apply](#structs)
index (any length, form ignored). Extends as far right as possible.

```
if c then t else e           parses to   {e, t} c
{e, t} c                     prints as   if c then t else e
{'1', '2'} [01]              prints as   if [01] then '2' else '1'
{x = e, t} c                 prints as   {x = e, t} c       labeled: not an if
{e, t, d} c                  prints as   {e, t, d} c        3 fields: not an if
```

- No `If` term. The printer prints every struct of two unlabeled fields, applied to
  anything, as `if` (`reduction.branch`); output parses back to the same term.
- In BANF, `{e, t} c` in tail position is a branch, labeled or not
  ([Translation](#if-only-in-tail-position)).
- Design: [plan_if_as_struct_apply.md](implemented/plan_if_as_struct_apply.md).

### Byte arrays

No numbers, only bytes.

```
[2a000000]~'i32'             42, as an i32
[2a00 0000]                  same bytes
[2a 00 00 00]                same bytes
[]                           empty
[deadbeef cafebabe
 00112233 44556677]~{lo = 'i64', hi = 'i64'}
```

- Inside `[]`: groups of hex digits split by whitespace (newlines too). A group has
  any number of bytes, an even number of digits.
- No comments inside the brackets.
- **Always little-endian, on every target**: `[2a000000]~'i32'` is 42 everywhere
  ([why](#byte-arrays-are-always-little-endian)).
- `~form` is optional and an ordinary `Formed`, not part of the literal: `[01000000]`
  could be `'i32'` 1 or `{a = 'i16', b = 'i16'}`.

#### Text byte arrays

`'Hello'` is the same term as `[48656c6c 6f]`.

- Characters `0x20..0x7e` except `'` and `\`. No escapes (yet). Single line. `''` is empty.
- Bytes with `'`, `\` or non-printable characters: write hex.
- A named form such as `'i32'` is a text byte array.

### Function forms

`P => R` (or `P ⇒ R`, U+21D2): form of a function from `P` to `R`. Term
`FunctionForm(param, result)`.

```
{c = 'i8'} => 'i32'          takes {c: i8}, returns i32
=> 'i32'                     param left out: FunctionForm(Empty, 'i32')
{putchar = {c = 'i8'} => 'i32'}   a function form as a field value
```

- One param, no param name: callers use the struct form's labels
  (`module.putchar {c = [41]~'i8'}`).
- `=> R` ≠ `{} => R` (no param vs. an empty struct). In `module`, `=> R` declares a
  function the body defines ([Programs](#module-declares-every-symbol)).
- `=> => R` is `=> (=> R)`. With something on its left, `=>` takes it as the param:
  `f => b` is `(f) => b`; as an argument write `f (=> b)`.
- `=>` vs `->`: a form vs a lambda at a glance; a binder's form safely ends at `->`.
- Why its own term: [Design decisions](#function-forms-are-their-own-term).

### Names

Plain identifiers: `[A-Za-z_][A-Za-z0-9_]*` (ASCII only), except reserved words. Any
other non-empty string goes in double quotes: `"a b"`, `"if"`, `"main.1"`.

- `"x"` and `x` are the same name; the parser stores the decoded string.
- Escapes: `\"`, `\\`, `\u{hex}`. No raw newlines. `""` is rejected.
- Quotes work wherever a name appears: variables, lambda params, struct labels,
  projection labels (`s."a b"`). Form names are byte arrays (`'a b'`), not names.
- Printers (BANF's too) quote only when needed: `Data('my data', ...)` prints
  `"my data": i8`.
- Why: [Quoted names](#quoted-names).

### Builtins and indices: `$name` and `$0`

`$` marks a reference no user name binds.

| Syntax | Term | Bound by |
|---|---|---|
| `$0`, `$1`… | `BruijnIndex` | position (`$0` = nearest binder) |
| `$fix` | `Builtin` | oymomo |

- Identifiers can't start with a digit, so the two never overlap.
- No space after `$`, no quotes: `$ fix`, `$"fix"` are errors.
- Nothing is reserved after `$`; the parser accepts any `$name`.
- `$name` is an atom, like a variable.
- What built-ins do: [oymomo › Built-ins](#built-ins).

### Comments

`// comment` to end of line. (`#` is unused.)

### Printer

[`printer.py`](../src/oymo/oymomo/printer.py): `printer.show(term)`,
`printer.show_form(form)`. Prints `→` for lambdas, `⇒` for function forms.

| Mode | Use | Output |
|---|---|---|
| compact (default) | tests | One line, parens only where needed: `a → b → a b`, `f (x → x)`, `(f a).x`. |
| `pretty=True` | people, goldens | Source that parses back to the same term (tested). Bytes in groups of four (`[deadbeef cafebabe]`) or as `'text'`. |
| `name_indices=True` | either mode | Prints a `BruijnIndex` as its binder's name, so resolved terms read like source. |

Both modes:
- Omitted forms are not shown. Names quoted when needed (`"if"`, `"a b"`).
- `~` has no spaces: `x~'i32' → x`, `[01]~'i8'`.
- An apply of a lambda prints as `let x~'i8' = e in body`.
- `BruijnIndex` → `$0`, `Builtin` → `$fix`, `Variable` → its name. `$0` parses back as
  a `BruijnIndex`, so resolved terms round-trip.
- `name_indices=True` keeps `$i` where an inner binder shadows the name
  (`x → x → $1`) or no binder is in scope, so output still resolves to the same term.
  Used by the shaped golden and rename tests.
- `'...'` only for a byte array with no form, all text bytes, ≤ 128 bytes; else hex
  ([why](#text-byte-arrays-1)).

Pretty mode breaks a term wider than `width` (default 80), indenting by `indent` (default 2):
- struct: one field per line, trailing comma;
- lambda: body on the next line, indented, unless it is a struct or lambda (so
  `module~{...} → {` stays together);
- apply: argument on the next line, indented;
- `let`: body on the next line at the `let`'s indentation, one let per line:
  ```
  entry = args~{n = 'i32'} →
    let t0 = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in
    if t0 then f.then0 {} else f.else0 {n = args.n},
  ```
- `if`: `then` and `else` on their own lines.

Compact mode lets grammar tests check nesting:
`show(parse('f a b')) == show(parse('(f a) b'))`.

## oymomo: forms, built-ins, reduction

What oymomo terms mean. Syntax: [oymomo syntax](#oymomo-syntax).

### Forms

A **form** is a value's logical structure (`'i32'`, `{x = 'i32'}`), used to generate
machine code. **Not a type**: nothing checks one form against another.

```
(x~'Int' -> x) 'hello'~'Str'        gives  'hello'~'Int'
```

A param's form only replaces the argument's form. See
[Type, Form, Layout](#type-form-layout).

#### Forms are terms

No separate form syntax or class; a form is an ordinary term:

| Form | Written | Term |
|---|---|---|
| named | `'i32'` | `ByteArray(b'i32')` (a bare `i32` is a variable) |
| struct | `{x = 'i32', y = 'i8'}` | `Struct` |
| function | `{c = 'i8'} => 'i32'` | `FunctionForm(param, result)` |
| array | `{'array', [03000000]~'i32', 'i32'}` | `Struct`, field 0 the tag; LLVM `[3 x i32]` |
| vector | `{'vector', [04000000]~'i32', 'i32'}` | `Struct`; LLVM `<4 x i32>` |
| scalable vector | `{'scalable_vector', [04000000]~'i32', 'i32'}` | `Struct`; LLVM `<vscale x 4 x i32>` |
| packed struct | `{'packed', a = 'i8', b = 'i32'}` | `Struct`; LLVM `<{i8, i32}>` |

- Any term may be a form. A binder's form (`x~F -> b`, `let x~F = v in b`) is the same
  kind of expression as `F` in `e~F`: `x~i32 -> x`, `x~module.T -> x`,
  `x~'i8' => 'i32' -> x`, `x~[00]~'i8' -> x`.
- Forms resolve like other terms: a variable in a lambda param's form is looked up
  *outside* the lambda (`x~(x) -> x`: the form is an outer `x`).
- BANF translation needs **literal** forms (named forms, structs and tagged structs of
  them); others: "form must be a literal".
- **Tagged structs** are LLVM's other aggregates (plan_memory.md decision 8): field 0
  is a tag naming the type, then its parts, positional, in LLVM's order. Reduction
  sees plain structs; only BANF and LLVM read the tag (`opcodes.tagged_form`, the one
  reader).
  - `'array'`, `'vector'`, `'scalable_vector'`, `'packed'` are reserved: never a data
    form, so `{'i32', x = 'i8'}` stays a plain struct.
  - Array / vector: exactly `count` and `element`. `count` is a byte array formed as an
    integer form, read unsigned; a vector's is above 0 and its element an integer form
    or `'ptr'`. Labels of tag, `count`, `element` are ignored; a packed struct keeps
    its field labels.
  - Scalable vector: not inside a struct, packed struct or array (as in LLVM); may be
    a param. llvmlite has no type for it, so LLVM translation rejects it.
  - Packed struct fields are read by label or index like a struct's (`v.b`); array and
    vector elements aren't (use `'getelementptr'` and `'load'`).
- `==` ignores locations on every term, so a parsed form equals one built in code
  (`terms.ByteArray(b'i32')`, `terms.struct_form(...)`).
- Why: [Forms are terms](#forms-are-terms-1).

#### Omitted forms are `Empty`

Any binder's `~form` may be left out (`x -> body`, `let x = e in ...`). Omitted =
`terms.Empty`, meaning **not written**.

- `Empty` is not void. There is no void form; `~'void'` is just a form named void.
- No default meaning: each position says what it means or rejects it. A BANF let
  takes its op's form (`let t0 = 'icmp_eq' {'i32', ...} in t0` needs no `t0~'i1'`). A
  byte array with nothing giving it a form (`[01]` alone): "form must be written".
- A byte array has no form of its own: `[2a]` is just bytes.
- Why: [Design decisions](#omitted-forms-are-empty-with-no-default).

#### `Formed`: any term with a form

`e~F` is `Formed(e, F)`, "`e`, formed as `F`". `F` is an expression, so a form can come
from a variable:

```
(x -> y -> y~x) 'i1' [01]           gives  [01]~'i1'
```

- `[01]~'i8'` is `Formed(ByteArray([01]), 'i8')`, like `y~'i8'` is `Formed(y, 'i8')`
  ([A byte array is only its bytes](#a-byte-array-is-only-its-bytes)).
- `Formed` never reduces. `reduce_until_top_stable` reduces inside `Formed.term`, and a
  struct apply (so an `if`) sees through a form on its index.
- Precedence: [Precedence](#precedence). History:
  [plan_annotation.md](implemented/plan_annotation.md).
- BANF translation: a formed byte array → a constant; any other formed atom → that
  atom with the written form.
- **The written form replaces the atom's own, unchecked**: `([01]~'i8')~'i16'` is the
  constant `[01]:i16`; `args.n~'i32'` is `n:i32` even if `n` is `i8`. LLVM translation
  rejects a formed name whose LLVM type differs.

### Built-ins

oymomo's helpers, each a global constant written `$name`: `$fix g`.

- Machine instructions are not built-ins but opcodes: `'add' {'i32', x, y}`, a byte
  array applied to a struct ([Opcodes](#opcodes)).
- One argument; several operands go in a struct. A call is always
  `Apply(Builtin(name), arg)`.
- Each built-in is its own constant: no `$` struct to project from, apply or unpack.
- No reserved names: `fix -> fix` is an ordinary lambda.

| Table | File | Gives |
|---|---|---|
| `BUILTINS` | [`reduction.py`](../src/oymo/oymomo/reduction.py) | the built-ins' names; each has a case in `reduction.reduce` |
| `OPCODES` / `DEFAULT_OPCODES` | [`opcodes.py`](../src/oymo/oymomo/opcodes.py) / [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py) | an opcode, and its machine code |

- A built-in's rule: a root-only case in `reduction.reduce`.
- An opcode has no rule of its own: `reduction.fold_opcode(call)` folds it at the root,
  reducing nothing.
- One rule for every `'name' arg`: the argument must be a struct literal whose fields
  are byte arrays or structs. So `banf_shape` reduces the argument, then each field,
  whatever the opcode and field count.

| Call | Rule |
|---|---|
| `$fix g` | gives `g ($fix g)` once `g` is a lambda; `g` is reduced to one first, never under it; must reduce away |
| `$fields_to_struct {more = [01], label = 'l1', value = e1, rest = ... {more = [00]}}` | gives `{l1 = e1, ...}`; reduces `more`, `label` and `rest` of each node first, never a value; stuck on a malformed list; must reduce away |
| `$struct_to_fields {l1 = e1, ...}` | gives `{more = [01], label = 'l1', value = e1, rest = ... {more = [00]}}`: labels as UTF-8 bytes, values unreduced, order kept ([plan_struct_pack.md](implemented/plan_struct_pack.md)); must reduce away |
| `$seq {d1, ..., dn, x}` | gives `x` once every `di` is a byte array, formed or not: a literal has no effect left to wait for. Every field is reduced first, the last one too; labels are ignored. Otherwise stuck, and `convert` drops it: it is the atom of `x`. It orders effects by hand ([plan_memory.md](implemented/plan_memory.md) decisions 1 to 4) |
| `'add' {...}` and every other opcode | on literal fields, the result LLVM would compute: `'add' {'i32', [01000000], [02000000]}` gives `[03000000]~'i32'`; needs a struct literal with one field per param. Never where LLVM has no defined result ([plan_constant_folding.md](implemented/plan_constant_folding.md)). See [Opcodes › Folding](#folding) |

- Every built-in but `$seq` is **reduction-only**: reduction must remove it. `convert`
  drops a stuck `$seq`.
- `$seq` says which effects a value needs; it doesn't order or keep them. `translate`
  keeps every let whose value is an op, once, in source order, chained or not (tests:
  [banf_translate_test.py](../tests/oymomo/banf_translate_test.py),
  `test_an_unused_effect_is_kept` and after):
  - **An unused effect is kept**: a store nothing waits for stays in the block.
  - **An effect used twice runs once**: two uses of one load read one `load`.
  - **Order is let order**: `$seq {b, a}` doesn't move `a` before `b`.
- `reduction.reduce` fires a built-in only once its argument has the needed
  constructor; it never reduces a part. `banf_shape.unblock` reduces the parts each
  built-in reads ([Blockers](#blockers)).
- What a leftover built-in's argument must reduce to (e.g. `'a struct'`), for the
  error message: `banf_translate._MUST_REDUCE_TO`.
- `convert` is the only gate into BANF: `'name' {...}` becomes an `OpcodeCall` only if
  `name` is in `OPCODES`; a leftover `$name` is an error
  ([Error messages › Built-ins](#built-ins-1)).
- BANF keeps instructions and symbols apart: `OpcodeCall` for opcodes, `Call` for
  `module` symbols. An opcode never becomes an LLVM symbol.
- Why built-ins (not `module` names, a `prim` binder, a `fix` term):
  [Design decisions › Built-ins](#built-ins-2),
  [plan_builtin.md](implemented/plan_builtin.md).

### `reduce`: one step at the root

`reduction.reduce(term)` takes one step if the root is a redex, else returns `term`
itself (`reduce(t) is t` means "not a redex"). It never looks inside.

| Rule | Before | After |
|---|---|---|
| beta | `(x -> body) e` | `body` with `e` for `x` |
| beta with form | `(x~F -> body) e` | `body` with `e~F` for `x` (`e`'s own form dropped) |
| built-in | `$fix (x -> b)` | `(x -> b) ($fix (x -> b))` (only on a lambda) |
| built-in | `$struct_to_fields {a = e}` | `{more = [01], label = 'a', value = e, rest = {more = [00]}}` |
| built-in | `$fields_to_struct {more = [01], label = 'a', value = e, rest = {more = [00]}}` | `{a = e}` |
| built-in | `$seq {[01], [02]~'i8', x}` | `x` |
| opcode | `'add' {'i32', [01000000], [02000000]~'i32'}` | `[03000000]~'i32'` |
| projection | `{a = e, ...}.a` | `e` |
| struct apply | `{e0, e1, ...} [01]` | `e1` |
| if (struct apply) | `if [01] then a else b` / `if [00] ...` | `a` / `b` |

Not redexes:
- an unknown built-in (`$nope g`), or a rule that doesn't fire: an opcode on a run-time
  operand (`'add' {'i32', args.n, ...}`), on a literal of the wrong form or size, or
  where LLVM has no defined result (`'udiv'` by `[00000000]`);
- a projection with a missing label;
- a struct apply on `{}`, with `''`, or with an argument not yet a byte array (index
  read by `reduction.index_value`: unsigned little-endian, form ignored). Past the end
  → last field: `if [02] then a else b` and `if [0100] then a else b` are both `a`.

Properties:
- **Only the root.** Arguments, lambda bodies, struct fields, `if` arms are not touched,
  nor an unreduced blocker (`$fix g a`, `{p = {a = e}}.p.a`).
  [`banf_shape`](#2-banf_shapeshape-reduce-until-each-position-has-its-shape) reduces
  blockers.
- **At most one rule applies**, so order doesn't matter: beta needs a `Lambda` callee,
  struct apply a `Struct`, a built-in rule a `Builtin`.
- **Never raises, never recurses.** Loops come from calling it repeatedly, so the fuel
  limit lives in `banf_shape`.
- Helpers: `shift`, `substitute`, `beta` (`shift(substitute(body, 0, shift(arg, 1)), -1)`),
  `project`, `index_value`.

## Programs

What a whole program must look like to compile to BANF and LLVM. Full example:
[Walkthrough](#walkthrough-one-function-through-every-stage).

### The shape of a program

A lambda `module -> {...}` around a struct of definitions:

```
module~{putchar = {c = 'i8'} => 'i32', errno = 'i32', main = => 'i32'} -> {
  main = f -> {entry = args~{} -> let t0 = module.putchar {c = [41]~'i8'} in t0},
}
```

```
module~{ declarations } -> {                the program
  name = f -> {                             a function: a struct of blocks
    entry = args~{ params } -> body,        a block: a lambda over its params
    other = args~{ params } -> body,
  },
  name = [bytes],                           defined data
}
```

Binder names are free in the source; shaping renames them to `module`, `f`, `args`
([Translation](#3-banf_renamerename-fixed-names-and-no-shadowing)).

### `module` declares every symbol

`module`'s form declares every symbol, imported or defined, in one struct. The body is
passed back in as `module`, so functions and imports are used the same way:
`module.fact {n = t1}`, `module.putchar {c = [41]~'i8'}`, `module.errno`.

The declaration's shape says what it is:

| Declaration | Defined in the body? | Result |
|---|---|---|
| `=> R` | yes, as a function | `banf.Function`: params from its entry block, return form `R` |
| `=> R` | no | error: "'main' declares no params, so it must be defined." |
| `{...} => R` | no | imported function, `banf.Signature`: `declare i32 @putchar(i8 %c)` |
| `{...} => R` | yes | error: "'putchar' declares its params; a definition takes them from its entry block." |
| data form `F` | no | imported read-only data, `banf.Data`: `@tbl = external constant i32` |
| data form `F` | yes, as a byte array | defined read-only data, `banf.Data` with a value: `@answer = constant i32 42` |
| `'ptr'` | no | imported cell, `banf.Cell`: `@errno = external global [0 x i8]` |
| `'ptr'` | yes, as `'global' {form, init}` | defined cell, `banf.Cell`: `@counter = global i32 41` |

Rules:
- A body label must be declared: "'f' is defined but not declared."
- A definition must fit its declaration: `=> R` needs `f -> {...}`; data needs a byte
  array ("'answer' is declared as data, so its definition must be a byte array."); `'ptr'`
  needs `'global' {...}`, and a `'global'` field needs a `'ptr'` declaration.
- **The declaration is the form of `module.x`** (plan_memory.md decisions 14 to 18):
  - Data is a read-only **value**: `module.answer` is read with `GetData` (an LLVM
    `load`), a pure read needing no `$seq`. LLVM may fold a defined one and reuse a
    read of an imported one.
  - A cell is **writable storage**: `module.counter` is its address, a `'ptr'` atom
    (`CellAddress`, printed `@counter`), used directly as an operand:
    `'load' {'i32', module.counter}`, `$seq {s, module.counter}`,
    `module.f {p = module.counter}`. Reads and writes through it are effects.
    `let c = module.counter in ...` is an error (the let's value is an atom).
  - `'global' {form, init}`: `form` a literal data form, `init` a byte array of it (bare
    or formed; an integer form's must have its width). No `init`: zeros
    (`zeroinitializer`). Storage is static, made at load time, so not an effect.
    `'global'` anywhere but a body field is an error.
  - An imported cell is `external global [0 x i8]`, as clang does for
    `extern char a[];`: every `'load'` brings its own form. A value that can change
    outside the program (`errno`) must be declared `'ptr'`; declared `'i32'` it is
    read-only, and LLVM may assume it never changes.
- A body field is reduced with `reduce_until_top_stable`, so `answer = (x -> x) [2a]`
  works. A data definition's form is the declared one; a form on the byte array
  (`[2a]~'i16'`) is dropped.
- Every parameter list is written **once**: a defined function's in its entry block,
  an imported one's in its declaration.
- Every return form is written, in the declaration
  ([Return forms are declared](#return-forms-are-declared)).
- A forgotten definition (declared `=> R`, not defined) is a translation error, not a
  link error.
- No symbols: write `module~{}`. The form is required.
- BANF bindings come out in declaration order.
- Recursion needs no `$fix`: functions call each other through `module`, as LLVM
  functions call by symbol. A source `$fix` is only unfolded during shaping; it never
  becomes a loop or call.
- Every external symbol is declared in `module`, so a module lists all it needs from
  outside; the linker resolves it.
- Why one binder (not `decls` + `defs`): [Design decisions](#one-module-binder).

### Symbols

Each `module` declaration becomes one LLVM symbol named after its label (`@fact`,
`@putchar`, `@errno`).

### Functions are structs of blocks

```
fact = f -> {
  entry = args~{n = 'i32'} -> ... if t0 then f.then0 {} else f.else0 {n = args.n},
  then0 = args~{} -> [01000000]~'i32',
  else0 = args~{n = 'i32'} -> ...,
}
```

Full example: [Walkthrough](#walkthrough-one-function-through-every-stage).

- The function's binder (`f`) is its own struct of blocks, so `f.then0 {}` jumps to a
  sibling. Same self-reference trick as `module`, one level down.
- Each block is a lambda over one struct (`args~{n = 'i32'} -> ...`); `args` is the
  block's param struct.
- **The first field is the entry block**, whatever its name. It can't be jumped to
  ([BANF](#the-entry-block-cannot-be-jumped-to)).
- A block body is a chain of lets ending in a terminator:
  - return an atom: `[01000000]~'i32'`, `args.n`, or a let name;
  - jump: `f.label {...}`;
  - branch: `if c then f.a {...} else f.b {...}`;
  - switch: `{f.a {...}, f.b {...}, f.c {...}} k`, three or more jumps.
- Why: [Design decisions](#functions-are-structs-of-blocks-1).

### One argument, always a struct

A lambda takes one argument. Every block's, opcode's and imported function's argument
is a **struct** whose labels name the arguments: `{minuend = x, subtrahend = y}`.
Translation expands it **one level** into params, one-to-one with LLVM:

```
oymomo: fact = f -> {entry = args~{n = 'i32'} -> ...}
BANF:   entry(n: i32)
LLVM:   define i32 @fact(i32 %n)
```

- One level only: `args~{p = {x = 'i32', y = 'i32'}}` is one param `p` of struct form,
  one LLVM argument `{i32, i32} %p`.
- A call or jump argument is a struct literal of atoms whose labels match the callee's
  params in order, or the block's own `args` forwarded as-is: `module.add args`,
  `f.body args`.
- The expansion happens in oymomo → BANF, so BANF → LLVM stays one-to-one.
- Why: [Design decisions](#one-argument-always-a-struct-1).

### Return forms are declared

Every function's return form, imported or defined, is in its `module` declaration
(`main = => 'i32'`). A returned value's form is not compared with it
([no checks](#a-generated-ir-no-checks-for-user-mistakes)). Recursion needs nothing
special:

```
module~{loop = => 'i8'} -> {
  loop = f -> {
    entry = args~{c = 'i1'} -> if args.c then f.a {} else f.b {},
    a = args~{} -> let t = module.loop {c = [00]~'i1'} in t,
    b = args~{} -> [07]~'i8',
  },
}
```

Why not inferred: [Design decisions](#return-forms-are-declared-not-inferred).

### Nested function forms are rejected, for now

A function form is accepted only as a `module` declaration's whole form. Rejected
until their meaning is decided:
- inside a data form: `module~{libc = {putchar = {c = 'i8'} => 'i32'}}`;
- as a param or result: `module~{g = {c = 'i8'} => {d = 'i8'} => 'i32'}`,
  `main = => => 'i32'`;
- with a non-struct param: `module~{g = 'i8' => 'i32'}`.

`Empty` forms inside a declaration are rejected too ("form must be written"): nothing
infers a form. `Empty` alone (`main = `) can't be written: a field needs a value.

### First-order only

No closures, no escaping lambdas. After reduction the only lambdas left are the
program, function, block and let binders. A helper lambda that reduction inlines is
fine; a leftover one is an error.

## Opcodes

An **opcode** is one LLVM instruction, called as a byte array applied to a struct:
`'add' {'i32', x, y}` is `add i32 x, y`.

- Not a built-in (no `$`): a function on values, the same in every program.
- Table: plain data in [`opcodes.py`](../src/oymo/oymomo/opcodes.py) (`OPCODES`, no BANF,
  no LLVM). LLVM code: [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py)
  (`DEFAULT_OPCODES`). A test checks both have the same names.
- `'name' {...}` is `Apply(ByteArray, Struct)`, a shape reduction otherwise leaves
  stuck (no rule for a byte array in function position), so no new term.

### Table

An opcode has no declared params: it reads its fields by position (`opcodes.Opcode`).
`form_of(fields)` gives the result form; `evaluate(fields)` the result bytes when the
needed fields are literals. `T` is one of `i1 i8 i16 i32 i64`.

| Opcodes | Fields | Result form | LLVM |
|---|---|---|---|
| `add mul` | `{form, a, b}` | `form` | `add`, `mul` |
| `sub` | `{form, minuend, subtrahend}` | `form` | `sub` |
| `sdiv udiv srem urem` | `{form, dividend, divisor}` | `form` | same names |
| `shl lshr ashr` | `{form, value, amount}` | `form` | same names |
| `and or xor` | `{form, a, b}` | `form` | `and`, `or`, `xor` |
| `icmp_eq icmp_ne icmp_slt icmp_sle icmp_sgt icmp_sge icmp_ult icmp_ule icmp_ugt icmp_uge` | `{form, lhs, rhs}` | `i1` | `icmp` and the predicate |
| `zext sext trunc` | `{form, value, to}` | `to` | same names |
| `alloca` | `{form}`, `{form, count}` | `ptr` | `alloca F`, `alloca F, iN count` |
| `getelementptr` | `{form, ptr, i0, ..., in}` | `ptr` | `getelementptr F, ptr p, iN i0, ...` |
| `load` | `{form, ptr}` | `form` | `load F, ptr p` |
| `store` | `{value, ptr}` | `{}`, which only `$seq` may use | `store F value, ptr p`; binds no LLVM value |
| `global` | `{form}`, `{form, init}` | `ptr` | `@x = global F init`; only as a body field ([cells](#module-declares-every-symbol)) |

- Operands are read at `form`; `to` only gives the result form.
- Memory opcodes are impure, so they never fold. Their `form` may be any literal form,
  a struct included; other fields bring their own forms (`[1000000000000000]~'i64'`, a let).
- `getelementptr` into a struct or packed struct: an index past the first must be a
  literal `'i32'` below the field count (as in LLVM); into an array or vector it may be
  a run-time value. See [plan_memory.md](implemented/plan_memory.md) decisions 5 to 9.
- Nothing checks which forms are given
  ([no checks](#a-generated-ir-no-checks-for-user-mistakes)): `'add' {'ptr', a, b}`
  reaches LLVM, which rejects it.
- `evaluate` computes only what LLVM defines: nothing for a `form` that isn't a `T`, or
  a conversion that doesn't widen (`zext`, `sext`) or narrow (`trunc`).

### Naming

- One opcode per LLVM instruction, named as LLVM does: `add`, `udiv`, `zext`.
- One opcode per comparison predicate: `icmp_` + LLVM's predicate (`icmp_slt`), not one
  `icmp` with a predicate field.
- Never `call`, `jump`, `branch`, `switch`, `return` (they'd read as BANF keywords);
  `banf_terms.py` asserts this.

### Fields are positional, in LLVM's order

`'sub' {'i32', x, y}` is `sub i32 x, y` = `x - y`, as LLVM writes `sub i32 %x, %y`.

- The form sits where LLVM writes the type: `'zext' {'i8', x, 'i32'}` is `zext i8 x to i32`.
- Labels are ignored, as in a branch: `'sub' {form = 'i32', subtrahend = x, minuend = y}`
  is still `x - y`.
- BANF prints fields in the same order: `sub 'i32', x, y`.

### Polymorphic in `form`

The form is a field, not part of the name, as in `add i32 %a, %b`.

- The fields must tell the result form: `form_of` needs a byte array where it reads one
  (`form` or `to`). It may be computed: `(f -> 'add' {f, x, y}) 'i32'` reduces to
  `'add' {'i32', x, y}`. Otherwise: `'add' cannot tell its result form from its fields.`
- BANF's `OpcodeCall` stores that form once and never asks the opcode again (like a
  `Call`'s comes from its callee's signature).
- Each field becomes an atom:
  - a bare byte array (the form `'i32'`, an operand `[01000000]`) stays bare: a `Const`
    with no form;
  - a struct literal is a form (an operand must be an atom): a `FormField`
    (`'alloca' {{x = 'i32', y = 'i64'}}`).
  - `llvm_opcodes.py` reads a form field as a form, a bare operand at `form`.
- Operand forms are not compared with `form`: `'add' {'i32', [01]~'i8', ...}` is
  accepted; LLVM may reject it. Convert explicitly with `'zext'`.

### Folding

An opcode whose fields are all literals reduces to its result, so a constant computed
in oymomo doesn't reach BANF as an instruction:

```
'add' {'i32', [01000000]~'i32', [02000000]~'i32'}   ⇒   [03000000]~'i32'
'add' {'i8', [ff], [01]}                            ⇒   [00]~'i8'
'add' {'i32', args.n, [01000000]~'i32'}             stays: a run-time operand
```

- **One rule for every opcode** (`reduction.fold_opcode`): wraps
  `opcode.evaluate(fields)` in `opcode.form_of(fields)`. `evaluate` computes on unsigned
  integers, with no LLVM. Every opcode is `pure`, so every opcode folds.
- **Same bytes as LLVM**:
  - little-endian, `(N + 7) // 8` bytes for `iN`, arithmetic modulo `2^N`;
  - signed opcodes (`sdiv srem ashr icmp_slt icmp_sle icmp_sgt icmp_sge sext`) read
    two's complement; `sdiv` rounds toward zero; `srem` has the dividend's sign;
  - comparisons give `i1` (`[01]` or `[00]`); `zext`, `sext`, `trunc` change width as LLVM;
  - `llvm_translate_test.test_fold_matches_llvm` runs each opcode at each `T` (and each
    conversion LLVM defines) through LLVM's JIT on edge operands and compares.
- **No undefined behaviour is folded**: where LLVM gives poison or UB, `evaluate`
  returns None and the call stays: division or remainder by 0, `sdiv`/`srem` of the
  signed minimum by -1, a shift by `N` or more.
- **Operands**: a byte array of exactly `(N + 7) // 8` bytes, below `2^N`, bare or
  formed (`opcodes.decode_uint`). A written form isn't compared with `form`; bytes are
  read at `form`: `'add' {'i8', [01]~'i32', [02]}` folds to `[03]~'i8'`. Anything else
  doesn't fold.
- **Result**: formed as the opcode's result (`[03000000]~'i32'`), so BANF knows its form
  and an `if` on a folded comparison is a jump.
- **Laziness**: `banf_shape` reduces the argument, then each field; the rule reduces nothing.
- In BANF, a let whose value folds is no longer an op, so it is substituted.
- Adding one: [How to… › Add an opcode](#add-an-opcode).

## BANF

**BANF** (block-based ANF): the first-order IR between oymomo and LLVM. SSA with
**block parameters instead of phi nodes** (as in MLIR, Cranelift). Classes, `form_of`,
verifier and printer: [`banf_terms.py`](../src/oymo/oymomo/banf_terms.py). No LLVM
dependency.

```
fact: i32
  entry(n: i32):
    t0 = icmp_eq 'i32', n, [00000000]:i32
    branch t0, then0(), else0(n)
  then0():
    return [01000000]:i32
  else0(n: i32):
    t1 = sub 'i32', n, [01000000]:i32
    t2 = call fact(t1)
    t3 = mul 'i32', n, t2
    return t3
```

### Module

```python
Module(bindings: list[Function | Signature | Data | Cell])
Function(name, return_form, blocks)       # blocks[0] is the entry block
Signature(name, params, return_form)       # imported function
Data(name, form, value=None)               # read-only: imported (None) or defined (bytes)
Cell(name, form=None, value=None)          # writable: imported (no form), or defined
CellAddress(name)                          # an atom, `module.counter`: the cell's `ptr`
```

- `name` is the LLVM symbol (`@fact`, `@putchar`, `@errno`), stored on the binding.
- `Signature` has its own `params`: it has no entry block to hold them.
- `Data`: read-only value, read with `GetData` (an LLVM `constant`). A value that can
  change outside the program (`errno`) is a `Cell`.
- `Cell`: writable storage. Defined: the stored form and initial bytes (None: zeros).
- `CellAddress`: an atom of form `ptr`; the verifier checks it names a `Cell`, as
  `GetData` must name a `Data`.

### Blocks

A block has params, lets, and one terminator (`return`, `jump`, `branch`, `switch`).
A join block declares what it receives; each jump passes it:

```
then0(x: i32, z: i32):
  jump join0(x, z)
else0(y: i32, z: i32):
  jump join0(y, z)
join0(v: i32, z: i32):
  t0 = add 'i32', v, z
```

The LLVM translator turns these back into phis where needed
([BANF to LLVM](#banf-to-llvm)). Why basic blocks and block params: [BANF](#banf-1).

#### Blocks are closed

A block uses only its own params and lets. A value from another block is passed as a
jump or branch argument: `else0` needs `n`, so `entry` does
`branch t0, then0(), else0(n)`.

- Names are scoped to their block, so a passed value keeps its name (`else0(n: i32)`).
- In oymomo this holds by construction: a block lambda sees only its `args`, its lets,
  and the outer `f` and `module`; built-ins are global.

#### The entry block cannot be jumped to

The entry block's params are the function's params (as in Cranelift). LLVM's entry
block can't have predecessors, and its params are arguments, not phis. A loop jumps to
a separate header:

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
| `OpcodeCall` | `'add' {'i32', ...}` | its stored `form`, told by the opcode's `form_of` in `convert` |
| `Call` | `module.g {...}` | the callee's `return_form` (`Function` or `Signature`) |
| `MakeStruct` | `{x = a, y = b}` | each label paired with its field atom's form |
| `GetField` | `args.p.x` | that field's form inside the struct's form |
| `GetIndex` | `args.p [01]` | the form of the field at that position, labeled or not; past the last field, the last field's (`Form i32 has no field at index 0.`) |
| `GetData` | `module.errno` | the `Data` binding's form |

Forms **are** stored on:

| On | Why |
|---|---|
| each `Const` | the same bytes can have many forms |
| each block param | a block must declare what its jumps pass in |
| each function's and signature's return form | calls read them, recursive calls included; they come from `module` |
| each `Data`, each defined `Cell` | |
| a `Let`, only if the source wrote one | otherwise `form_of` computes it; a stored `MakeStruct` form would repeat a full struct form on every line |

- Ops carry no form, as in Cranelift (`v0 = iadd v1, v2`).
- A written let form (`Let.form`; `Empty` if not written) replaces the op's form.
- The verifier and LLVM translator use `let_form` while walking a block (the written
  form, else `form_of` its op) and add it to the block's name table.

### Printer

| Prints | Example | Note |
|---|---|---|
| a let | `t0 = icmp_eq 'i32', n, [00000000]:i32` | no `let` keyword, no form (unless written: `t0: i32 = ...`) |
| an opcode | `t3 = mul 'i32', n, t2` | assembly style: no parens, no `$` |
| a call | `t2 = call fact(t1)` | keyword `call`, parens, commas |
| a data read | `t0 = errno` | bare name (an opcode always has operands) |
| a `GetIndex` | `y = p.1` | a digit label would need quotes (`p."1"`), so never a `GetField` |
| an unlabeled field | `{i32, i8}`, `{n, y = [01]:i8}` | value alone |
| a function form with no param | `(=> R)` | |
| a `Signature` | `putchar(c: i8): i32` | |
| imported `Data` | `errno: i32` | |
| defined `Data` | `answer: i32 = [2a000000]` | |
| imported `Cell` | `errno: global` | |
| defined `Cell` | `counter: global i32 = [29000000]`, `zeroed: global i32` | |
| a `CellAddress` | `c = load 'i32', @counter` | `@`, as LLVM names a global |
| a `Function` | `fact: i32` then its blocks | blank line around each function |

- Every terminator starts with a keyword (`jump`, `branch`, `switch`, `return`).
- Calls and data reads use the symbol, not `module.`.
- Bindings print in declaration order.
- Block labels are indented 2 spaces, instructions 4.
- Names quoted when needed: `"my data": i8`.
- Why: [BANF](#banf-1).

## Translation: oymomo → BANF → LLVM

### oymomo → BANF

`banf_translate.translate(term)` runs four passes. `shape(term)` runs the first three
and returns an oymomo term in BANF's shape; `convert(shaped)` runs the last.

| # | Pass | Does |
|---|---|---|
| 1 | `reduction.resolve` | Each `Variable` becomes a `BruijnIndex`. Names stay on `Lambda.param_name`. Unbound name → error. |
| 2 | `banf_shape.shape` | Reduces only where the term doesn't have BANF's shape yet. |
| 3 | `banf_rename.rename` | Renames binders: fixed structural names, no shadowing. |
| 4 | `banf_translate.convert` | Reads the shaped term into BANF; `TranslationError` with a source location on any mismatch. |

Golden tests approve the shaped term as `name.shaped.oymo` (next to BANF and LLVM) and
check it translates to the same BANF.

#### The principle: translation only reduces

`shape` runs term reductions (beta, built-ins such as `$fix`, projection, `if`) until
each position has BANF's shape; `convert` only reads the result.

- **No defaults.** An omitted form is `Empty`, never `void`. A position needing a form
  rejects it ("form must be written").
- **Nothing inferred.** Every form BANF stores is in the source, return forms included;
  every parameter list and form is written once.
- **Unneeded forms are dropped**, not rejected, where BANF has no slot (on the `f`
  binder, on a data definition).
- **A form is not a type.** A written form replaces a computed one, never checked
  (a let's form, a formed atom). `banf.verify` checks names and counts, never forms
  ([no checks](#a-generated-ir-no-checks-for-user-mistakes)); `llvm_translate` rejects
  a replaced form whose LLVM type differs.
- A term without BANF's shape after reduction is rejected; the source fixes it.
- Why: [Translation only reduces](#translation-only-reduces),
  [plan_banf_explicit.md](implemented/plan_banf_explicit.md).

#### 1. `reduction.resolve`

Names → indices, by counting enclosing lambdas. The one-step reducer the next pass
uses: [reduce](#reduce-one-step-at-the-root).

#### 2. `banf_shape.shape`: reduce until each position has its shape

Each [position](#positions) wants certain constructors. The term there is reduced until
it has one, then its own positions are visited. Forms and binder kinds aren't checked
here (except `args`, through `k`); `convert` does that, so this pass needs no context.

##### Blockers

Some roots become a redex only after one part, the **blocker**, is reduced: in
`$fix g a`, `$fix g` must first unfold to a lambda.

| Term | Blocker |
|---|---|
| `{...} i` (callee already a struct) | `i` |
| `f a`, otherwise (including `$fix g`) | `f` |
| `s.l` | `s` |
| `if c then ...`, which is `{e, t} c` | `c` |
| `t~F` | `t` |
| `$fix g`, `$struct_to_fields s` | `g`, `s` (only the top: not under the lambda, not the fields) |
| `$fields_to_struct l` | the spine of `l`: each node, its `more`, and if `more` is `[01]`, its `label` and `rest`; never a `value` |
| `'name' a` (an opcode call), `$seq a` | `a`, then each of its fields |
| anything else | none |

- `step` reduces an apply's callee to a struct, then the index, then the root: in
  `{a = x} ((y -> y) [00])` the index must become a byte array first.
- An argument is reduced only when the callee is a struct, built-in or opcode, so
  ordinary applications stay lazy: `f ((x -> x) a)` keeps its argument.
- A built-in fires in `reduce` only once its argument has the needed constructor (a
  lambda, a struct, a literal field list). `unblock` reduces its blockers; if none
  changes, the call is stuck for good.

```
step(t) = reduce(t)           if reduce(t) is not t                  -- fire the rule at the root
        = t with blocker b'   if t has a blocker b, and              -- else unblock
                              b' = reduce_until_top_stable(b) is not b
        = t                   otherwise

reduce_until_top_stable(t) = reduce_until_top_stable(step(t))    if step(t) is not t
                           = t                                    otherwise
```

`reduce_until_top_stable` stops at every Lambda, Struct, ByteArray, BruijnIndex and
Builtin, and at stuck terms (`'add' {'i32', args.n, ...}`, `args.n`, `f.done {...}`,
`if t0 then a else b`).

- "Reduce `t` until it is X" = take `reduce_until_top_stable(t)`, *then* look at its
  constructor. Not the other way: `{f = x -> ...}.f args.n` is already an apply, but its
  callee must be reduced before it is a call such as `'add' {'i32', ...}`.
- A position already holding a wanted constructor isn't reduced further, so a
  let-bound struct stays a `MakeStruct`.

##### Positions

As numbered in [`banf_shape.py`](../src/oymo/oymomo/banf_shape.py):

1. The term, until a Lambda: `module -> <body>`.
2. `<body>`, until a Struct: `{label = <func>, ...}`.
3. `<func>`, until a Lambda: `f -> <func_body>`.
4. `<func_body>`, until a Struct: `{label = <block>, ...}`.
5. `<block>`, until a Lambda: `args -> <block_body>`.
6. `<block_body>`, a chain of lets ending in a terminal:
   ```
   block_body := terminal | (x -> block_body) <value>      -- a let
   terminal   := [bytes]                                    -- return a constant
               | args.label                                 -- return a param
               | $i, where i < k                            -- return a let
               | f.label <op_arg>                           -- jump
               | {<jump>, ..., <jump>} <atom>               -- branch (two jumps) or switch (three or more)
   ```
   `k` counts the lets since the block's `args` binder, so `args` is `$k`; it tells
   `args.label` from other projections. A let isn't reduced with
   `reduce_until_top_stable` (it is a redex that must be kept). Repeat:
   1. Let `(x -> rest) <value>`: take `reduce_until_top_stable(<value>)`. If it is an op
      (an apply, a struct, or a projection other than `args.label`), keep the let, visit
      the op (7), go on with `rest`. Else beta-reduce the let and go on.
   2. Else, if `step` changes the body, go on with that. This can make a let:
      `(x -> y -> rest) a b` leaves `(y -> rest') b`.
   3. Else visit the terminal's positions and stop.
7. `<value>`, a let's op: an apply's `<op_arg>` becomes a struct of atoms or a
   BruijnIndex (forwarding `args`); a struct's fields become atoms; a projection's
   struct is a blocker, already reduced.
8. `<jump>`, a branch arm or switch target (a field of `{a0, ..., an} c`): until
   `f.label <op_arg>`.
9. `<atom>`: until a ByteArray, `$i` with `i < k`, or `args.n`. `args` itself is not an
   atom: BANF passes a block's params one by one.

##### Consequences

- A let whose value isn't an op is beta-reduced: helpers are inlined,
  `let t = args.n in t` becomes `args.n`, a let-bound `if` lands in tail position.
- A term that can't get its shape is left for `convert` to report. The only error here
  is running out of fuel.
- **Fuel**: one unit per step, 10,000 total. `$fix (self -> self)` fails with "ran out
  of reduction steps".
- Nothing is flattened: a nested call stays nested and is an error (flattening would
  invent names).

#### 3. `banf_rename.rename`: fixed names and no shadowing

**Structural binders get fixed names.** Positions 1, 3, 5 are renamed so every shaped
program reads `module -> {main = f -> {entry = args -> ...}}`.

- `convert` checks each position by name; a wrong name means a wrong shape.
- On any root path each name appears once, so they never clash.
- A position `banf_shape` left unshaped isn't structural: its binder follows the let
  rule below, and `convert` reports the shape error.
- The fixed names don't reach BANF: `f.label` → a jump target, `args.n` → `banf.Var('n')`.

**Other binders keep their names unless they clash.** A let keeps `x` unless `x` is
*visible*: an enclosing binder's name (after renaming, so the fixed names count) or a
param label of its block. Then it becomes `x_L`, else `x__L`, and so on; `L` is its
level (number of enclosing binders; a block's first let is level 3).

| Lets | Become |
|---|---|
| `let t = ... in let t = ... in let t = ... in t` | `t, t_4, t_5` |
| two lets `n` with `args~{n = 'i8'}` | `n_3, n_4` (param labels become BANF `Var`s) |
| user's `t_4` after a renamed `t_4` | `t_4_5` |
| `t, t_5, t` | `t, t_5, t__5` |
| a let named `args` | `args_3` |
| a let named `f` | `f_3` |
| a let named `prim` | `prim` |

- Labels (struct, field, block, function, param) are never renamed; only param labels
  count as visible. The others are separate namespaces (`Jump.target`, `Call.function`,
  `GetData.name` are strings, not `Var`s), so a let `n` used as `{n = n}` keeps its name.
- Visible names are per path: sibling blocks can both have a `t` (LLVM adds `.1`, fine).
- Idempotent: a second run changes nothing.
- Linear: one set, add on the way down, remove on the way up.
- Rejected alternatives: [Design decisions](#renaming).

#### 4. `convert`: read the shaped term

##### Binders are found by index

In a block body with `k` lets so far, the binders above are, inside out: the lets
(`$0` … `$k-1`), `args` (`$k`), `f` (`$k+1`), `module` (`$k+2`). So `convert` classifies
each `BruijnIndex` by arithmetic and keeps no names. A let reference becomes a
`banf.Var` named after the BANF let already built.

##### What the shape is

- **Let**: `let x = op in rest`, i.e. `(x -> rest) (op)`. No form: the op's. A written
  form must be a literal and **replaces** the op's form unchecked:
  `let t0~'i32' = 'icmp_eq' {'i32', ...} in t0` gives `t0` form `i32` (`'icmp_eq'`
  gives `i1`). BANF prints `t0: i32 = icmp_eq 'i32', ...`; LLVM translation rejects it
  (LLVM types differ).
- **Atom**: a byte array with a literal form (`[01]~'i8'`), a let name, or
  `args.label`. Any atom may get a literal form, replacing its own (`args.n~'i32'`,
  `t~'i8'`). `let m~'i32' = args.n in m` isn't a BANF let (value not an op), so it is
  beta-reduced to `args.n~'i32'`.
- **`$seq {d1, ..., dn, x}`**, stuck because some `di` isn't a literal: the atom of `x`.
  - Every field must be an atom; the `di` are dropped (their lets are already in the
    block, and BANF keeps let order).
  - Stands wherever an atom does: op argument, jump argument, branch condition, return.
  - A let on a stuck `$seq` is a let on an atom, so `banf_shape` beta-reduces it
    (`_is_op`): each use gets the `$seq`. BANF and LLVM never see `$seq`.
- **Op**, only as a let's value:

  | Source | BANF op |
  |---|---|
  | `'opcode' {...}` | `OpcodeCall` |
  | `module.g {...}` (imported or defined) | `Call` |
  | struct literal of atoms | `MakeStruct` |
  | projection on an atom: `args.p.x` | `GetField` |
  | atom applied to an index: `args.p [01]` | `GetIndex` |
  | `module.errno` | `GetData` |

- **`GetIndex`** `s i`: `s` is an atom with a struct form (a let-bound struct, or a
  param like `args.p`).
  - `i` is read by `reduction.index_value`: any byte array literal, unsigned
    little-endian, form ignored (`[01]`, `[0100]`, `[01]~'i8'` are all 1).
  - `i` is reduced first like any op argument: `args.p ((i -> i) [01])` and
    `let i = [01] in args.p i` work.
  - A run-time value (`args.n`, a let bound to an op) or `''`: "An index must be a byte
    array literal, such as [01]." (LLVM's `extractvalue` needs a constant).
  - Past the last field → the last field, as in reduction: `args.p [02]` on `{i32, i8}`
    is `p.2`, an `i8`, lowered to `extractvalue ..., 1`.
  - A form with no fields: "Form i32 has no field at index 0.".
  - Binders are read only by label, so `args [00]` is an error.
- **Terminators**, only in tail position:
  - jump: `f.label {...}`;
  - branch: `if c then f.a {...} else f.b {...}` = `{f.b {...}, f.a {...}} c`, both arms
    jumps, labels ignored;
  - switch: `{f.a {...}, f.b {...}, f.c {...}} k`, three or more jumps, labels ignored;
  - return: an atom.

##### Labels name params, declarations and blocks

BANF reads `module`, `f`, `args` only by label, so every field needs a label in: the
module form, a signature's param form, the module body, a definition's blocks, the top
level of a block's param form, and the argument struct of a call, jump or opcode
("The module form needs a label on every field.").

Elsewhere (a value struct, a nested data form like `args~{p = {'i32', 'i8'}}`) fields
may be unlabeled, and several unlabeled fields aren't duplicates. BANF prints an
unlabeled field alone (`{i32, i8}`); LLVM names its `insertvalue` by index (`%"q.0"`).

##### Operands must be atoms

- `'add' {'i32', 'add' {'i32', ...}, ...}` is an error; bind the inner call with a let
  first (allowing it means flattening, i.e. inventing names).
- `$seq {d1, ..., x}` with atom fields is an atom (it stands for `x`).
- A struct literal in an opcode call is a form, not an operand (`'alloca' {{x = 'i32'}}`).

##### An op in tail position must be bound first

Write `args~{} -> let t0 = module.putchar {c = [41]~'i8'} in t0`, not
`args~{} -> module.putchar {c = [41]~'i8'}`. A BANF `Return` takes an atom; the
explicit `let t0` keeps every name in the source.

##### `if` only in tail position

`if c then [01]~'i8' else f.b {}` is an error. A let-bound `if` is substituted, so
`let t = if c then f.a {} else f.b {} in t` works; an `if` ending up as an operand is an
error. All of this holds for `{e, t} c` (same term).

- **Switch**: three or more fields. `{f.a {}, f.b {}, f.c {x = args.x}} args.k` is
  `switch k, a(), b(), c(x)`: jumps to field `k`, or the last field if `k` is past it.
  - BANF puts nothing on `k`'s form; LLVM translation needs an `iN` with room for the
    cases (`i1` holds 3 targets).
  - A let-bound switch is substituted into the tail, like an `if`.
  - One field: "A switch needs two or more fields; one is a jump.".
  - A block may be named more than once only with the same args ("A switch passes
    different args to 'a'."). See [plan_switch.md](implemented/plan_switch.md).
- A BANF `Branch` is a terminator with two targets. An `if` whose value is used needs a
  join block, written explicitly in the source.
- `if c then f.a {} else f.a {}` is valid BANF (Cranelift allows it). The LLVM backend
  rejects it: `a` would get two edges from one block, which an LLVM phi can't tell apart.

##### Binders can't be used as values

`f`, `args`, `module` alone are errors ("'args' cannot be used as a value."; the message
uses the fixed name), except `args` forwarded as a whole call or jump argument. So are
`module.g` and `$fix` without an argument ("$fix must be applied."). They have no
runtime value.

### BANF to LLVM

[`llvm_translate.py`](../src/oymo/oymomo/llvm_translate.py) maps BANF one-to-one onto LLVM:

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
| form `ptr` | opaque `ptr`; a pointer can't be a literal |
| tagged struct form | `[N x E]`, `<N x E>`, `<{...}>` (packed); a scalable vector is rejected (no llvmlite type) |
| `[2a000000]:i32` | `i32 42` (little-endian bytes → number) |
| block param, one predecessor | the value that predecessor passes (no phi) |
| block param, several predecessors | `phi`, one incoming value per edge: `%v = phi i32 [%x, %a], [0, %b]` |
| `GetData` | `load` from the global |
| `GetField`, `GetIndex` | `extractvalue` (`args.p [00]` gives the same IR as `args.p.x`) |
| `MakeStruct` | one `insertvalue` per field, named `%q.x` after the let and field |
| defined `Data` | read-only `constant` with initializer: `@answer = constant i32 42` |
| imported `Data` | `external constant` |
| defined `Cell` | writable `global`: `@counter = global i32 41`; without `init`, `zeroinitializer` |
| imported `Cell` | `external global [0 x i8]` |
| `CellAddress` | the global itself: `ptr @counter` |

- Every symbol is declared first, so functions call each other in any order.
- Unreachable blocks are not emitted, so phis list only existing blocks.
- Value names are the BANF let names (`%t0`), easy to match against BANF.
- Constants: an `iN` constant needs `(N + 7) // 8` bytes (`i1`: one byte, 0 or 1). LLVM
  stores the number in the data layout's byte order, so a big-endian target (`E-...`)
  needs no swap. No struct constants yet.
- Data initializers follow the constant rules ("A i32 constant needs 4 bytes."); struct
  data forms are rejected for now, cells' too.
- Every global's address is the opaque `ptr`, like every other pointer.
- **No conversions.** A formed name or a let with a written form is used as-is if its
  LLVM type equals the original's (e.g. a struct form with other labels, same field
  types). Else rejected: "'n' is formed as i32, but its LLVM type is i8.", "Let 't0' is
  formed as i32, but its op gives i1.". No `bitcast`, widening or narrowing.

## Error messages

Grouped by the stage that raises them; `<…>` varies. Every translation error carries a
source location. Search the source for the message text to find where it's raised.

### Names and resolution (`reduction.py`)

| Message | Cause | Fix |
|---|---|---|
| `Unknown name '<x>'.` | A variable that no lambda or let binds. | Bind it, or check spelling. Built-ins need `$` (`$fix`). |

### Shaping (`banf_shape.py`)

| Message | Cause | Fix |
|---|---|---|
| `Did not reach BANF shape: ran out of reduction steps.` | More than 10,000 steps, usually a term that never stops reducing, e.g. `$fix (self -> self)`. | Make sure recursion goes through `module.f` calls, not `$fix` loops. See [Translation](#consequences). |

### Program shape (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `Expected a program of the shape module~{...} -> {...}.` | The top level isn't a lambda around a struct. | See [Programs](#the-shape-of-a-program). |
| `The module binder needs a struct form, such as module~{}.` | `module -> {...}` without a form. | Declare every symbol: `module~{main = => 'i32'} -> ...`. |
| `'<f>' is defined but not declared.` | A body field with no `module` declaration. | Add `f = => R` (function) or `f = 'iN'` (data) to the module form. |
| `'<f>' declares no params, so it must be defined.` | Declared `=> R` but missing from the body. | Define it, or declare it with params to import it. |
| `'<f>' declares its params; a definition takes them from its entry block.` | Declared `{...} => R` and also defined. | Declare a defined function as `=> R`; params go on its entry block. |
| `'<x>' is declared as data, so its definition must be a byte array.` | A data declaration defined as something else. | Define it as bytes: `answer = [2a000000]`. |
| `'<x>' is declared 'ptr', so its definition must be 'global' {form, init}.` | A cell defined as something else. | Define it: `counter = 'global' {'i32', [29000000]~'i32'}`. |
| `'<x>' is defined by 'global', so it is declared 'ptr'.` | A `'global'` field whose declaration isn't `'ptr'`. | Declare it `counter = 'ptr'`. |
| `'global' takes a form and an optional init, such as 'global' {'i32'}.` | e.g. `'global' {}`. | Write the form. |
| `'global': init must be <n> bytes for <form>, got <m>.` | An init of the wrong width. | Write `(N + 7) // 8` bytes. |
| `'global' must be a definition, such as counter = 'global' {...}.` | `'global'` in a block. | Define a cell in the module body. |
| `module.<x> is a cell's address, an atom: use it directly, as in 'load' {'i32', module.<x>}.` | `let c = module.counter in ...`. | Use `module.counter` where the pointer is needed. |
| `module.<x> is a cell, so it cannot be applied.` | `module.counter {}`. | Load from it: `'load' {'i32', module.counter}`. |
| `<what> needs a label on every field.` | An unlabeled field where a label names something (module form, blocks, params, call/jump/opcode arguments). | Add labels. See [Translation](#labels-name-params-declarations-and-blocks). |
| `<what>: function forms nested inside other forms are not supported.` | A function form inside a data form, or as a param/result. | Not supported yet. See [Programs](#nested-function-forms-are-rejected-for-now). |
| `<what>: a function form needs a struct form as its param.` | e.g. `g = 'i8' => 'i32'`. | Use `{c = 'i8'} => 'i32'`. |

### Forms (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `<what>: form must be written.` / `Byte array: form must be written.` | A form is needed but omitted (`Empty`); nothing infers one. | Write it: `[01]~'i8'`, `args~{n = 'i32'}`. See [oymomo](#omitted-forms-are-empty). |
| `<what>: form must be a literal, got <form>.` | A form that didn't reduce to a named form or struct of them. | Use a literal like `'i32'` or `{x = 'i32'}`, or make sure it reduces to one. |
| `<what>: 'array' form must be {'array', count, element}.` | An array or a vector with other than two parts. | Write `{'array', [03000000]~'i32', 'i32'}`. |
| `<what>: 'array' count must be a literal of an integer form, such as [03000000]~'i32'.` | A bare byte array or a run-time value as `count`. | Form the count: `[03000000]~'i32'`. |
| `<what>: 'vector' count must be above 0.` | A vector of no elements. | Give it a count of 1 or more. |
| `<what>: 'vector' element must be an integer form or 'ptr', got <form>.` | A vector of structs or arrays. | Use an array instead. |
| `<what>: a scalable vector can't be inside a struct, a packed struct or an array.` | A scalable vector nested in an aggregate. | Keep it a value or param of its own. |

### Block bodies (`banf_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `Expected an atom: a byte array, a let name, or args.label.` | An operand that is an op, e.g. a nested call. | Bind it first: `let t = 'add' {'i32', ...} in ... t ...`. See [Translation](#operands-must-be-atoms). |
| `A let's value must be an op, not an atom.` | A let in BANF position whose value is an atom. | Use the atom directly. |
| `An if must be in tail position.` | An `if` used as a value. | Branch to blocks and join explicitly. See [Translation](#if-only-in-tail-position). |
| `A switch needs two or more fields; one is a jump.` | `{f.a {}} k` in tail position. | Write the jump: `f.a {}`. See [Translation](#if-only-in-tail-position). |
| `A switch needs two or more fields.` | `{} k` in tail position. | Give it targets. |
| `Every field of a switch must be a jump, such as f.a {}.` | `{f.a {}, [01]~'i8', f.b {}} k`. | Make each field a jump. |
| `A jump must be in tail position.` | `f.label {...}` used as a value. | Put the jump last. |
| `Cannot jump to the entry block.` | `f.entry {...}`. | Jump to a separate loop header. See [BANF](#the-entry-block-cannot-be-jumped-to). |
| `'<args>' cannot be used as a value.` | `f`, `args` or `module` used alone. | Use `args.n`, `module.g {...}`, `f.b {...}`; `args` may only be forwarded whole as a call/jump argument. |
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
| `$fix must be applied.` / `$<name> must be applied.` | A built-in used without an argument. | Apply it: `$fix g`. |
| `$<name> has no opcode, so it must reduce away: its argument must reduce to <needs>.` | A built-in whose rule didn't fire. | Make its argument reduce to what the rule needs (e.g. a struct). |
| `Unknown built-in '$<name>'.` | Not in `BUILTINS`. Opcodes have no `$`. | Check spelling; an opcode is written `'add' {'i32', a, b}` ([Opcodes](#opcodes)). |
| `$seq needs a value.` | `$seq {}`. | Write the value last: `$seq {s, p}`. |
| `$seq: every field must be an atom.` | A stuck `$seq` with a field that isn't an atom, e.g. `$seq {s, {x = p}}`. | Bind it with a let first. |
| `The argument to $seq must be a struct literal.` | e.g. `$seq args.n`. | Write the fields: `$seq {s, p}`. |
| `Target has no implementation of '<name>'.` | The LLVM `Target.opcodes` lacks the op. | Add it to `llvm_opcodes.py`. |

### Opcodes

| Message | Cause | Fix |
|---|---|---|
| `Unknown opcode '<name>'.` | `'<name>' {...}` with a name not in `OPCODES`. | Check spelling against [Opcodes](#opcodes). |
| `'add' cannot tell its result form from its fields.` | The fields don't give the result form: a wrong number of fields, or a non-literal where the form goes (`'add' {f, a, b}` with `f` not reducing to a byte array). | Write the fields in LLVM's order, with a literal form: `'add' {'i32', a, b}`. |
| `The argument to 'add' must be a struct literal.` | e.g. `'add' args`. | Write the fields: `'add' {'i32', a, b}`. |

### BANF verifier (`banf_terms.py`)

| Message | Cause | Fix |
|---|---|---|
| `<what> takes <n> arguments, got <m>.` | Wrong argument count. | Match the callee's params. |
| `A switch needs a target.` | A BANF `Switch` with no targets. | Give it targets. |
| `A switch passes different args to '<b>'.` | `{f.a {x = [01]~'i8'}, f.b {}, f.a {x = [02]~'i8'}} k`. | Pass the same args each time `a` is named (an LLVM phi needs equal entries from one block), or use another block. |
| `Form <form> has no field at index <i>.` | `GetIndex` on a form with no fields. | Index a struct with at least one field. |
| `A pointer can't be a literal.` | `[0000000000000000]~'ptr'`. | Get a pointer from `'alloca'`, `'getelementptr'` or a call. |
| `'load' takes 2 fields, got <n>.` / `'store' takes 2 fields, got <n>.` | e.g. `'store' {v}`. | `'load' {form, ptr}`, `'store' {value, ptr}`. |
| `'load' expects ptr: ptr, got <form>.` | The pointer field isn't of form `ptr`. | Pass a pointer. |
| `'store': value must have a form, such as [01000000]~'i32'.` | A bare byte array stored. | Write its form: `[2a000000]~'i32'`. |
| `'<s>' is the result of a store; only $seq can use it.` | A store's let used as a value. | Use it only in `$seq {s, ...}`. |
| `'<x>' is not a cell.` | A `CellAddress` naming something else. | Declare it `'ptr'`. |

### LLVM (`llvm_translate.py`)

| Message | Cause | Fix |
|---|---|---|
| `'<n>' is formed as i32, but its LLVM type is i8.` | A formed atom whose form maps to a different LLVM type. | Forms don't convert; use an opcode such as `'zext'`. |
| `Let '<t0>' is formed as i32, but its op gives i1.` | A let's written form differs in LLVM type from its op. | Remove the form, or convert explicitly. |
| `A i32 constant needs 4 bytes.` | Wrong byte count for an `iN` constant (`(N + 7) // 8` bytes). | Write the right number of bytes: `[2a000000]`. |
| `Constant does not fit in <form>.` | e.g. an `i1` byte that isn't `00` or `01`. | Fix the bytes. |
| `Only integer constants are supported, got <form>.` | A struct constant. | Not supported yet. |
| `A branch cannot have the same block as both targets.` | `if c then f.a {} else f.a {}`; valid BANF (Cranelift allows it). | Use two blocks (LLVM phis can't tell the edges apart). See [Translation](#if-only-in-tail-position). |
| `Switch selector must be an integer form, got <form>.` | A switch on a non-`iN` value. | Switch on an integer. |
| `'getelementptr': index <i> into <form> must be a literal 'i32' below <n>.` | A run-time or out-of-range index into a struct. | Index a struct field with a literal `[01000000]~'i32'`. |
| `'getelementptr': index <i> goes into <form>, which has no parts.` | More indices than the form has levels. | Drop the extra index. |
| `'<name>': <what> must have a form, such as [01000000]~'i32'.` | A bare byte array as a count, pointer or index. | Write its form: `[1000000000000000]~'i64'`. |
| `'getelementptr' expects a pointer, got <type>.` | The pointer field isn't a `'ptr'`. | Pass a pointer. |
| `Form <vscale x 4 x i32> has no LLVM type in llvmlite.` | A scalable vector reached LLVM translation. | Not supported by llvmlite. |
| `A switch on i1 has 4 targets; it holds 3.` | More targets than the selector's form has values, plus one for the default. | Widen the selector, e.g. `'zext' {'i1', s, 'i8'}`. |

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

The whole pipeline (what the golden test does):

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

Run with `hatch run python your_script.py`. On failure, see
[Error messages](#error-messages).

### Add a golden test

1. Write `tests/goldens/<name>.oymo`, starting with the line `language oymomo`.
2. Add `run_golden_test('<name>')` to `test_goldens` in
   [`golden_test.py`](../tests/golden_test.py).
3. Run `hatch test tests/golden_test.py`. The first run writes
   `<name>.shaped.oymo.received`, `<name>.banf.received`, `<name>.ll.received`
   (approvaltests). Review, then drop `.received` to approve.

The test also rewrites the `.oymo` source into its pretty form (checking it gives the
same BANF) and checks the shaped output compiles to the same BANF.

### Add an opcode

1. [`opcodes.py`](../src/oymo/oymomo/opcodes.py): add an `Opcode` to `_generate()`
   (`_binary` for `{form, a, b}`, `_convert` for `{form, value, to}`, or a new shape),
   with `form_of(fields)` and `evaluate(fields)`. It reads fields by position, in LLVM's
   operand order, and returns None where it can't read them or LLVM has no defined result.
2. [`llvm_opcodes.py`](../src/oymo/oymomo/llvm_opcodes.py): add its LLVM code, reading the
   BANF fields by position (`_BINARY`, `_COMPARE` or `_CONVERT` for existing shapes).
3. Don't name it `call`, `jump`, `branch`, `switch` or `return` (`banf_terms.py` checks).
4. A `pure` opcode folds; `test_fold_matches_llvm` checks `evaluate` against LLVM.
5. Add tests in `opcodes_test.py` and `llvm_translate_test.py`; a test checks both tables
   have the same names.
6. Update [Opcodes](#opcodes).

### Add a built-in reduction rule

1. [`reduction.py`](../src/oymo/oymomo/reduction.py): add the name to `BUILTINS` and a
   case to `reduce` that fires only when the argument has the needed constructor
   (root-only: `reduce` never reduces a part).
2. [`banf_shape.py`](../src/oymo/oymomo/banf_shape.py): add a case to `unblock` reducing
   the parts the rule reads (its blockers). Parts not reduced there stay lazy. Return `t`
   itself if no part changed.
3. The parser accepts any `$name`; `convert` rejects a leftover reduction-only built-in.
   Add what its argument must reduce to in `banf_translate._MUST_REDUCE_TO` (for the message).
4. Add tests in `reduction_test.py` and `banf_shape_test.py` (what is reduced, what stays
   lazy, stuck calls keep what they reduced); update [oymomo › Built-ins](#built-ins).

### Write a design change

Larger changes start as a plan: `docs/plan_<name>.md`, one commit per step, listed in
[plans.md](plans.md) (open until every step is done, then closed and moved to
`docs/implemented/`).

### Update the notes when a plan lands

Each step updates the section of `docs/notes.md` it changes:

| Change to | Update |
|---|---|
| syntax, precedence, printer | [oymomo syntax](#oymomo-syntax) |
| forms, built-ins, `reduce` | [oymomo](#oymomo-forms-built-ins-reduction) |
| program shape, `module`, declarations | [Programs](#programs) |
| opcodes | [Opcodes](#opcodes) |
| BANF classes, ops, printer | [BANF](#banf) |
| shaping, renaming, `convert`, LLVM | [Translation](#translation-oymomo--banf--llvm) |
| a new or changed error message | [Error messages](#error-messages) |
| the reason for a choice, rejected alternatives | [Design decisions](#design-decisions) |
| a new word | [Glossary](glossary.md) |

## Design decisions

Why things are as they are, and what was rejected. History of larger changes: the
`plan_*.md` files in [plans.md](plans.md).

### Type, Form, Layout are three words

oymomo and BANF know only forms; types belong to higher layers, layouts to the backend.
Keeping the words apart stops a backend fact ("i32 is 4-byte aligned") from leaking into
oymomo, where `[2a000000]~'i32'` only means "these bytes, read as the form i32".
→ [Overview](#type-form-layout)

### BANF does not depend on LLVM

How an opcode becomes LLVM instructions is a backend detail: BANF names the opcode
(`add`), the `Target` supplies the code. No `byte_order` field in `Target`: `data_layout`
already says it, and two sources could disagree. → [Overview](#where-the-code-lives)

### Flat files with prefixes

The stages are small; a prefix (`banf_`, `llvm_`) shows the stage as clearly as a
subpackage, without extra `__init__.py` files and import paths.

### Brackets have one job each

`{}` structs, `()` grouping, `[]` bytes, `''` text bytes, `""` names, so the parser never
guesses: `(` always groups, `{` is always a struct, `[` always bytes. Structs moved from
the earlier plan of `[]` to `{}` (as in C, Rust), freeing `[]` for byte arrays.
→ [oymomo syntax](#brackets-one-job-each)

### Struct, not record

Fields keep their order, and the order sets the layout: `{x = 'i32', y = 'i8'}` is
`{i32, i8}` in LLVM, `{y = 'i8', x = 'i32'}` is `{i8, i32}`. "Struct" says that;
"record" suggests an unordered set of labels. → [oymomo syntax](#structs)

### The name `Project`

`s.x` is the term `Project`: a one-word verb like `Apply`, and TAPL's name for `t.l` on
records (projection, E-ProjRcd); the reducer already called its step `project`.

History: first `Select`, then `FieldAccess` (pairs with the `Field` class; what C, Rust,
Java call `s.x`), with `Project` rejected as type-theory jargon. We came back to it: this
is a lambda calculus, and every other term is named after its operation, not its look.

Rejected:
- `Select`: unclear.
- `FieldAccess`: names the syntax, breaks the verb pattern.
- `Access`, `Read`: sound like memory operations next to LLVM.
- `Field`: taken by the `Field` class.
- `Member`: C++ flavored, suggests methods.
- `Get`: reads like a function call.
- `Dot`: names the syntax, not the meaning.
- `Projection`: a noun among verbs.
- `Pick`, `Take`, `Pluck`, `Extract`, `Lookup`, `Focus`.

`Project` stays a term next to struct apply (`s [00]`) because BANF's shapes and the
printer match on it. Struct apply needed no new syntax or term: `s i` is already an
`Apply`. → [oymomo syntax](#projection-and-struct-apply),
[plan_struct_apply.md](implemented/plan_struct_apply.md)

### The lambda arrow

`->` is easy to type; `→` reads like math. Both accepted; the printer prints `→`.

### Forms are terms

One syntax and one set of terms for values and forms, so later stages compute forms
with the same machinery as values. → [oymomo](#forms-are-terms),
[plan_term_as_form.md](implemented/plan_term_as_form.md)

### Omitted forms are `Empty`, with no default

Quick sketches stay short, and nothing is silently defaulted: each position says what
`Empty` means or rejects it. It used to mean `void`; dropped so translation never fills
in a value the source didn't write. → [oymomo](#omitted-forms-are-empty),
[plan_banf_explicit.md](implemented/plan_banf_explicit.md)

### `~` binds a term to a form

`e~F` reads "`e` shaped as `F`".

Rejected:
- `:`: nearly every language reads `e : T` as a type annotation, and a form is not a
  type: nothing checks it; a param's form replaces the argument's
  ([Type, Form, Layout](#type-form-layout)).
- `@`: `@name` is an LLVM global, and LLVM IR sits beside oymomo throughout.
- `as`: a new reserved word, reads as a cast, and `f a as F` looks like `(f a) as F`
  though `~` binds tighter than application.

Written without spaces (`x~'i32' -> x`) so it reads as part of its operand. One ASCII
character, so no Unicode alias. → [oymomo syntax](#precedence)

### `Formed` binds tighter than application

Follows the rule "values bind tighter than things that reduce" ([Precedence](#precedence)).

Rejected: `~` below application, like `:` in Haskell, OCaml, Lean (`f a~g b` =
`(f a)~(g b)`): it made `~` the only value operator looser than application.
→ [oymomo syntax](#precedence), [plan_annotation.md](implemented/plan_annotation.md)

### A byte array is only its bytes

`[01]~'i8'` is `Formed(ByteArray([01]), 'i8')`, not a literal with a built-in form. So
every `~` not on a binder is one term with one meaning, and beta reduction alone gives a
dynamic form. The same bytes can have many forms (`[01000000]`: `'i32'` 1 or
`{a = 'i16', b = 'i16'}`).

### Byte arrays are bracketed hex

oymomo has only byte arrays, so literals are bytes, not numbers. `[]` was freed when
structs took `{}`; the brackets bound the literal, so no prefix or quotes.

Rejected:
- a prefix sigil (`#2a000000`, also `%`, `$`, `@`): needed `_` separators and a `_` line
  continuation;
- `0x...`: reads as an integer and hides the byte order;
- backticks: look like quoting;
- juxtaposed literals: juxtaposition is already application.

### Byte arrays are always little-endian

`[2a000000]~'i32'` is 42 on every target.
- Fixed, not a default: with no integer literals, the byte order is what gives a literal
  its number; with an overridable default one source would mean two numbers. Same idea
  as WebAssembly memory and the `.bc` encoding: the encoding is fixed; the machine's byte
  order is a target detail.
- An evaluator (beta reduction plus opcodes) can run `'add'` without a target and agree
  with compiled code, so constant folding is safe.
- A big-endian target still gets big-endian bytes in memory: the translator emits the
  number (`i32 42`) and LLVM lays it out per `data_layout`.
- Later cost: once opcodes reinterpret memory (store an `i32`, read bytes), a big-endian
  target sees bytes in another order than the literal. Then either byte-swap loads and
  stores (as WebAssembly does) or call those opcodes target-dependent.

### Text byte arrays

`'` was unused; `"` is taken by quoted names. No escapes, and `\` is kept out of the
allowed characters to leave room for escapes later.

The printer uses `'...'` only for a byte array with no form, all text bytes, ≤ 128
bytes: a written form (`[41]~'i8'`) usually means a number, so hex stays; a long blob
reads better as grouped hex. The limit is fixed, not `width`, so output doesn't depend
on layout settings.

### Quoted names

LLVM does the same (`@main` vs `@"foo bar"`), so oymomo names map directly to symbols,
including mangled names from higher layers. SQL also uses `"..."`. Plain identifiers
stay ASCII: no Unicode identifier rules or confusable characters.

Cost: `"` is unavailable for string literals; oymomo has none. Rejected: Zig-style
`@"..."`, only worth it if strings come.

### `$` for built-ins and indices

`$` marks a reference no user name binds: `$0` by position, `$fix` by oymomo. User names
are always bare. `#` stays unused (comments kept `//` after byte arrays moved to `[]`).

### `let` is sugar

No new term: the parser builds `Apply(Lambda(x, body), e)`. In `(t0 -> rest) (op)` the
value comes after the whole rest of the block, far from its name; with `let`, a chain
reads top to bottom, like BANF.

### Function forms are their own term

`FunctionForm(param, result)` used to be a tagged struct
`{tag = ' => ', param = P, result = R}`. Every consumer had to tell it from a plain
struct (shape, field order, tag checks), a hand-written struct could become a function
form by accident, and BANF output and errors showed the encoding. Now a struct is always
a struct.

Rejected: a tag member on `Struct` (nominal typing; maybe later), and `Lambda` as a Π
type (keeps `Lambda` free for form constructors). Named `FunctionForm`, not `Arrow`: it
names the meaning and leaves room for a separate function type.

`=>`, not `->`: a different arrow tells a form from a term at a glance (in
`module~{putchar = {c = 'i8'} => 'i32'} -> {...}`, `=>` is in a form, `->` binds a
lambda), and a binder's form safely ends at the first `->`.

### The printer lives in `printer.py`

Not in the tests, so any stage can print terms. Compact mode keeps tests short and
reading like source; pretty mode round-trips, so goldens are valid source.

### Built-ins

`$fix` is a global constant, not a name in `module` and not a binder.
- **Not in `module`**: built-ins and machine instructions are not symbols. Neither `$fix`
  nor an opcode ever becomes an LLVM symbol, while every `module` entry does
  (`@putchar`, `@fact`). BANF keeps the split: `OpcodeCall` vs `Call`.
- **Not a binder**: a binder's index depends on depth (programs used to start with
  `prim ->`, and `prim` was `$3` under three lambdas), so `reduce`, which sees only the
  term, couldn't recognize `prim.fix`. A `Builtin` is the same at any depth.
- **Separate constants**, not fields of one global struct: no `$` value to project from,
  apply or unpack.
- **`fix` is a built-in, not its own term**: a new built-in is one table entry, not a
  term, a grammar rule, a reserved word and cases in five modules.
- **Every built-in is reduction-only**: machine instructions are opcodes. Each
  built-in's `needs` gives its own error message.

→ [oymomo](#built-ins), [plan_builtin.md](implemented/plan_builtin.md)

### One `module` binder

One binder declares every symbol, imported or defined, instead of `decls` (imports) and
`defs` (definitions). With two:
- a defined function's return form had nowhere to be written, so it was inferred;
- calls went through `decls.f` or `defs.f` depending on where `f` lived;
- a name in both was an extra error.

With one, the form lists every symbol with its return form, and the declaration's shape
says which are imported.

Rejected: an empty byte array as a "no body" sentinel for imports (a magic value; the
declaration's shape says the same).

Not done: cross-module calls by name. → [Programs](#module-declares-every-symbol)

### Functions are structs of blocks

Plain oymomo (lambdas, structs, application): no new syntax for blocks and jumps, and
every name in the BANF output comes from the source.

### One argument, always a struct

oymomo stays a one-argument lambda calculus, and labels name the arguments at every call
site (`{minuend = x, subtrahend = y}`), so argument order can't be mixed up silently.
Expanded one level, in oymomo → BANF, so BANF stays LLVM-shaped and BANF → LLVM has no
expansion of its own. A deeper expansion would invent names like `p.x`, and LLVM passes
struct values anyway.

### Return forms are declared, not inferred

Written once, where the symbol is declared; nothing computed. Inference had to iterate
over the module to a fixed point, and a function with no base case
(`entry = args~{} -> let t = module.g {} in t`) had no return form at all.

### Opcodes as LLVM writes them

One opcode per LLVM instruction, form as a field (as in `add i32 %a, %b`): about 25
entries instead of a generated name per signature. Fields are positional in LLVM's
operand order, so the order to remember is LLVM's, which the BANF and LLVM printouts
show. An opcode declares no params: it reads fields by position (`form_of`, `evaluate`,
its LLVM code), so BANF needs no opcode schema and stores the result form in the call.
Operand widths are not compared with `form`. → [Opcodes](#opcodes)

### BANF

- **Basic blocks**: one BANF block → one LLVM block, one let → one instruction.
- **Block params instead of phi**: a join block declares what it receives, so each edge
  says what flows along it.
- **Closed blocks**: each block reads on its own; no dominance or live-in analysis to
  know what's in scope.
- **Entry block can't be jumped to**: LLVM's entry block can't have predecessors.
- **Forms only where needed**: ops carry no form, as in Cranelift; a stored `MakeStruct`
  form would repeat a full struct form on every line.
- **`name` on the binding**, not in `(name, binding)` tuples: simpler to carry and print.
- **`Data`, not `Global`**: every binding becomes an LLVM global.
- **Printer**:
  - no `let` keyword: a block holds only lets plus one terminator, and every terminator
    starts with a keyword;
  - assembly-style opcodes; `call` with parens so it doesn't read like oymomo application;
  - indentation instead of braces: labels at 2, instructions at 4, so the column tells a
    line's kind. At column 0, `entry(a: i32):` would look like the signature
    `putchar(c: i8): i32`, and nothing would mark where a function ends.

→ [BANF](#banf)

### Translation only reduces

No defaults, nothing inferred, unneeded forms dropped, a written form replaces a
computed one. A term not in shape is rejected and the source fixes it, so every name and
form in BANF comes from the source.
→ [Translation](#the-principle-translation-only-reduces),
[plan_banf_explicit.md](implemented/plan_banf_explicit.md)

Consequences:
- **Operands must be atoms**: nested calls would mean flattening into lets, i.e.
  inventing temporary names. That is normalization.
- **A tail op must be bound first**: a BANF `Return` takes an atom; a tail op would make
  the translator invent a name.
- **`if` only in tail position**: a BANF `Branch` is a terminator; an `if` whose value is
  used needs a join block, written explicitly. Two different targets because an LLVM phi
  can't tell two edges from one block apart.
- **Binders aren't values**: no runtime value; `module` is not a struct anything could build.

### Renaming

Structural binders get fixed names (`module`, `f`, `args`) so `convert` can check shape
by name. Other binders keep their name unless it's visible, then get a level suffix.

Rejected:
- one set per function, to avoid LLVM's `.1`: renames lets that clash only with a sibling
  block, and LLVM names don't matter;
- checking every label: separate namespaces, and collecting them needs an extra pass;
- renaming params: param labels appear in the block's form, in `args.n` and in every
  jump's `{n = ...}`, so renaming rewrites labels in many places;
- `_<level>_<original>` for every binder: unique without a set, but renames every let,
  even ones that clash with nothing;
- `name$level` (`n$3`): needs quotes, and `$` now starts a BruijnIndex or Builtin.

→ [Translation](#3-banf_renamerename-fixed-names-and-no-shadowing)

### Memory as LLVM's defaults

- A `'load'` or `'store'` carries no `align`: LLVM assumes the form's ABI alignment.
- Byte order is the target's; a struct's layout (padding, offsets) is LLVM's for the target.
- On a big-endian target, storing `[2a000000]~'i32'` and loading `'i8'` at the same
  pointer gives `[00]`, unlike byte array literals, which are little-endian everywhere
  ([Byte arrays are always little-endian](#byte-arrays-are-always-little-endian)).
  Memory has no literals, so the two never meet.
- Nothing checks an access: a misaligned or dangling pointer is undefined, as in C.

→ [plan_memory.md](implemented/plan_memory.md) decision 12

### LLVM translation converts nothing

A formed name or let with a written form is used as-is only if its LLVM type matches;
else it's rejected. No `bitcast`, widening or narrowing: a form is not a type, and
conversions are explicit opcodes.
