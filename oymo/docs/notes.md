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
`bruijn.py`, `banf_terms.py`, `banf_prim.py`, `banf_reduce.py`, `banf_rename.py`,
`banf_translate.py`, `llvm_prims.py`,
`llvm_translate.py`, and tests use the same names in `tests/oymomo/`.
- Why flat: the stages are small, and a prefix shows the stage as clearly as a
  subpackage without the extra `__init__.py` files and import paths.
- Rule: only `llvm_*.py` imports llvmlite, and no `banf_*.py` imports an
  `llvm_*.py`. BANF depends only on `oymomo.terms`.

### BANF does not depend on LLVM
Anything LLVM needs that BANF doesn't have is passed to the LLVM translator:

```python
Target(triple='x86_64-unknown-linux-gnu', data_layout='', prims=DEFAULT_PRIMS)
```

- No `byte_order`: byte arrays are always little-endian (see "Byte arrays"), and the
  target's own byte order comes from `data_layout` (`e` or `E`). A separate field
  could disagree with it.
- `prims` maps each prim op name to the LLVM instructions that implement it.
- Why: how each prim op becomes LLVM instructions is a backend detail, so BANF
  only names the op (`prim.add_i32`) and the target supplies the implementation.

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
x : 'i32' -> body            Lambda
f a b                        Apply
{x = e1, y = e2}             Struct
s.x                          Project
if c then a else b           If
let x = e in body            sugar for (x -> body) e
fix f                        Fix
[2a 00 00 00]                ByteArray
e : 'i32'                    Formed
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

### Project for `s.x`
It is a one-word verb like `Apply` and `Fix`, and it is TAPL's name for `t.l` on
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

### Lambda as `x : form -> body`
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
- Any term may be a form. After a binder's `:`, a struct, a byte array (with or
  without its own `: form`) or a function form is written as it is; any other term
  needs parentheses: `x: (i32) -> x`, `x: (a -> b) -> c`. `x: i32 -> x` is a syntax
  error. The grammar rules are `FORM` (`FORM_ATOM => FORM` or `FORM_ATOM`) and
  `FORM_ATOM` (struct, byte array, or parenthesized expression).
- Forms are resolved like other terms: a variable in a lambda param's form is
  looked up outside the lambda, so `x: (x) -> x` refers to an outer `x`. BANF
  translation needs literal forms (named forms and structs of them) and rejects
  others with "form must be a literal".
- Locations are left out of `==` on every term, so a parsed form equals the same
  form built in code (`terms.name_to_form('i32')`, `terms.struct_form(...)`).
- Why: one syntax and one set of terms for values and forms; later stages can
  compute forms with the same machinery as values.

### Forms are optional; omitted means void
Every binder `: form` may be left out: lambda params (`x -> body`) and lets. An
omitted form is void (`terms.Void`). `void` is not special: `: 'void'` is the form
named void. A byte array has no form of its own; `[2a]` is just bytes.
- Why: quick sketches stay short, and each later stage decides what it can infer.
  BANF translation, for example, infers a let's form from its op, so
  `let t0 = prim.eq_i32 {...} in t0` needs no `t0: 'i1'`. It rejects a byte array
  where nothing gives it a form, as in `[01]` with no `: form`.

### `Formed(term, form)`: any term with a form
`Formed` is `term : form`, "`term`, formed as `form`". It lets the form of any term come
from an expression, so a byte array's form can be a variable:
`(x -> y -> y : x) 'i1' [01]` evaluates to `[01] : 'i1'`. See `plan_annotation.md`.
- A byte array is only its bytes: `[01] : 'i8'` is `Formed(ByteArray([01]), 'i8')`, just
  like `y : 'i8'` is `Formed(y, 'i8')`. So every `:` that isn't on a binder is one term
  with one meaning, and beta reduction alone gives a dynamic form.
- `Formed` itself never reduces. `whnf` reduces inside `Formed.term`, and an `if` sees
  through a form on its condition.
- BANF translation turns a formed byte array into a constant. It rejects any other
  `Formed`, including a form on a formed byte array (`([01]:'i8'):'i16'`).
