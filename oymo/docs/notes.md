# Oymo design notes

Informal notes on decisions, tradeoffs, and things not to forget. Each decision
says what was chosen, shows an example, and says why.

## Terminology: Type, Form, Layout

- Type: semantic, program-level meaning.
- Form: logical structure, the arrangement of components.
- Layout: physical memory representation.

A type may have several forms, and a form may have several layouts.

```
Bool
  type: Bool
  form: 'i1'
  LLVM layout: i1

Int32
  type: Int
  form: 'i32'
  LLVM layout: i32

Point
  type: Point(x: Int, y: Int)
  form: {x = 'i32', y = 'i32'}
  LLVM layout: { i32, i32 }
```

Why three words: the kernel (oymomo) and BANF only know forms. Types belong to
higher layers, and layouts belong to the backend (LLVM). Keeping the words apart
stops a backend detail like "i32 is 4-byte aligned" from leaking into the
kernel, where `[2a000000]: 'i32'` only says "these bytes, read as the form i32".

The difference between Form and Type
- Form does not have form-check like type-check. Valid application example: (x:Int->x) 'hello':'Str'. This evaluates to 'hello':'Int'.
- Function param form is used just to replace passed arguments form, nothing else.
- Form is useful when generating machine code.

## Pipeline

```
oymomo source --parse--> oymomo terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

`banf_translate` is itself a pipeline (see "oymomo to BANF" below):
```
terms --bruijn.resolve--> BruijnIndex terms --banf_reduce.shape--> BANF-shaped term
      --banf_rename.rename--> no shadowing --banf_translate.convert--> BANF