- `:` has its own precedence level, between `->`/`if`/`let` and application, and is
  right associative: `f a : g b` is `(f a) : (g b)`, `a : b : c` is `a : (b : c)`,
  `x -> y : t` is `x -> (y : t)`, and an argument needs parentheses: `f (y : x)`,
  `f ([01] : 'u8') [02]`. Without them, `f [01] : 'u8' [02]` is
  `(f [01]) : ('u8' [02])`.
- A lambda is tried first, so `x : F -> body` is still a lambda with a param form.

### Byte arrays are bracketed hex: `[2a 00 00 00] : 'i32'`
- The kernel has only byte arrays, so literals are written as bytes, not numbers.
- Bytes are little-endian on every target: `[2a000000] : 'i32'` is 42 everywhere.
  - Why fixed, not a default: oymomo has no integer literals, so the byte order is
    what gives a literal its number. With an overridable default, one source would
    mean two numbers. Same idea as WebAssembly memory and the `.bc` encoding: the
    encoding is fixed, the machine's byte order is a target detail.
  - Why: an evaluator (beta reduction plus prims) can run `add_i32` without a
    target, and it agrees with compiled code, so constant folding is safe.
  - A big-endian target gets big-endian bytes in memory: the LLVM translator
    emits the number (`i32 42`) and LLVM lays it out per `data_layout`.
  - Cost, later: once prims can reinterpret memory (store an `i32`, read bytes),
    a big-endian target sees bytes in a different order than the literal. Then
    either byte-swap loads and stores (as WebAssembly does) or call those prims
    target-dependent.
- Inside `[]`: groups of hex digits separated by whitespace. A group holds any
  number of bytes but has an even number of digits, so `[2a000000]`,
  `[2a00 0000]` and `[2a 00 00 00]` are the same bytes. `[]` is the empty array.
- Newlines are whitespace, so long arrays split without any continuation rule:
  ```
  [deadbeef cafebabe
   00112233 44556677] : {lo = 'i64', hi = 'i64'}
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
  for hex: `'Hi' : 'i16'`. A named form such as `'i32'` is a text byte array.
- Allowed characters: `0x20..0x7e` except `'` and `\`. No escapes, so bytes with
  `'`, `\`, or anything non-printable are written in hex. Keeping `\` out leaves
  room for escapes later. Single line only. `''` is the empty array.
- `'` was unused, and `"` is taken by quoted names.
- The printer uses `'...'` only for a byte array without a form (not the `t` of a
  `t : form`), every byte is text, and the array is at most 128 bytes; otherwise hex.
  Why: a written form (`[41]: 'i8'`) usually means a number, so hex stays; a long
  blob reads better as grouped hex. The limit is fixed, not `width`, so output
  doesn't depend on layout settings.

### Identifiers: plain or double quoted
Plain identifiers match `[A-Za-z_][A-Za-z0-9_]*`, excluding the reserved words
`if then else fix let in`. Any other non-empty string is written in double quotes:
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

### Comments use `//`
Kept after byte arrays moved to `[]`; `#` is now unused.

### `let x = e in body` is sugar for `(x -> body) e`
- No new term: the parser builds `Apply(Lambda(x, body), e)`, and the printer prints
  every apply of a lambda as a `let`. The optional form goes on the name, as on a
  lambda param: `let t0: 'i1' = prim.eq_i32 {...} in t0`.
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
  labels are what callers use (`decls.putchar {c = [41]: 'i8'}`).
- Why a dedicated term: it used to be a tagged struct
  `{tag = ' => ', param = P, result = R}`. Every consumer then had to tell it
  from a plain struct (shape, field order and tag checks), a hand-written struct
  could turn into a function form by accident, and BANF output and errors showed
  the encoding. A struct is now always a struct. Rejected: a tag member on
  `Struct` (nominal typing; maybe later) and `Lambda` as a Π type (keeps
  `Lambda` free for form constructors). Named `FunctionForm`, not `Arrow`: it
  names the meaning and leaves room for a separate function type.
- Why not `->` like a lambda: a different arrow tells a form from a term at a
  glance, in `decls: {putchar = {c = 'i8'} => 'i32'} -> defs -> ...` the `=>` is in a
  form and each `->` binds a lambda.
- Right-associative: `{a = 'i8'} => {b = 'i8'} => 'i32'` is
  `{a = 'i8'} => ({b = 'i8'} => 'i32')`. Parens group the other way.
- `=>` is an expression operator too, so a function form can be a struct field
  value: `{putchar = {c = 'i8'} => 'i32'}`. It binds tighter than application and
  looser than `.`: `f a => g b` is `f (a => g) b`.
- After a binder's `:`, the operands of `=>` are form atoms (struct, byte array, or
  parenthesized): `x: {c = 'i8'} => 'i32' -> x`.
- Why this is safe: `=>` is not a lambda's `->`, so in
  `decls: {} => 'i32' -> defs -> body` the form ends at `->` and `defs` stays a
  lambda binder.
- `=>` binds tighter than `:`, so `[00]: 'i8' => 'i32'` is a byte array whose form
  is a function form. So a param with a form needs parentheses:
  `([00]: 'i8') => 'i32'`. The printer adds them.

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
    another lambda stays on the same line, so `prim → decls: {} → defs → {`
    stays together;
  - an apply's argument goes on the next line, indented;
  - a `let` puts its body on the next line, at the `let`'s own indentation, so a
    chain of lets reads one let per line:
    ```
    entry = args: {n = 'i32'} →
      let t0 = prim.eq_i32 {a = args.n, b = [00000000]: 'i32'} in
      if t0 then f.then0 {} else f.else0 {n = args.n},
    ```
  - an `if` puts `then` and `else` on their own lines.
- An apply of a lambda prints as `let` in both modes: compact
  `let x:'i8' = e in body`, pretty `let x: 'i8' = e in body`.