```

- oymomo: the lambda-calculus kernel language. Surface syntax in `grammar.py`,
  terms in `terms.py`.
- BANF: a first-order IR shaped like LLVM, with block params instead of phi nodes
  (see "BANF" below).
- LLVM: generated with llvmlite.

### Files are flat, with prefixes
Everything sits in `oymo/src/oymo/oymomo/`:
`bruijn.py`, `banf_terms.py`, `banf_opcodes.py`, `banf_reduce.py`, `banf_rename.py`,
`banf_translate.py`, `llvm_opcodes.py`,
`llvm_translate.py`, and tests use the same names in `tests/oymomo/`.
- Why flat: the stages are small, and a prefix shows the stage as clearly as a
  subpackage without the extra `__init__.py` files and import paths.
- Rule: only `llvm_*.py` imports llvmlite, and no `banf_*.py` imports an
  `llvm_*.py`. BANF depends only on `oymomo.terms`.

### BANF does not depend on LLVM
Anything LLVM needs that BANF doesn't have is passed to the LLVM translator:

```python
Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=DEFAULT_OPCODES)
```

- No `byte_order`: byte arrays are always little-endian (see "Byte arrays"), and the
  target's own byte order comes from `data_layout` (`e` or `E`). A separate field
  could disagree with it.
- `opcodes` maps each opcode name to the LLVM instructions that implement it.
- Why: how each opcode becomes LLVM instructions is a backend detail, so BANF
  only names the opcode (`add_i32`) and the target supplies the implementation.

## Punctuation

```
{}  structs (ordered fields): {x = e}, also struct forms {x = 'i32'}
()  grouping only
[]  byte arrays [2a 00 00 00]
''  text byte arrays 'Hello'
```

Why each bracket has one job: the parser never has to guess. `(` always groups,
`{` is always a struct, and `[` is always bytes.

## Kernel syntax decisions

Surface syntax of the oymomo kernel lambda calculus:
```
x: 'i32' -> body            Lambda
f a b                        Apply
{x = e1, y = e2}             Struct
{e1, y = e2}                 Struct with an unlabeled field
s.x                          Project
s [00]                       Apply: the field at position 0
if c then a else b           If
let x = e in body            sugar for (x -> body) e
$add_i32, $fix g             Builtin, applied like a function
[2a 00 00 00]                ByteArray
e: 'i32'                    Formed
{c = 'i8'} => 'i32'          FunctionForm
// comment                   line comment
```

### Struct, not record
Fields keep their declaration order, and the order matters for layout:
`{x = 'i32', y = 'i8'}` and `{y = 'i8', x = 'i32'}` are different forms with different LLVM
types (`{i32, i8}` vs `{i8, i32}`). "Struct" says that; "record" suggests an
unordered set of labels.

### {} for structs, not []
Structs are written with braces, as in C and Rust: `{label = e, ...}`. A struct
form is an ordinary struct too: `{x = [01]: 'i8'}` is a value, `{x = 'i8'}` is its
form (see "Forms are terms"). Every field has a value. This replaces the earlier
plan to use `[]`, which freed `[]` for byte arrays.

### Labels are optional and may repeat
A field is `label = value` or just `value`: `{'1', b = '2'}` has an unlabeled field
and a field `b`, so a struct can be a tuple. The labeled form is parsed first, so
`{a}` is an unlabeled field holding the variable `a`, not a field named `a`.
- An unlabeled field's label is `''`. A written name is never empty (`{"" = x}` is
  a parse error), so `''` only ever means "no label". The printer prints such a
  field as its value alone.
- Labels may repeat, and `s.a` picks the first field labeled `a`:
  `{a = '1', a = '2'}.a` gives `'1'`. `s.` can't be written, so no projection
  reaches an unlabeled field.
- In BANF, an unlabeled field is fine in a value struct and in a data form
  (`p = {'i32', 'i8'}`), but not where a label names something; see "Labels name
  params, declarations and blocks".

### Labels by name, positions by index: `s.a` and `s [00]`
`s.a` picks a field by a label written in the source. `s i` picks a field by its
position, and `i` is a term, so it can be computed at run time. A struct apply never
looks at labels, so every field is reachable by index, unlabeled and duplicate ones
included: `{a = '1', a = '2'} [01]` gives `'2'`, which `s.a` can't reach.
- No new syntax and no new term: `s i` is already an `Apply`, and only gets a
  reduction rule (see "`reduce`"). Labels stay static: no `s.(e)`, no `{(e) = v}`.
- An index is an unsigned little-endian integer of any length, starting at 0:
  `[01]`, `[0100]` and `[01000000]` are all 1, `[0001]` is 256. A form on the index is
  ignored, as for an `if` condition.
- A missing field is stuck, as for projection: an index past the last field, `''`,
  or an argument that isn't a byte array.
- `Project` stays its own term: BANF's shapes and the printer match on it.
- In BANF, a value struct applied to an index is the op `GetIndex` (`let y = args.p [01]
  in y` prints `y = p.1`). There the index must reduce to a byte array literal, since
  LLVM's `extractvalue` needs a constant (see "What the shape is").
- Precedence is application's: `s [00] [01]` is `(s [00]) [01]`, `f s [00]` is
  `(f s) [00]`, and `s [00] : t` is `s ([00] : t)`.

### Project for `s.x`
It is a one-word verb like `Apply`, and it is TAPL's name for `t.l` on
records (projection, E-ProjRcd); the reducer already called its step `project`.
We first chose `Select`, then `FieldAccess` (it pairs with the `Field` class and
is what C, Rust, and Java call `s.x`), and rejected `Project` as type-theory
jargon. We came back to it because this is a lambda calculus, and every other
term is named after its operation, not after what it looks like.
Rejected: `Select` (unclear), `FieldAccess` (names the syntax and breaks the verb
pattern), `Access` and `Read` (sound like memory operations next to LLVM),
`Field` (taken by the `Field` class), `Member` (C++ flavored, suggests methods),
`Get` (reads like a function call), `Dot` (names the syntax, not the meaning),
`Projection` (a noun among verbs), and `Pick`, `Take`, `Pluck`, `Extract`,
`Lookup`, `Focus`.

### Lambda as `x: form -> body`
- The arrow can be written `->` or `→` (U+2192); both mean the same. `→` reads like
  the math notation, and `->` is easy to type on any keyboard. A printer emits `->`,
  so generated code is plain ASCII.
- Lambda and `if` extend as far right as possible: `a -> b -> a b` is
  `a -> (b -> (a b))`. So a lambda argument needs parens: `f (x -> x)`, while
  `f x -> x` is a syntax error.
- Application is left-associative and binds looser than projection:
  `f a.x b` is `(f a.x) b`.

### Forms are terms
There is no separate form syntax or form class: a form is an ordinary term.
- A named form is a byte array: `'i32'` is the form i32 (`ByteArray(b'i32')`).
  A bare `i32` is a variable, not a form name.
- A struct form is a struct: `{x = 'i32', y = 'i8'}`.
- A function form is a `FunctionForm(param, result)` term, written `P => R`
  (see "Function forms").
- Any term may be a form. A binder's form (`x: F -> b`, `let x: F = v in b`) is an
  ordinary formed-level expression, the same as the `F` of `e: F`: `x: i32 -> x`,
  `x: module.T -> x`, `x: 'i8' => 'i32' -> x`, `x: [00]: 'i8' -> x`. It never holds a
  lambda, so it ends at the first `->`: `x: a -> b -> c` is the lambda `x: a` with
  body `b -> c`. A lambda or an application needs parentheses: `x: (a -> b) -> c`,
  `x: (f a) -> x`. There is no separate form grammar rule.
- Forms are resolved like other terms: a variable in a lambda param's form is
  looked up outside the lambda, so `x: (x) -> x` refers to an outer `x`. BANF
  translation needs literal forms (named forms and structs of them) and rejects
  others with "form must be a literal".
- Locations are left out of `==` on every term, so a parsed form equals the same
  form built in code (`terms.ByteArray(b'i32')`, `terms.struct_form(...)`).
- Why: one syntax and one set of terms for values and forms; later stages can
  compute forms with the same machinery as values.

### Forms are optional; omitted means `Empty`
Every binder `: form` may be left out: lambda params (`x -> body`) and lets. An
omitted form is `Empty` (`terms.Empty`): not written. It is not a void form; there is
none, and `: 'void'` is just the form named void. A byte array has no form of its own;
`[2a]` is just bytes.
- Why: quick sketches stay short. `Empty` has no default meaning: each position says
  what `Empty` means there, or rejects it. A BANF let, for example, has no form of its
  own, so `let t0 = $eq_i32 {...} in t0` needs no `t0: 'i1'`: the let's form is
  its op's. BANF translation rejects a byte array where nothing gives it a form, as in
  `[01]` with no `: form` ("form must be written").

### `Formed(term, form)`: any term with a form
`Formed` is `term: form`, "`term`, formed as `form`". It lets the form of any term come
from an expression, so a byte array's form can be a variable:
`(x -> y -> y: x) 'i1' [01]` evaluates to `[01]: 'i1'`. See `plan_annotation.md`.
- A byte array is only its bytes: `[01]: 'i8'` is `Formed(ByteArray([01]), 'i8')`, just
  like `y: 'i8'` is `Formed(y, 'i8')`. So every `:` that isn't on a binder is one term
  with one meaning, and beta reduction alone gives a dynamic form.
- `Formed` itself never reduces. `whnf` reduces inside `Formed.term`, and an `if` sees
  through a form on its condition.
- BANF translation turns a formed byte array into a constant, and any other formed
  atom into that atom with the written form. The written form replaces the atom's
  own form, unchecked: `([01]:'i8'):'i16'` is the constant `[01]:i16`, and `args.n:'i32'`
  is `n:i32` in BANF even when `n` is `i8`. LLVM translation rejects a formed name whose
  LLVM type differs from the name's.
- Precedence, highest first: atom, project `.`, `=>`, `:`, apply,
  `->`/`if`/`let`. The rule: values bind tighter than reducibles. `Formed` and
  `FunctionForm` never reduce, so `:` and `=>` bind tighter than application; `.` binds
  tighter still, since `module.T` and `args.n` read as paths. `:` is right associative
  and looser than `=>`.
  - `f [01]: 'u8' [02]` is `f ([01]: 'u8') [02]`, `f a: g b` is `f (a: g) b`,
    `$fix f: t` is `$fix (f: t)`.
  - `x: A => B` is `x: (A => B)`, `A => B: C` is `(A => B): C`,
    `a: b: c` is `a: (b: c)`, `x: module.T` is `x: (module.T)`.
  - An application inside `:` needs parentheses: `y: (f a)`, `(f a): t`.
    `y: f a` is `(y: f) a`.
  - Rejected: `:` below application, as in Haskell, OCaml and Lean
    (`f a: g b` = `(f a): (g b)`). It made `:` the only value operator looser than
    application. See `plan_annotation.md`.
- A lambda is tried first, so `x: F -> body` is still a lambda with a param form.

### Byte arrays are bracketed hex: `[2a 00 00 00]: 'i32'`
- The kernel has only byte arrays, so literals are written as bytes, not numbers.
- Bytes are little-endian on every target: `[2a000000]: 'i32'` is 42 everywhere.
  - Why fixed, not a default: oymomo has no integer literals, so the byte order is
    what gives a literal its number. With an overridable default, one source would
    mean two numbers. Same idea as WebAssembly memory and the `.bc` encoding: the
    encoding is fixed, the machine's byte order is a target detail.
  - Why: an evaluator (beta reduction plus opcodes) can run `add_i32` without a
    target, and it agrees with compiled code, so constant folding is safe.
  - A big-endian target gets big-endian bytes in memory: the LLVM translator
    emits the number (`i32 42`) and LLVM lays it out per `data_layout`.
  - Cost, later: once opcodes can reinterpret memory (store an `i32`, read bytes),
    a big-endian target sees bytes in a different order than the literal. Then
    either byte-swap loads and stores (as WebAssembly does) or call those opcodes
    target-dependent.
- Inside `[]`: groups of hex digits separated by whitespace. A group holds any
  number of bytes but has an even number of digits, so `[2a000000]`,
  `[2a00 0000]` and `[2a 00 00 00]` are the same bytes. `[]` is the empty array.
- Newlines are whitespace, so long arrays split without any continuation rule:
  ```
  [deadbeef cafebabe
   00112233 44556677]: {lo = 'i64', hi = 'i64'}
  ```
- Comments are not allowed inside the brackets.
- `[]` was freed when structs took `{}`, and the brackets bound the literal, so no
  prefix and no quotes are needed.
- The `: form` is optional, and it is an ordinary `Formed`, not part of the literal,
  since the same bytes can have many forms: `[01000000]` could be `'i32'` 1, or
  `{a = 'i16', b = 'i16'}`.
- Rejected: a prefix sigil (`#2a000000`, also `%`, `$`, `@`), which needed `_`
  separators and a `_` line continuation; `0x...`, which reads as an integer and
  hides the byte order; backticks, which look like quoting; juxtaposing literals,
  because juxtaposition is already application.

### Text byte arrays: `'Hello'`
- A byte array whose bytes are all printable ASCII can be written in single
  quotes: `'Hello'` is the same term as `[48656c6c 6f]`. The form suffix works as
  for hex: `'Hi': 'i16'`. A named form such as `'i32'` is a text byte array.
- Allowed characters: `0x20..0x7e` except `'` and `\`. No escapes, so bytes with
  `'`, `\`, or anything non-printable are written in hex. Keeping `\` out leaves
  room for escapes later. Single line only. `''` is the empty array.
- `'` was unused, and `"` is taken by quoted names.
- The printer uses `'...'` only for a byte array without a form (not the `t` of a
  `t: form`), every byte is text, and the array is at most 128 bytes; otherwise hex.
  Why: a written form (`[41]: 'i8'`) usually means a number, so hex stays; a long
  blob reads better as grouped hex. The limit is fixed, not `width`, so output
  doesn't depend on layout settings.

### Identifiers: plain or double quoted
Plain identifiers match `[A-Za-z_][A-Za-z0-9_]*`, excluding the reserved words
`if then else let in`. Any other non-empty string is written in double quotes:
`"a b"`, `"if"`, `"main.1"`.
- LLVM does the same (`@main` vs `@"foo bar"`), so kernel names map directly to
  symbols, including mangled names from higher-level languages. SQL also uses `"..."`.
- `"x"` and `x` are the same name; the parser stores the decoded string.
- Escapes: `\"`, `\\`, `\u{hex}`. No raw newlines. `""` is rejected.
- Quotes work everywhere a name appears: variables, lambda parameters, struct
  labels, and projection labels (`s."a b"`). Form names are byte arrays (`'a b'`).
- A printer quotes a name only when it is not a plain identifier. The BANF printer
  does too: `Data('my data', name_to_form('i8'))` prints as `"my data": i8`.
- Plain identifiers stay ASCII; other names use quotes. This avoids Unicode
  identifier rules and confusable characters.
- Cost: `"` is not available for string literals. The kernel has none.
  Rejected: Zig-style `@"..."`, only worth it if strings come.

### `$name` for built-ins, `$0` for indices
`$` marks a reference that no user name binds: `$0` is bound by position, `$add_i32`
by the kernel. User names are always written bare.
- `$` followed by digits is a `BruijnIndex`; `$` followed by a plain identifier is a
  `Builtin`. An identifier can't start with a digit, so the two never overlap.
- No trivia between `$` and the name, and the name can't be quoted: `$ fix` and
  `$"fix"` are errors. Nothing is reserved after `$`.
- `$name` is a primary, like a variable: `$add_i32 {...}.a` is `$add_i32 ({...}.a)`,
  `f $fix g` is `(f $fix) g`.

### Comments use `//`
Kept after byte arrays moved to `[]`; `#` is now unused.

### `let x = e in body` is sugar for `(x -> body) e`
- No new term: the parser builds `Apply(Lambda(x, body), e)`, and the printer prints
  every apply of a lambda as a `let`. The optional form goes on the name, as on a
  lambda param: `let t0: 'i1' = $eq_i32 {...} in t0`.
- Like a lambda, a let extends as far right as possible: `let x = e in a b` is
  `let x = e in (a b)`, and an argument needs parens: `f (let x = e in x)`.
- Why: the applied-lambda let `(t0 -> rest) (op)` puts the value after the whole
  rest of the block, far from its name. With `let`, a chain of lets reads top to
  bottom, as BANF does.
- `let` and `in` are reserved words.

### Function forms: `{c = 'i8'} => 'i32'`
- A function form is its own term, `FunctionForm(param, result)`. `P => R` (or
  `P ⇒ R`, U+21D2) writes it; printers emit `⇒` (the BANF printer `=>`). It has one
  param, matching one-argument lambdas, and no param name: the struct form's
  labels are what callers use (`module.putchar {c = [41]: 'i8'}`).
- Why a dedicated term: it used to be a tagged struct
  `{tag = ' => ', param = P, result = R}`. Every consumer then had to tell it
  from a plain struct (shape, field order and tag checks), a hand-written struct
  could turn into a function form by accident, and BANF output and errors showed
  the encoding. A struct is now always a struct. Rejected: a tag member on
  `Struct` (nominal typing; maybe later) and `Lambda` as a Π type (keeps
  `Lambda` free for form constructors). Named `FunctionForm`, not `Arrow`: it
  names the meaning and leaves room for a separate function type.
- Why not `->` like a lambda: a different arrow tells a form from a term at a
  glance, in `module: {putchar = {c = 'i8'} => 'i32'} -> {...}` the `=>` is in a
  form and each `->` binds a lambda.
- Right-associative: `{a = 'i8'} => {b = 'i8'} => 'i32'` is
  `{a = 'i8'} => ({b = 'i8'} => 'i32')`. Parens group the other way.
- `=>` is an expression operator too, so a function form can be a struct field
  value: `{putchar = {c = 'i8'} => 'i32'}`. It binds tighter than application and
  looser than `.`: `f a => g b` is `f (a => g) b`.
- A binder form follows the same precedence: `x: {c = 'i8'} => 'i32' -> x`,
  `x: i8 => s.f -> x`.
- Why this is safe: `=>` is not a lambda's `->`, so in
  `module: {} => 'i32' -> body` the form ends at `->`.
- `=>` binds tighter than `:`, so `[00]: 'i8' => 'i32'` is a byte array whose form
  is a function form. So a param with a form needs parentheses:
  `([00]: 'i8') => 'i32'`. The printer adds them.
- `=> R` leaves the param out: `FunctionForm(Empty, R)`. It is not `{} => R`, whose
  param is a struct with no fields. `=> => R` is `=> (=> R)`. With something on its
  left, `=>` takes that as the param, so `f => b` is `(f) => b`; as an apply argument
  it needs parentheses, `f (=> b)`, which the printer adds. The BANF printer shows
  `(=> R)`. In the `module` binder's form it declares a function the body defines
  (see "`module`").

### Printer: compact for tests, pretty for people
`printer.show(term)` and `printer.show_form(form)` live in `printer.py`, not in the
tests, so any stage can print terms. Both print `→`, which reads better than `->`,
and `⇒` for function forms.
- Compact (default): one line, with parentheses only where the grammar needs
  them, so it isn't ambiguous: `a → b → a b`, `f (x → x)`, `(f a).x`. Written
  forms are shown without a space (`x:'i32' → x`), and an omitted form isn't
  shown in either mode. Names are quoted when needed. Why: tests read like source and
  stay short; a grammar test that checks nesting compares against the
  parenthesized source, e.g. `show(parse('f a b')) == show(parse('(f a) b'))`.
- `pretty=True`: oymomo source that parses back to the same term (a test checks
  this). Parens only where needed (`f (x → x)`, `(let x = e in f) a`). Names are quoted when needed (`"if"`, `"a b"`). Bytes are shown in
  groups of four (`[deadbeef cafebabe]`), or as `'text'` (see "Text byte arrays").
- A pretty term wider than `width` columns (default 80) breaks, indenting each
  level by `indent` spaces (default 2):
  - a struct puts one field per line, with a trailing comma;
  - a lambda's body goes on the next line, indented. A body that is a struct or
    another lambda stays on the same line, so `module: {...} → {`
    stays together;
  - an apply's argument goes on the next line, indented;
  - a `let` puts its body on the next line, at the `let`'s own indentation, so a
    chain of lets reads one let per line:
    ```
    entry = args: {n = 'i32'} →
      let t0 = $eq_i32 {a = args.n, b = [00000000]: 'i32'} in
      if t0 then f.then0 {} else f.else0 {n = args.n},
    ```
  - an `if` puts `then` and `else` on their own lines.
- An apply of a lambda prints as `let` in both modes: compact
  `let x:'i8' = e in body`, pretty `let x: 'i8' = e in body`.
- A `BruijnIndex` prints as `$0`, a `Builtin` as `$add_i32`, and a `Variable` as its
  name, in both modes:
  the printer shows the term as it is. The parser reads `$0` back as a
  `BruijnIndex` (no space after `$`), so the output of a resolved term parses
  back to the same term.
- `name_indices=True` (either mode) prints a `BruijnIndex` as its binder's name,
  so a resolved term reads like source. It keeps `$i` where an inner binder
  shadows that name (`x → x → $1`) or no binder is in scope, so the output still
  parses and resolves back to the same term. The shaped golden and the rename
  tests use it.

## Program shape

```
module: {putchar = {c = 'i8'} => 'i32', errno = 'i32', main = => 'i32'} -> {
  main = f -> {entry = args:{} -> let t0 = module.putchar {c = [41]:'i8'} in t0},
}
```

A program is a lambda around a struct of definitions.

### Built-ins: `$add_i32`
The machine primitives (arithmetic, logic, comparison, conversions) are built-ins,
each a global constant written `$name`: `$add_i32 {a = x, b = y}`. A built-in with
machine code is an **opcode**; its name is in `banf_opcodes.OPCODES`.
- Why not names in `module`: it separates machine-provided instructions from symbols.
  `$add_i32` is an instruction the machine provides, so it never becomes an
  LLVM symbol, while every symbol in `module` does (`@putchar`, `@fact`).
  BANF keeps the split too: `OpcodeCall` for opcodes, `Call` for symbols.
- Why not a binder: a binder's index depends on depth (the program used to start
  with `prim ->`, and `prim` was `$3` under three lambdas), so `reduce`, which sees
  only the term, couldn't recognize `prim.fix`. A `Builtin` is the same at any depth.
- Every built-in is a separate constant, not a field of a global struct: there is no
  `$` value to project from, apply, or unpack.
- Every built-in takes one argument. One with several operands takes a struct, so a
  call is always `Apply(Builtin(name), arg)`.
- No word is reserved for them: `prim` and `fix` are plain names (`fix -> fix` is a
  lambda), and the parser accepts any `$name`.
- A name can be in two tables. Reduction rules are in `bruijn.BUILTIN_RULES`
  (`BuiltinRule(name, strict, needs, rule)`); machine code is in
  `banf_opcodes.OPCODES` and `llvm_opcodes.DEFAULT_OPCODES`:

  | Name | Rule | Opcode |
  |---|---|---|
  | `fix` | `$fix g` gives `g ($fix g)` | no: it must reduce away |
  | `add_i32` and the other opcodes | not yet (constant folding) | yes |

- A built-in with a rule and no opcode is **kernel-only**. That comes from the tables,
  with no flag to keep in sync. Reduction removes it: `$fix g` always fires. `convert`
  is the only gate into BANF: `$name arg` becomes an `OpcodeCall` only if `name` is in
  `OPCODES`. One message for each way a built-in can be left over:

  | Left over | Message |
  |---|---|
  | `$fix`, not applied | `$fix must be applied.` |
  | a kernel-only `$name arg` whose rule didn't fire | `$name has no opcode, so it must reduce away: its argument must reduce to <needs>.` |
  | `$nope {}`, in no table | `Unknown built-in '$nope'.` |

  The ending of the second comes from the rule (`BuiltinRule.needs`, such as
  `'a struct'`), so a new built-in brings its own message.
- Why `fix` is a built-in, not its own term: a new kernel built-in is one table
  entry, instead of a term, a grammar rule, a reserved word and cases in five modules.

### `module`: every symbol, declared by the binder's form
`module`'s form declares every symbol of the module, imported or defined, in one
struct. The program's body is the struct of definitions, passed back in as `module`
so functions call each other and imports the same way: `module.fact {n = t1}`,
`module.putchar {c = [41]:'i8'}`, `module.errno`. The shape of each declaration
says whether the body defines it:

| Declaration | Defined in the body | Result |
|---|---|---|
| `=> R` | as a function | `banf.Function`: params from its entry block, return form `R` |
| `=> R` | no | error: "'main' declares no params, so it must be defined." |
| `{...} => R` | no | imported function, `banf.Signature`: `declare i32 @putchar(i8 %c)` |
| `{...} => R` | yes | error: "'putchar' declares its params; a definition takes them from its entry block." |
| data form `F` | no | imported data, `banf.Data`: `@errno = external global i32` |
| data form `F` | as a byte array | defined data, `banf.Data` with a value: `@answer = global i32 42` |

- A body label must be declared: "'f' is defined but not declared."
- A definition must fit its declaration: `=> R` needs `blocks -> {...}`, and a data
  declaration needs a byte array ("'answer' is declared as data, so its definition
  must be a byte array."). The body field is taken to whnf, so
  `answer = (x -> x) [2a]` is fine. Its form is the declared one: a form written on
  the byte array (`[2a]: 'i16'`) is dropped, since BANF has no slot for it.
- Every parameter list is written once: a defined function's comes only from its
  entry block, an imported function's only from its declaration.
- Every return form is written, in the declaration (see "Return forms are
  declared").
- A forgotten definition is caught: a function meant to be defined is declared as
  `=> R`, so leaving it out is a translation error, not a link error.
- A module with no symbols writes `module: {}`. The form is required, so the
  translator always knows the symbol list.
- BANF bindings are in declaration order.
- Why one binder, not `decls` for imports and `defs` for definitions: with two, a
  defined function's return form had nowhere to be written, so it was inferred;
  calls went through `decls.f` or `defs.f` depending on where `f` lived; and a
  name in both was an extra error. With one, the form lists every symbol with its
  return form, and the declaration's shape says which ones are imported.
- Why not an empty byte array as a "no body" sentinel for imports (an earlier
  idea): it needs a magic value. The declaration's shape says the same thing.
- Why recursion needs no `$fix`: functions call each other by projection on
  `module`, just as LLVM functions call each other by symbol. A `$fix` in the
  source is only unfolded while reducing to BANF's shape (see "oymomo to BANF"); it
  never becomes a loop or a call.
- Why not cross-module calls by name: every external symbol is declared in
  `module`, so a module lists everything it needs from outside, and the linker
  resolves it.

### Symbols
Every declaration in `module` becomes one LLVM symbol, named after its label.

### Functions as structs of blocks
Each field of the body is a function written as a struct of blocks:

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

- The binder (`f` here, any name) is the function's own blocks, so `f.then0 {}`
  jumps to a sibling block. It is the same self-reference trick as `module`, one
  level down. Renaming calls it `blocks` (see "Binders get fixed names").
- Each block is a lambda taking one struct (`args:{n = 'i32'} -> ...`). The binder
  (`args` here, any name) is the block's param struct.
- The first field is the entry block, whatever its name.
- Why this shape: it is plain oymomo (lambdas, structs, application), so no new
  syntax was needed for blocks and jumps, and every name and label in the BANF
  output comes from the source.

### One argument, always a struct
An oymomo lambda takes exactly one argument. When a program is translated to BANF,
every block's argument must be a struct, and so must every opcode's and every
imported function's.
- Why: the kernel stays a plain one-argument lambda calculus. Labels name the
  arguments at every call site (`{minuend = x, subtrahend = y}`), so argument order
  can't be mixed up silently.
- The translation to BANF expands the struct one level into multiple params, which
  map one-to-one onto LLVM params:
  ```
  oymomo: fact = f -> {entry = args:{n = 'i32'} -> ...}
  BANF:   entry(n: i32)
  LLVM:   define i32 @fact(i32 %n)
  ```
- Only one level: `args:{p = {x = 'i32', y = 'i32'}}` gives one param `p` whose form is a
  struct, which is one LLVM struct argument `{i32, i32} %p`. A deeper expansion
  would have to invent names like `p.x`, and LLVM passes struct values anyway.
- Why the expansion happens in oymomo-to-BANF, not BANF-to-LLVM: BANF is meant to
  be LLVM-shaped, so BANF-to-LLVM stays one-to-one with no expansion of its own.
- A call or jump argument is a struct literal of atoms whose labels match the
  callee's params in order, or the block's own `args` forwarded as-is:
  `module.add args` or `f.body args`.

## Opcodes

### Monomorphic: one op per signature
Each unique signature (param forms plus result form) is its own op:
`add_i32`, `add_i64`, `eq_i8`, `zext_i8_i32`, `trunc_i64_i32`. There is no generic
`add`.
- Why: an `OpcodeCall`'s result form is a table lookup, the same way a `Call`'s comes
  from its callee's signature. Nothing needs width inference, and conversions don't
  need a stored target form: `zext_i8_i32` always returns `i32`.
- Cost: many op names. They are generated from templates, not written by hand.
- Strict widths: `$add_i32 {a = [01]:'i8', b = ...}` is an error
  (`$add_i32 expects a: i32, got i8.`). Convert explicitly with `zext_i8_i32`.

### Naming
- Same-form ops: `<op>_<form>` (`add_i32`, `eq_i8`).
- Conversions name both forms, from and to: `zext_i8_i32`, `trunc_i64_i32`.

### Labels fit the op
Each template picks labels that say what each operand means:

```
add mul and or xor           {a: T, b: T} -> T          order doesn't matter
sub                          {minuend: T, subtrahend: T} -> T
sdiv udiv srem urem          {dividend: T, divisor: T} -> T
shl lshr ashr                {value: T, amount: T} -> T
eq ne                        {a: T, b: T} => i1
slt sle sgt sge ult ule ugt uge   {lhs: T, rhs: T} => i1
zext sext                    {value: F} -> T            for each wider T
trunc                        {value: F} -> T            for each narrower T
```

- Why not `a`/`b` everywhere: for non-commutative ops the label documents the
  operand's role, so `$sub_i32 {minuend = x, subtrahend = y}` can't be read
  the wrong way round.
- Forms: `i1 i8 i16 i32 i64`. Arithmetic, shifts and ordered comparisons skip `i1`;
  `and or xor eq ne` include it (as boolean logic). No same-width conversions.
- `banf_opcodes.py` holds these signatures as plain data, with no LLVM;
  `llvm_opcodes.py` maps each one to llvmlite (`add_*` to `builder.add`, `slt_*` to
  `icmp_signed('<')`, `zext_i8_i32` to `zext(value, i32)`). A test checks that the
  two tables have the same op names.

## BANF

BANF: block-based ANF; SSA with block parameters instead of phi nodes, as in MLIR
and Cranelift.

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

### Why basic blocks, and why block params instead of phi
- Basic blocks make the IR close to LLVM, so lowering is one BANF block to one LLVM
  block, one let to one instruction.
- Block params replace phi nodes: a join block declares what it receives, and each
  jump passes it, so each edge says what flows along it.
  ```
  then0(x: i32, z: i32):
    jump join0(x, z)
  else0(y: i32, z: i32):
    jump join0(y, z)
  join0(v: i32, z: i32):
    t0 = add_i32 v, z
  ```
  The LLVM translator turns these back into phis where needed (see "BANF to LLVM").

### Blocks are closed
A block can use only its own params and lets. A value from another block must be
passed through a jump or branch argument. In `fact`, `else0` needs `n`, so `entry`
passes it: `branch t0, then0(), else0(n)`.
- Why: each block reads on its own, with no dominance or live-in analysis needed to
  know what is in scope. Names are scoped to their block, so a passed-in value can
  keep its name (`else0(n: i32)`).
- In oymomo this holds by construction: a block lambda's scope only holds its
  `args`, its lets, and the outer binders `f` and `module`; built-ins are global.

### The entry block cannot be jumped to
The entry block's params are the function's params, as in Cranelift.
- Why: LLVM's entry block can't have predecessors, and its params are the LLVM
  function's arguments, not phis. A loop jumps to a separate header block instead:
  ```
  entry(n: i32):
    jump loop(n)
  loop(n: i32):
    ...
    jump loop(t1)
  ```

### Forms are stored only where they can't be worked out
Forms appear on each `Const`, on each block param, on each function's and
signature's return form, and on each `Data`. Ops carry no form, as in Cranelift
(`v0 = iadd v1, v2`), and a `Let` carries one only if the source wrote it.
- Why a `Const` has one: the same bytes can have many forms.
- Why a block param has one: a block has to declare what its jumps pass in.
- Why return forms are stored: calls read them, including recursive calls. They
  come from the `module` declarations.
- Why it's optional on `Let`: `form_of(op, forms, module)` computes it, and a stored
  form would be verbose. A `MakeStruct` result would repeat a full struct form such as
  `{x: i32, y: {lo: i64, hi: i64}}` on every line that builds or reads one. A written
  let form replaces the op's form (`Let.form`; `Empty` when not written).

`form_of` works out each op's result form:
- `OpcodeCall`: the op's result form from `banf_opcodes.py`.
- `Call`: the callee's `return_form`, whether it is a `Function` or a `Signature`.
- `MakeStruct`: each label paired with its field atom's form.
- `GetField`: that field's form inside the struct atom's form.
- `GetIndex`: the form of the field at that position in the struct atom's form,
  labeled or not (`Form {x: i32} has no field at index 2.`).
- `GetData`: the `Data` binding's form.

The verifier and the LLVM translator use `let_form` while walking a block: the
let's written form, or else `form_of` its op. They add it to the block's name table.

### Module = bindings, each with a name
```python
Module(bindings: list[Function | Signature | Data])
Function(name, return_form, blocks)       # blocks[0] is the entry block
Signature(name, params, return_form)       # imported function
Data(name, form, value=None)               # data: imported (None) or defined (bytes)
```
- `name` is the LLVM symbol (`@fact`, `@putchar`, `@errno`). It lives on the
  binding instead of in `(name, binding)` tuples, which is simpler to carry around
  and to print.
- `Signature` needs its own `params` because it has no entry block to hold them.
- `Data` is read-only in oymomo (it has no assignment) but re-read on every use with
  `GetData`, because a value like `errno` can change outside the program. Defined
  data is read the same way, with `module.answer`. Not named
  `Global`, because every binding becomes an LLVM global.

### Printer
- A binding prints as `name = op` with no `let` keyword and no form, as in
  Cranelift: `t0 = eq_i32 n, [00000000]:i32`. That is unambiguous, because a
  block holds only lets plus one terminator, and every terminator starts with a
  keyword (`jump`, `branch`, `return`).
- Opcodes print assembly style, as in Cranelift: the name, then the operands
  separated by commas, with no parentheses and no `$` (`t3 = mul_i32 n, t2`).
- Calls print with the keyword `call`, parentheses and commas (`t2 = call fact(t1)`),
  so they don't read like oymomo's one-argument application or like an opcode.
- A data read is a bare name (`t0 = errno`): an opcode always has operands, so
  `t0 = add_i32` can only be data.
- Calls and data reads use the symbol, not `module.`: `call fact(t1)`, `t0 = errno`.
- A `GetIndex` prints as `p.1`. A label written as digits needs quotes (`p."1"`), so
  `p.1` is never a `GetField`.
- Bindings print in declaration order: `putchar(c: i8): i32` for a `Signature`,
  `errno: i32` for imported `Data`, `answer: i32 = [2a000000]` for defined `Data`, and each function as `fact: i32` followed by its blocks,
  with a blank line around each function.
- Blocks are indented under their function (labels at 2 spaces, instructions at 4),
  so the column tells a line's kind. At column 0, the block label `entry(a: i32):`
  would look like the signature `putchar(c: i8): i32`, and nothing would mark
  where a function ends. Braces would do that too, but indentation already does.

## oymomo to BANF: reduce, rename, convert

`banf_translate.translate(term)` runs four passes. `shape(term)` runs the first
three and returns an oymomo term in BANF's shape; `convert(shaped)` runs the last.
1. `bruijn.resolve`: each `Variable` becomes a `BruijnIndex`, counting enclosing
   lambdas. Binder names stay on `Lambda.param_name`. An unbound name is an error.
2. `banf_reduce.shape`: reduces only where the term doesn't have BANF's shape yet.
3. `banf_rename.rename`: gives binders names that don't shadow each other.
4. `banf_translate.convert`: reads the shaped term into BANF, and raises
   `TranslationError` with a source location on any mismatch.

**Translation only reduces terms.** `shape` runs term reductions (beta, built-in rules such as `$fix`, project,
`if`) until each position has BANF's shape, then renames binders. `convert` only reads
the result:
- No default values: an omitted form is `Empty`, and `Empty` is never read as `void`
  or as anything else. A position that needs a form rejects it ("form must be
  written").
- Nothing inferred: every form BANF stores is written in the source, return forms
  included (see "Return forms are declared"), and every parameter list and form is
  written once.
- Unneeded forms are dropped: a form written where BANF has no slot for it (on the
  `blocks` binder, or on a data definition) is dropped, not rejected.
- A form is not a type: a written form is never checked against a computed one; it
  replaces it (a let's form, a formed atom). `banf.verify` still checks arguments,
  branch conditions and returns against the forms they're *required* to have, and
  `llvm_translate` rejects a replaced form whose LLVM type differs.

A term that doesn't have BANF's shape after reduction is rejected with the usual
message, and the source fixes it explicitly. See `plan_banf_explicit.md` for the
decisions behind this.

The golden tests approve the shaped term next to the BANF and LLVM output, as
`name.shaped.oymo`, and check that it translates to the same BANF.

### `reduce`: one step at the root
`bruijn.reduce(term)` takes one step if the root is a redex, and otherwise returns
`term` itself (so `reduce(t) is t` says "not a redex"). It never looks inside.
- beta: `(x -> body) e` gives `body` with `e` put in for `x`. With a form,
  `(x: F -> body) e` puts in `e: F`, and drops `e`'s own form (`e: G` goes in
  as `e: F`). Without one, `e` goes in as it is, so it keeps its own form, if it
  has one;
- built-in: `$name a` steps by the rule in `bruijn.BUILTIN_RULES[name]`, if there is
  one and it fires: `$fix g` gives `g ($fix g)`. A built-in with no rule
  (`$add_i32 {...}`) or an unknown one (`$nope g`) is not a redex;
- projection: `{a = e, ...}.a` gives `e`. A missing label is not a redex;
- struct apply: `{e0, e1, ...} [01]` gives `e1`, the field at that position,
  labeled or not. The index is the byte array's unsigned little-endian value, so
  `[01]`, `[0100]` and `[01000000]` are all 1, and a form on it is ignored
  (`bruijn.index_value`). An index past the last field, `''`, or an argument that
  isn't a byte array yet is not a redex;
- if: `if [01] then a else b` gives `a`, and `if [00] ...` gives `b`.

- Only the root: arguments, lambda bodies, struct fields and `if` arms stay as
  they are, and so does a head whose root isn't a redex yet (`$fix g a`,
  `{p = {a = e}}.p.a`). `banf_reduce` reduces heads.
- At most one rule applies to a term, so their order doesn't matter: beta needs
  a `Lambda` callee, struct apply a `Struct` callee, a built-in rule a `Builtin`
  callee.
- It never raises and never recurses, so one call always finishes. Loops come
  from calling it again and again, so the fuel is in `banf_reduce`.
- Opcodes are not run (`$add_i32 {...}` is stuck), and an `if` condition's form isn't
  checked: only the one-byte values `01` and `00` are redexes.
- The helpers it uses are `shift`, `substitute`, `beta`
  (`shift(substitute(body, 0, shift(arg, 1)), -1)`), `project` and
  `index_value`.

### `banf_reduce`: reduce until each position has its shape
Each position wants certain constructors. The term there is reduced until it has
one, then its own positions are visited. Forms and binder kinds aren't checked
(except `args`, through `k` below); `convert` does that, so this pass needs no
context.

**Heads.** Some roots become a redex only after their head is reduced: in
`$fix g a`, `$fix g` must unfold to a lambda first. The head of an apply is its
callee, of a projection its struct, of an if its condition, of a `Formed` its
term; other terms have none. Once an apply's callee is a struct, its head is the
argument instead: in `{a = x} ((y -> y) [00])` the index must become a byte array
before the struct apply fires. So `step` reduces the callee to a struct, then the
index, then the root. An argument is reduced only when the callee is already a
struct, so ordinary applications stay lazy (`f ((x -> x) a)` keeps its argument).
A strict built-in's argument is its head too: a rule marked `strict` reads its
argument, so in `$unpack ((x -> x) {...})` the argument is reduced to a struct before
the rule fires. `banf_reduce` reads the flag on the rule, so a new built-in needs no
change there. `$fix` is not strict: `$fix g` unfolds without reducing `g`.

| Term | Head |
|---|---|
| `{...} i` | `i` |
| `$name a`, with `name`'s rule strict | `a` |
| `f a`, otherwise (including `$fix g`) | `f` |
| `s.l` | `s` |
| `if c then ...` | `c` |
| `t: F` | `t` |
```
step(t) = reduce(t)        if reduce(t) is not t                        -- a step at the root
        = t with head h'   if t has a head h, and h' = whnf(h) is not h   -- else reduce the head
        = t                otherwise

whnf(t) = whnf(step(t))    if step(t) is not t
        = t                otherwise
```
`whnf` stops at every Lambda, Struct, ByteArray, BruijnIndex and Builtin, and at stuck terms
such as `$add_i32 {...}`, `args.n`, `blocks.done {...}` or `if t0 then a else b`.
- "Reduce `t` until it is X" means take `whnf(t)`, then look at its constructor.
  Looking first would be wrong: `{f = x -> ...}.f args.n` is already an apply, but
  its callee must be reduced before it is a call such as `$add_i32 {...}`.
- A position that already has a wanted constructor is not reduced further, since
  `whnf` stops there. So a let-bound struct stays a `MakeStruct`.

**Positions**, as numbered in `banf_reduce.py`:
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
               | if <atom> then <jump> else <jump>          -- branch
   ```
   `k` counts the lets since the block's `args` binder, so `args` is `$k`; it
   tells `args.label` from other projections. A let isn't reduced with `whnf`,
   since it is a redex that must be kept. Repeat:
   1. For a let `(x -> rest) <value>`, take `whnf(<value>)`. If it is an op (an
      apply, a struct, or a projection other than `args.label`), keep the let,
      visit the op (7), and go on with `rest`. Otherwise beta-reduce the let and
      go on with the result.
   2. Else, if `step` changes the body, go on with that. This can make a let:
      in `(x -> y -> rest) a b` the head reduces and leaves `(y -> rest') b`.
   3. Else visit the terminal's positions and stop.
7. `<value>`, a let's op: an apply's `<op_arg>` becomes a struct of atoms or a
   BruijnIndex (forwarding `args`); a struct's fields become atoms; a
   projection's struct is a head, already reduced.
8. `<jump>`, an `if` arm: until `blocks.label <op_arg>`.
9. `<atom>`: until a ByteArray, `$i` with `i < k`, or `args.n`. `args` itself is
   not an atom: BANF passes a block's params one by one.

More rules:
- Because a let whose value isn't an op is beta-reduced, helpers are inlined,
  `let t = args.n in t` becomes `args.n`, and a let-bound `if` lands in tail
  position.
- A term that can't get its shape is left as it is, for `convert` to report with
  the usual message, so this pass has no errors except running out of fuel.
- Fuel: each step costs one unit, out of 10,000. A term that keeps reducing, such
  as `$fix (self -> self)`, fails with "ran out of reduction steps".
- Nothing is flattened: a nested call stays nested and is an error, since
  flattening would mean inventing names.

### Binders get fixed names
The structural binders (positions 1, 3 and 5) are renamed to fixed names,
so every shaped program reads
`module -> {main = blocks -> {entry = args -> ...}}`. `convert` then
checks each position by name, and a wrong name means a wrong shape.
- On any path from the root the three names appear once each, so they never clash.
- A position `banf_reduce` left without its shape is not structural: its binder
  follows the rule below, and `convert` reports the shape error.
- The fixed names don't reach BANF: `blocks.label` becomes a jump target and
  `args.n` becomes `banf.Var('n')`.

### Other binders keep their names unless they clash
A let keeps its name `x` unless `x` is visible: the name of an enclosing binder
(after renaming, so the three fixed names count), or a param label of its block.
Then it becomes `x_L`, else `x__L`, and so on, where `L` is its level (the number
of enclosing binders; a block's first let is level 3).
- `let t = ... in let t = ... in let t = ... in t` gives `t, t_4, t_5`.
- With `args: {n = 'i8'}`, two lets named `n` give `n_3, n_4`, since `n` is a param
  label: param labels become BANF `Var`s, as in `entry(n: i8)`.
- A user's own `t_4` after a renamed `t_4` gives `t_4_5`; `t, t_5, t` gives
  `t, t_5, t__5`. A let named `args` gives `args_3`; one named `prim` keeps its name.
- Labels (struct, field, block, function, param) are never renamed, and only
  param labels count as visible. The others live in their own namespaces in
  oymomo and in BANF (`Jump.target`, `Call.function` and `GetData.name` are plain
  strings, not `Var`s), so a let `n` used as `{n = n}` keeps its name.
- Visible names are per path, so sibling blocks can both have a `t`. In LLVM, two
  values with one name get a `.1` suffix, which is fine.
- A second run changes nothing: the output has no clashes, so every name is kept.
- Cost: one set, with an add on the way down and a remove on the way up. The names
  on one path are distinct, so a plain set is enough, and the pass is linear.
- Rejected:
  - one set per function, to avoid LLVM's `.1`: it renames lets that clash only
    with a sibling block, and LLVM names don't matter;
  - checking every label: those are separate namespaces, and collecting them
    would need an extra pass;
  - renaming params: param labels appear in the block's form, in `args.n` and in
    every jump's `{n = ...}`, so renaming them means rewriting labels in many
    places;
  - `_<level>_<original>` for every binder: unique without a set, but it renames
    every let, even ones that clash with nothing;
  - `name$level` (`n$3`): it needs quotes, and `$` now starts a BruijnIndex or a
    Builtin.

### `convert` finds binders by index
Inside a block body with `k` lets so far, the binders above are always, from the
inside out: the lets (`$0` to `$k-1`), then `args` (`$k`), `blocks` (`$k+1`),
`module` (`$k+2`). So `convert` classifies each `BruijnIndex` by
arithmetic and keeps no binder names of its own. A let reference becomes a
`banf.Var` named after the BANF let already built.

### What the shape is
- **Let**: `let x = op in rest`, which is `(x -> rest) (op)`. The form may be
  omitted, and then the let's form is the op's. A written form must be a literal,
  and it replaces the op's form without being compared to it, since a form is not a
  type: `let t0: 'i32' = $eq_i32 {...} in t0` gives `t0` the form `i32`, though
  `eq_i32` gives `i1`. BANF prints it as `t0: i32 = eq_i32 ...`. LLVM translation
  rejects it, since the LLVM types differ (see "BANF to LLVM").
- **Atoms**: a byte array with a literal form (`[01]: 'i8'`), a let name, or `args.label`.
  Any atom can be given a literal form, which replaces its own (`args.n: 'i32'`,
  `t: 'i8'`). `let m: 'i32' = args.n in m` isn't a let in BANF: its value isn't an op,
  so it's beta-reduced, and beta carries the form, giving `args.n: 'i32'`.
- **Ops**, only as a let's value: `$opcode {...}` (an `OpcodeCall`), `module.g {...}` (a `Call`, whether
  `g` is imported or defined), a struct literal of atoms (`MakeStruct`), a projection
  on an atom (`let x = args.p.x in ...` is a `GetField` on param `p`), an atom
  applied to an index (`let y = args.p [01] in ...` is a `GetIndex`), or
  `module.errno` for data (`GetData`).
- **`GetIndex`**: `s i`, where `s` is an atom with a struct form (a let-bound struct or
  a param such as `args.p`), reads the field at position `i`, labeled or not, as the
  kernel's struct apply does on a struct literal. `i` is read by `bruijn.index_value`:
  any byte array literal, unsigned little-endian, a form on it ignored, so `[01]`,
  `[0100]` and `[01]: 'i8'` are all 1. It is reduced first like any op argument, so
  `args.p ((i -> i) [01])` and `let i = [01] in args.p i` work. A run-time value
  (`args.n`, or a let bound to an op) or `''` is an error (`An index must be a byte
  array literal, such as [01].`), since LLVM's `extractvalue` needs a constant. An
  index past the last field is a form error (`Form {i32, i8} has no field at index
  2.`). Binders are read only by label, so `args [00]` stays an error.
- **Terminators**, only in tail position:
  - `f.label {...}` is a jump.
  - `if c then f.a {...} else f.b {...}` is a branch. Both arms must be jumps.
  - An atom is returned.

### Labels name params, declarations and blocks
BANF reads `module`, `blocks` and `args` only by label, so every field needs a
label in the module form, a signature's param form, the module body, a definition's
blocks, the top level of a block's param form, and the argument struct of a call, a
jump or an opcode: "The module form needs a label on every field." Elsewhere (a value
struct, a nested data form such as `args: {p = {'i32', 'i8'}}`) a field may be
unlabeled, and several unlabeled fields are not duplicate labels. BANF prints an
unlabeled field alone (`{i32, i8}`, `{n, y = [01]:i8}`), and LLVM names its
`insertvalue` by index (`%"q.0"`).

### Operands must be atoms; nested calls are rejected
`$add_i32 {a = $add_i32 {...}, b = ...}` is an error; bind the inner call
with a let first.
- Why: allowing it means flattening nested calls into lets, which means inventing
  temporary names. That is normalization.

### An op in tail position must be bound first
`main = f -> {entry = args:{} -> let t0 = module.putchar {c = [41]:'i8'} in t0}`,
not `... args:{} -> module.putchar {c = [41]:'i8'}`.
- Why: a BANF `Return` takes an atom. Accepting a tail op would make the
  translator invent a name for the result; the explicit `let t0` keeps every
  name in the source.

### `if` only in tail position, with jumps in both arms, to different blocks
`if c then [01]:'i8' else f.b {}` is an error. A let-bound `if` is substituted, so
`let t = if c then f.a {} else f.b {} in t` is fine, but an `if` that ends up as
an operand is an error.
- Why: a BANF `Branch` is a terminator with two targets. An `if` whose value is
  used needs a join block, and the source writes that block explicitly.
- Why different targets: `if c then f.a {} else f.a {}` would give `a` two
  incoming edges from the same block, and an LLVM phi can't tell those edges apart.

### Binders can't be used as values
`blocks`, `args` and `module` used on their own are errors
(`'args' cannot be used as a value.`; the message uses the fixed name), except `args` forwarded as a whole call or
jump argument. So are `module.g` and `$add_i8` without an argument
(`$add_i8 must be applied.`).
- Why: they have no runtime value. `module` is not a struct anything could build.

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

- Why declare instead of infer: the form is written once, where the symbol is
  declared, and nothing is computed. Inference had to iterate over the whole module
  to a fixed point, and a function with no base case
  (`entry = args:{} -> let t = module.g {} in t`) had no return form at all.

### Nested function forms are rejected, for now
A function form is accepted only as a `module` declaration's whole form. These are
rejected until it's decided what they mean:
- inside a data form: `module: {libc = {putchar = {c = 'i8'} => 'i32'}}`,
- as a param or result: `module: {g = {c = 'i8'} => {d = 'i8'} => 'i32'}`, `main = => => 'i32'`,
- with a non-struct param: `module: {g = 'i8' => 'i32'}`.

`Empty` forms inside a declaration are rejected too ("form must be written"), since
nothing infers a form. `Empty` alone (`main = `) can't be written, since a struct field
needs a value.

### First-order only
No closures and no escaping lambdas: after reduction, the only lambdas are the
program binders, function, block and let lambdas. A helper lambda that reduction
inlines is fine; one that is left over is an error.

## BANF to LLVM

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

- Forms map to LLVM types: `iN` is `iN`, and a struct form is a literal struct
  type with fields in declaration order. Other form names are rejected.
- Every symbol is declared first, so functions can call each other in any order.
- Block params with one predecessor bind straight to what that predecessor passes,
  so no phi is emitted: `else0`'s `n` is just `%n` from `entry`.
- Block params with several predecessors become phis, one incoming value per edge:
  `%v = phi i32 [%x, %a], [0, %b]`.
- Unreachable blocks are not emitted, so a phi only has incoming values from
  blocks that exist.
- Constants: an integer read from the bytes as little-endian, emitted as a number
  (`[2a000000]:i32` is `i32 42`). LLVM stores it in the data layout's byte order,
  so a big-endian target (`E-...`) needs no swap in the translator. An `iN`
  constant needs `(N + 7) // 8` bytes, so `i1` is one byte holding 0 or 1. Struct
  constants are not supported yet.
- LLVM value names are the BANF let names (`%t0`), so IR is easy to match against
  BANF. A `MakeStruct` builds its value with one `insertvalue` per field, and the
  intermediate values are named after the let and field (`%q.x`) instead of
  llvmlite's numbering.
- `GetData` is a `load` from the global. `GetField` is `extractvalue`.
- `GetIndex` is `extractvalue` too, with the index as the position: `args.p [00]`
  gives the same IR as `args.p.x`.
- Defined data is a writable `global` (not `constant`) with an initializer,
  `@answer = global i32 42`; imported data is an `external global`. The initializer
  follows the constant rules, so it needs an integer form and the right byte count
  ("A i32 constant needs 4 bytes."), and struct data forms are rejected for now.
  Constness will come later with the data's form.
- A formed name (`n:i32`) is checked the same way: used as it is if the LLVM types are
  equal, otherwise rejected ("'n' is formed as i32, but its LLVM type is i8.").
- A let with a written form: if the form's LLVM type equals the op's value type (for
  example, a struct form with other labels and the same field types), the value is
  used as it is. Otherwise it's rejected ("Let 't0' is formed as i32, but its op gives
  i1."). Nothing is converted: no `bitcast`, no widening, no narrowing.

## Testing
- Unit tests per stage: `grammar_test.py`, `printer_test.py`, `banf_opcodes_test.py`,
  `banf_terms_test.py`, `bruijn_test.py`, `banf_reduce_test.py`,
  `banf_rename_test.py`, `banf_translate_test.py`, `llvm_translate_test.py`.
- BANF tests build modules by hand, so they don't depend on the translator.
- Every LLVM test parses the IR with `llvmlite.binding` and verifies it.
- Golden tests (`tests/goldens/`): each `name.oymo` produces approved
  `name.shaped.oymo`, `name.banf` and `name.ll` files.

## Not yet decided / not done
- Nested function forms (in data forms, or as a function form's param or result).
- Closures and higher-order functions.
- Struct constants in LLVM, including struct data initializers.
- The `language oymomo` header at the top of `.oymo` files is checked and stripped
  by the golden test; the parser doesn't handle layers yet.
- Void functions: every function returns a value.