- A `BruijnIndex` prints as `$0` and a `Variable` as its name, in both modes:
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
prim -> decls: {putchar = {c = 'i8'} => 'i32', errno = 'i32'} -> defs -> {
  main = f -> {entry = args:{} -> let t0 = decls.putchar {c = [41]:'i8'} in t0},
}
```

A program is three nested lambdas around a struct of definitions.

### `prim`: the machine primitives
`prim` is the struct of machine primitives (arithmetic, logic, comparison,
conversions): `prim.add_i32 {a = x, b = y}`.
- Why a separate binder: it separates machine-provided instructions from symbols.
  `prim.add_i32` is an instruction the machine provides, so it never becomes an
  LLVM symbol, while every `decls` and `defs` field does (`@putchar`, `@fact`).
  BANF keeps the split too: `PrimCall` for prims, `Call` for symbols.

### `decls`: imports, declared by the binder's form
`decls` is the struct of imports. Its form lists them; it has no value in the
source, because the linker provides it. Each field can be any form:
- A function form declares an imported function:
  `putchar = {c = 'i8'} => 'i32'` becomes `declare i32 @putchar(i8 %c)`.
- Any other form declares imported data:
  `errno = 'i32'` becomes `@errno = external global i32`.
- A module with no imports writes `decls: {}`. The `{}` form is required, so the
  translator always knows the import list.
- Why imports are separate from definitions: an earlier idea was to mix
  declarations into `defs`, with an empty byte array as a "no body" sentinel
  (`putchar = {c: i8} -> []:i32`, in the old form syntax). That mixes two kinds of things in one struct and
  needs a magic value. A typed binder says the same thing with no sentinel.
- Why not cross-module calls by name: every external symbol goes through `decls`,
  so a module lists everything it needs from outside, and the linker resolves it.

### `defs`: the module's own definitions
`defs` is the struct the program's body builds, passed back in so its functions
call each other by projection: `defs.fact {n = t1}`.
- Why: recursion and mutual recursion work without `fix`, just as LLVM functions
  call each other by symbol. A `fix` in the source is only unfolded while reducing
  to BANF's shape (see "oymomo to BANF"); it never becomes a loop or a call.

### Symbols
Every `decls` and `defs` field becomes one LLVM symbol, named after its label. A
name in both is an error: `decls: {main = 'i32'} -> defs -> {main = ...}`.

### Functions as structs of blocks
Each `defs` field is a function written as a struct of blocks:

```
fact = f -> {
  entry = args:{n = 'i32'} ->
    let t0 = prim.eq_i32 {a = args.n, b = [00000000]:'i32'} in
    if t0 then f.then0 {} else f.else0 {n = args.n},
  then0 = args:{} -> [01000000]:'i32',
  else0 = args:{n = 'i32'} ->
    let t1 = prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'} in
    let t2 = defs.fact {n = t1} in
    let t3 = prim.mul_i32 {a = args.n, b = t2} in
    t3,
}
```

- The binder (`f` here, any name) is the function's own blocks, so `f.then0 {}`
  jumps to a sibling block. It is the same self-reference trick as `defs`, one
  level down. Renaming calls it `blocks` (see "Binders get fixed names").
- Each block is a lambda taking one struct (`args:{n = 'i32'} -> ...`). The binder
  (`args` here, any name) is the block's param struct.
- The first field is the entry block, whatever its name.
- Why this shape: it is plain oymomo (lambdas, structs, application), so no new
  syntax was needed for blocks and jumps, and every name and label in the BANF
  output comes from the source.

### One argument, always a struct
An oymomo lambda takes exactly one argument. When a program is translated to BANF,
every block's argument must be a struct, and so must every prim op's and every
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
  `defs.add args` or `f.body args`.

## Prim ops

### Monomorphic: one op per signature
Each unique signature (param forms plus result form) is its own op:
`add_i32`, `add_i64`, `eq_i8`, `zext_i8_i32`, `trunc_i64_i32`. There is no generic
`add`.
- Why: a `PrimCall`'s result form is a table lookup, the same way a `Call`'s comes
  from its callee's signature. Nothing needs width inference, and conversions don't
  need a stored target form: `zext_i8_i32` always returns `i32`.
- Cost: many op names. They are generated from templates, not written by hand.
- Strict widths: `prim.add_i32 {a = [01]:'i8', b = ...}` is an error
  (`prim.add_i32 expects a: i32, got i8.`). Convert explicitly with `zext_i8_i32`.

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
  operand's role, so `prim.sub_i32 {minuend = x, subtrahend = y}` can't be read
  the wrong way round.
- Forms: `i1 i8 i16 i32 i64`. Arithmetic, shifts and ordered comparisons skip `i1`;
  `and or xor eq ne` include it (as boolean logic). No same-width conversions.
- `banf_prim.py` holds these signatures as plain data, with no LLVM;
  `llvm_prims.py` maps each one to llvmlite (`add_*` to `builder.add`, `slt_*` to
  `icmp_signed('<')`, `zext_i8_i32` to `zext(value, i32)`). A test checks that the
  two tables have the same op names.

## BANF

BANF: block-based ANF; SSA with block parameters instead of phi nodes, as in MLIR
and Cranelift.

```
fact: i32
  entry(n: i32):
    t0 = prim.eq_i32(n, [00000000]:i32)
    branch t0, then0(), else0(n)
  then0():
    return [01000000]:i32
  else0(n: i32):
    t1 = prim.sub_i32(n, [01000000]:i32)
    t2 = fact(t1)
    t3 = prim.mul_i32(n, t2)
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
    t0 = prim.add_i32(v, z)
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
  `args`, its lets, and the outer binders `f`, `prim`, `decls`, `defs`.

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
signature's return form, and on each `Data`. Ops and `Let`s carry no form, as in
Cranelift (`v0 = iadd v1, v2`).
- Why a `Const` has one: the same bytes can have many forms.
- Why a block param has one: a block has to declare what its jumps pass in.
- Why return forms are stored: calls read them, including recursive calls.
- Why not on `Let`: `form_of(op, forms, module)` computes it, and a stored form
  would be verbose. A `MakeStruct` result would repeat a full struct form such as
  `{x: i32, y: {lo: i64, hi: i64}}` on every line that builds or reads one.

`form_of` works out each op's result form:
- `PrimCall`: the op's result form from `banf_prim.py`.
- `Call`: the callee's `return_form`, whether it is a `Function` or a `Signature`.
- `MakeStruct`: each label paired with its field atom's form.
- `GetField`: that field's form inside the struct atom's form.
- `GetData`: the `Data` binding's form.

The printer, the verifier and the LLVM translator all use it while walking a
block, adding each let's form to the block's name table.

### Module = bindings, each with a name
```python
Module(bindings: list[Function | Signature | Data])
Function(name, return_form, blocks)       # blocks[0] is the entry block
Signature(name, params, return_form)       # imported function
Data(name, form)                           # imported data
```
- `name` is the LLVM symbol (`@fact`, `@putchar`, `@errno`). It lives on the
  binding instead of in `(name, binding)` tuples, which is simpler to carry around
  and to print.
- `Signature` needs its own `params` because it has no entry block to hold them.
- `Data` is read-only (oymomo has no assignment) but re-read on every use with
  `GetData`, because a value like `errno` can change outside the program. Not named
  `Global`, because every binding becomes an LLVM global.

### Printer
- A binding prints as `name = op` with no `let` keyword and no form, as in
  Cranelift: `t0 = prim.eq_i32(n, [00000000]:i32)`. That is unambiguous, because a
  block holds only lets plus one terminator, and every terminator starts with a
  keyword (`jump`, `branch`, `return`).
- Calls print with parentheses and commas (`fact(t1)`), so they don't read like
  oymomo's one-argument application.
- Calls and data reads use the symbol, not `defs.` / `decls.`: `t0 = errno`.
- Imports print first: `putchar(c: i8): i32` for a `Signature`, `errno: i32` for
  `Data`, then each function as `fact: i32` followed by its blocks.
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
4. `banf_translate.convert`: reads the shaped term into BANF, infers return forms,
   and raises `TranslationError` with a source location on any mismatch.

The golden tests approve the shaped term next to the BANF and LLVM output, as
`name.shaped.oymo`, and check that it translates to the same BANF.

### `reduce`: one step at the root
`bruijn.reduce(term)` takes one step if the root is a redex, and otherwise returns
`term` itself (so `reduce(t) is t` says "not a redex"). It never looks inside.
- beta: `(x -> body) e` gives `body` with `e` put in for `x`;
- fix: `fix g` gives `g (fix g)`;
- projection: `{a = e, ...}.a` gives `e`. A missing label is not a redex;
- if: `if [01] then a else b` gives `a`, and `if [00] ...` gives `b`.

- Only the root: arguments, lambda bodies, struct fields and `if` arms stay as
  they are, and so does a head whose root isn't a redex yet (`(fix g) a`,
  `{p = {a = e}}.p.a`). `banf_reduce` reduces heads.
- At most one rule applies to a term, so their order doesn't matter.
- It never raises and never recurses, so one call always finishes. Loops come
  from calling it again and again, so the fuel is in `banf_reduce`.
- Prims are not run (`prim` is only a binder), and an `if` condition's form isn't
  checked: only the one-byte values `01` and `00` are redexes.
- The helpers it uses are `shift`, `substitute`, `beta`
  (`shift(substitute(body, 0, shift(arg, 1)), -1)`), `unfold` and `project`.

### `banf_reduce`: reduce until each position has its shape
Each position wants certain constructors. The term there is reduced until it has
one, then its own positions are visited. Forms and binder kinds aren't checked
(except `args`, through `k` below); `convert` does that, so this pass needs no
context.

**Heads.** Some roots become a redex only after their head is reduced: in
`(fix g) a`, `fix g` must unfold to a lambda first. The head of an apply is its
callee, of a projection its struct, of an if its condition; other terms have
none.
```
step(t) = reduce(t)        if reduce(t) is not t                        -- a step at the root
        = t with head h'   if t has a head h, and h' = whnf(h) is not h   -- else reduce the head
        = t                otherwise

whnf(t) = whnf(step(t))    if step(t) is not t
        = t                otherwise
```
`whnf` stops at every Lambda, Struct, ByteArray and BruijnIndex, and at stuck terms
such as `prim.add_i32 {...}`, `args.n`, `blocks.done {...}` or `if t0 then a else b`.
- "Reduce `t` until it is X" means take `whnf(t)`, then look at its constructor.
  Looking first would be wrong: `{f = x -> ...}.f args.n` is already an apply, but
  its callee must be reduced before it is a call such as `prim.op {...}`.
- A position that already has a wanted constructor is not reduced further, since
  `whnf` stops there. So a let-bound struct stays a `MakeStruct`.

**Positions**, as numbered in `banf_reduce.py`:
1. The term, until a Lambda: `prim -> <decls>`.
2. `<decls>`, until a Lambda: `decls -> <defs>`.
3. `<defs>`, until a Lambda: `defs -> <body>`.
4. `<body>`, until a Struct: `{label = <func>, ...}`.
5. `<func>`, until a Lambda: `blocks -> <func_body>`.
6. `<func_body>`, until a Struct: `{label = <block>, ...}`.
7. `<block>`, until a Lambda: `args -> <block_body>`.
8. `<block_body>`, a chain of lets ending in a terminal:
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
      visit the op (9), and go on with `rest`. Otherwise beta-reduce the let and
      go on with the result.
   2. Else, if `step` changes the body, go on with that. This can make a let:
      in `(x -> y -> rest) a b` the head reduces and leaves `(y -> rest') b`.
   3. Else visit the terminal's positions and stop.
9. `<value>`, a let's op: an apply's `<op_arg>` becomes a struct of atoms or a
   BruijnIndex (forwarding `args`); a struct's fields become atoms; a
   projection's struct is a head, already reduced.
10. `<jump>`, an `if` arm: until `blocks.label <op_arg>`.
11. `<atom>`: until a ByteArray, `$i` with `i < k`, or `args.n`. `args` itself is
    not an atom: BANF passes a block's params one by one.

More rules:
- Because a let whose value isn't an op is beta-reduced, helpers are inlined,
  `let t = args.n in t` becomes `args.n`, and a let-bound `if` lands in tail
  position.
- A term that can't get its shape is left as it is, for `convert` to report with
  the usual message, so this pass has no errors except running out of fuel.
- Fuel: each step costs one unit, out of 10,000. A term that keeps reducing, such
  as `fix (self -> self)`, fails with "ran out of reduction steps".
- Nothing is flattened: a nested call stays nested and is an error, since
  flattening would mean inventing names.

### Binders get fixed names
The structural binders (positions 1, 2, 3, 5 and 7) are renamed to fixed names,
so every shaped program reads
`prim -> decls -> defs -> {main = blocks -> {entry = args -> ...}}`. `convert` then
checks each position by name, and a wrong name means a wrong shape.
- On any path from the root the five names appear once each, so they never clash.
- A position `banf_reduce` left without its shape is not structural: its binder
  follows the rule below, and `convert` reports the shape error.
- The fixed names don't reach BANF: `blocks.label` becomes a jump target and
  `args.n` becomes `banf.Var('n')`.

### Other binders keep their names unless they clash
A let keeps its name `x` unless `x` is visible: the name of an enclosing binder
(after renaming, so the five fixed names count), or a param label of its block.
Then it becomes `x_L`, else `x__L`, and so on, where `L` is its level (the number
of enclosing binders; a block's first let is level 5).
- `let t = ... in let t = ... in let t = ... in t` gives `t, t_6, t_7`.
- With `args: {n = 'i8'}`, two lets named `n` give `n_5, n_6`, since `n` is a param
  label: param labels become BANF `Var`s, as in `entry(n: i8)`.
- A user's own `t_6` after a renamed `t_6` gives `t_6_7`; `t, t_7, t` gives
  `t, t_7, t__7`. A let named `args` gives `args_5`.
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
  - `name$level` (`n$5`): it needs quotes, and `$` now starts a BruijnIndex.

### `convert` finds binders by index
Inside a block body with `k` lets so far, the binders above are always, from the
inside out: the lets (`$0` to `$k-1`), then `args` (`$k`), `blocks`, `defs`,
`decls`, `prim` (`$k+4`). So `convert` classifies each `BruijnIndex` by
arithmetic and keeps no binder names of its own. A let reference becomes a
`banf.Var` named after the BANF let already built.

### What the shape is
- **Let**: `let x = op in rest`, which is `(x -> rest) (op)`. The form may be
  omitted; if written, it must equal the op's form:
  `let t0: 'i32' = prim.eq_i32 {...} in t0` is an error, since `eq_i32` gives `i1`.
- **Atoms**: a byte array with a literal form (`[01] : 'i8'`), a let name, or `args.label`.
- **Ops**, only as a let's value: `prim.op {...}`, `defs.g {...}`, `decls.g {...}`,
  a struct literal of atoms (`MakeStruct`), a projection on an atom
  (`let x = args.p.x in ...` is a `GetField` on param `p`), or `decls.g` for
  imported data (`GetData`).
- **Terminators**, only in tail position:
  - `f.label {...}` is a jump.
  - `if c then f.a {...} else f.b {...}` is a branch. Both arms must be jumps.
  - An atom is returned.

### Operands must be atoms; nested calls are rejected
`prim.add_i32 {a = prim.add_i32 {...}, b = ...}` is an error; bind the inner call
with a let first.
- Why: allowing it means flattening nested calls into lets, which means inventing
  temporary names. That is normalization.

### An op in tail position must be bound first
`main = f -> {entry = args:{} -> let t0 = decls.putchar {c = [41]:'i8'} in t0}`,
not `... args:{} -> decls.putchar {c = [41]:'i8'}`.
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
`blocks`, `args`, `prim`, `decls` and `defs` used on their own are errors
(`'args' cannot be used as a value.`; the message uses the fixed name), except `args` forwarded as a whole call or
jump argument. So are `defs.g` and `decls.putchar` without an argument.
- Why: they have no runtime value. `prim` is not a struct anything could build.

### Return forms are inferred, to a fixed point
A function's return form is the form of its returned atoms, which must all agree.
It is iterated over the whole module, so a block returning a recursive call's
result resolves through another block:

```
loop = f -> {
  entry = args:{c = 'i1'} -> if args.c then f.a {} else f.b {},
  a = args:{} -> let t = defs.loop {c = [00]:'i1'} in t,
  b = args:{} -> [07]:'i8',
}
```

`a`'s return depends on `loop`'s, which `b` fixes as `i8`. A function with no
base case, like `g = f -> {entry = args:{} -> let t = defs.g {} in t}`, is an error.
- Why infer instead of requiring a written return form: block params and constants
  already carry forms, so the return form follows from them.

### Nested function forms are rejected, for now
A function form is accepted only as a `decls` field's whole form. These are
rejected until it's decided what they mean:
- inside a data form: `decls: {libc: {putchar: {c: i8} => i32}}`,
- as a param or result: `decls: {g: {c: i8} => {d: i8} => i32}`,
- with a non-struct param: `decls: {g: i8 => i32}`.

Void forms in `decls` are rejected too, since nothing can infer
an import's form.

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
- `GetData` is a `load` from the external global. `GetField` is `extractvalue`.

## Testing
- Unit tests per stage: `grammar_test.py`, `printer_test.py`, `banf_prim_test.py`,
  `banf_terms_test.py`, `bruijn_test.py`, `banf_reduce_test.py`,
  `banf_rename_test.py`, `banf_translate_test.py`, `llvm_translate_test.py`.
- BANF tests build modules by hand, so they don't depend on the translator.
- Every LLVM test parses the IR with `llvmlite.binding` and verifies it.
- Golden tests (`tests/goldens/`): each `name.oymo` produces approved
  `name.shaped.oymo`, `name.banf` and `name.ll` files.

## Not yet decided / not done
- Nested function forms (in data forms, or as a function form's param or result).
- Closures and higher-order functions.
- Struct constants in LLVM.
- The `language oymomo` header at the top of `.oymo` files is checked and stripped
  by the golden test; the parser doesn't handle layers yet.
- Void functions: every function returns a value.
