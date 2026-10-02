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
  form: i1
  LLVM layout: i1

Int32
  type: Int
  form: i32
  LLVM layout: i32

Point
  type: Point(x: Int, y: Int)
  form: {x: i32, y: i32}
  LLVM layout: { i32, i32 }
```

Why three words: the kernel (oymomo) and BANF only know forms. Types belong to
higher layers, and layouts belong to the backend (LLVM). Keeping the words apart
stops a backend detail like "i32 is 4-byte aligned" from leaking into the
kernel, where `[2a000000]:i32` only says "these bytes, read as the form i32".

## Pipeline

```
oymomo source --parse--> oymomo terms --banf_translate--> BANF --llvm_translate--> LLVM IR
```

- oymomo: the lambda-calculus kernel language. Surface syntax in `grammar.py`,
  terms in `terms.py`.
- BANF: a first-order IR shaped like LLVM, with block params instead of phi nodes
  (see "BANF" below).
- LLVM: generated with llvmlite.

### Files are flat, with prefixes
Everything sits in `oymo/src/oymo/oymomo/`:
`banf_terms.py`, `banf_prim.py`, `banf_translate.py`, `llvm_prims.py`,
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
{}  structs (ordered fields): terms {x = 1} and forms {x: i32}
()  grouping only
[]  byte arrays [2a 00 00 00]
```

Why each bracket has one job: the parser never has to guess. `(` always groups,
`{` is always a struct, and `[` is always bytes.

## Kernel syntax decisions

Surface syntax of the oymomo kernel lambda calculus:
```
x : i32 -> body              Lambda
f a b                        Apply
{x = e1, y = e2}             Struct
s.x                          FieldAccess
if c then a else b           If
fix f                        Fix
[2a 00 00 00] : i32          ByteArray
{c: i8} -> i32               FunctionForm (in form position)
// comment                   line comment
```

### Struct, not record
Fields keep their declaration order, and the order matters for layout:
`{x: i32, y: i8}` and `{y: i8, x: i32}` are different forms with different LLVM
types (`{i32, i8}` vs `{i8, i32}`). "Struct" says that; "record" suggests an
unordered set of labels.

### {} for structs, not []
Structs are written with braces, as in C and Rust. A struct term and a struct form
share `{}` and are told apart by `=` (term) vs `:` (form):
`{x = [01]:i8}` is a value, `{x: i8}` is its form. This replaces the earlier plan
to use `[]`, which freed `[]` for byte arrays.

### FieldAccess for `s.x`
It pairs with the `Field` class and is what C, Rust, and Java call `s.x`. We first
kept `Select` to stay with one-word verbs like `Apply` and `Fix`, then chose clarity
over that preference.
Rejected: `Select` (unclear), `Project`/`Proj` (type-theory jargon), `Access`
and `Read` (sound like memory operations next to LLVM), `Field` (taken by the
`Field` class), `Member` (C++ flavored, suggests methods), `Get` (reads like a
function call), `Dot` (names the syntax, not the meaning), and `Pick`, `Take`,
`Pluck`, `Extract`, `Lookup`, `Focus`.

### Lambda as `x : form -> body`
- The arrow can be written `->` or `→` (U+2192); both mean the same. `→` reads like
  the math notation, and `->` is easy to type on any keyboard. A printer emits `->`,
  so generated code is plain ASCII.
- Lambda and `if` extend as far right as possible: `a -> b -> a b` is
  `a -> (b -> (a b))`. So a lambda argument needs parens: `f (x -> x)`, while
  `f x -> x` is a syntax error.
- Application is left-associative and binds looser than field access:
  `f a.x b` is `(f a.x) b`.

### Forms are optional; omitted means "unknown"
Every `: form` may be left out: lambda params (`x -> body`), byte arrays (`[2a]`),
and struct form fields (`{x, y: i32}`). An omitted form is the string `'unknown'`,
the same as writing `: unknown`. `unknown` is an ordinary form name, not a reserved
word.
- Why: quick sketches stay short, and each later stage decides what it can infer.
  BANF translation, for example, infers a let's form from its op, so
  `(t0 -> t0) (prim.eq_i32 {...})` needs no `t0: i1`. It rejects an unknown form
  where nothing can infer it, as in a byte array `[01]` with no form.

### Byte arrays are bracketed hex: `[2a 00 00 00] : i32`
- The kernel has only byte arrays, so literals are written as bytes, not numbers.
- Bytes are little-endian on every target: `[2a000000] : i32` is 42 everywhere.
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
   00112233 44556677] : {lo: i64, hi: i64}
  ```
- Comments are not allowed inside the brackets.
- `[]` was freed when structs took `{}`, and the brackets bound the literal, so no
  prefix and no quotes are needed.
- The form after `:` is optional (omitted means `unknown`), since the same bytes
  can have many forms: `[01000000]` could be `i32` 1, or `{a: i16, b: i16}`.
- Rejected: a prefix sigil (`#2a000000`, also `%`, `$`, `@`), which needed `_`
  separators and a `_` line continuation; `0x...`, which reads as an integer and
  hides the byte order; backticks, which look like quoting; juxtaposing literals,
  because juxtaposition is already application.

### Identifiers: plain or double quoted
Plain identifiers match `[A-Za-z_][A-Za-z0-9_]*`, excluding the reserved words
`if then else fix`. Any other non-empty string is written in double quotes:
`"a b"`, `"if"`, `"main.1"`.
- LLVM does the same (`@main` vs `@"foo bar"`), so kernel names map directly to
  symbols, including mangled names from higher-level languages. SQL also uses `"..."`.
- `"x"` and `x` are the same name; the parser stores the decoded string.
- Escapes: `\"`, `\\`, `\u{hex}`. No raw newlines. `""` is rejected.
- Quotes work everywhere a name appears: variables, lambda parameters, struct
  labels, field access labels (`s."a b"`), and form names.
- A printer quotes a name only when it is not a plain identifier. The BANF printer
  does too: `Data('my data', 'i8')` prints as `"my data": i8`.
- Plain identifiers stay ASCII; other names use quotes. This avoids Unicode
  identifier rules and confusable characters.
- Cost: `"` is not available for string literals. The kernel has none.
  Rejected: Zig-style `@"..."`, only worth it if strings come.

### Comments use `//`
Kept after byte arrays moved to `[]`; `#` is now unused.

### No surface syntax for BruijnIndex
Name resolution produces it; users write names.

### Function forms: `{c: i8} -> i32`
- A function form is written with `->` or `→`, like a lambda. It has one param,
  matching one-argument lambdas, and no param name: the struct form's labels are
  what callers use (`decls.putchar {c = [41]:i8}`).
- Right-associative: `{a: i8} -> {b: i8} -> i32` is `{a: i8} -> ({b: i8} -> i32)`.
  Parens group the other way: `({a: i8} -> {b: i8}) -> i32`.
- An arrow form is allowed only as the form of a struct-form field or inside
  parentheses: `{putchar: {c: i8} -> i32}`, `x: ({c: i8} -> i32) -> x`. The form
  after a lambda's or byte array's `:` is a name, a struct form, or a parenthesized
  form.
- Why: in `decls: {...} -> defs -> body`, an unrestricted arrow form would parse
  `{...} -> defs` as one function form and swallow the `defs` binder. The grammar
  has two rules: `FORM` (name, struct form, or parenthesized `ARROW_FORM`) and
  `ARROW_FORM` (`FORM -> ARROW_FORM` or `FORM`). Struct-form fields use
  `ARROW_FORM`.

## Program shape

```
prim -> decls: {putchar: {c: i8} -> i32, errno: i32} -> defs -> {
  main = f -> {entry = args:{} -> (t0 -> t0) (decls.putchar {c = [41]:i8})},
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
  `putchar: {c: i8} -> i32` becomes `declare i32 @putchar(i8 %c)`.
- Any other form declares imported data:
  `errno: i32` becomes `@errno = external global i32`.
- A module with no imports writes `decls: {}`. The `{}` form is required, so the
  translator always knows the import list.
- Why imports are separate from definitions: an earlier idea was to mix
  declarations into `defs`, with an empty byte array as a "no body" sentinel
  (`putchar = {c: i8} -> []:i32`). That mixes two kinds of things in one struct and
  needs a magic value. A typed binder says the same thing with no sentinel.
- Why not cross-module calls by name: every external symbol goes through `decls`,
  so a module lists everything it needs from outside, and the linker resolves it.

### `defs`: the module's own definitions
`defs` is the struct the program's body builds, passed back in so its functions
call each other by field access: `defs.fact {n = t1}`.
- Why: recursion and mutual recursion work without `fix`, just as LLVM functions
  call each other by symbol. The translator rejects `fix`.

### Symbols
Every `decls` and `defs` field becomes one LLVM symbol, named after its label. A
name in both is an error: `decls: {main: i32} -> defs -> {main = ...}`.

### Functions as structs of blocks
Each `defs` field is a function written as a struct of blocks:

```
fact = f -> {
  entry = args:{n: i32} ->
    (t0 -> if t0 then f.then0 {} else f.else0 {n = args.n})
      (prim.eq_i32 {a = args.n, b = [00000000]:i32}),
  then0 = args:{} -> [01000000]:i32,
  else0 = args:{n: i32} ->
    (t1 -> (t2 -> (t3 -> t3) (prim.mul_i32 {a = args.n, b = t2}))
             (defs.fact {n = t1}))
      (prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:i32}),
}
```

- The binder (`f` here, any name) is the function's own blocks, so `f.then0 {}`
  jumps to a sibling block. It is the same self-reference trick as `defs`, one
  level down.
- Each block is a lambda taking one struct (`args:{n: i32} -> ...`). The binder
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
  oymomo: fact = f -> {entry = args:{n: i32} -> ...}
  BANF:   entry(n: i32)
  LLVM:   define i32 @fact(i32 %n)
  ```
- Only one level: `args:{p: {x: i32, y: i32}}` gives one param `p` whose form is a
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
- Strict widths: `prim.add_i32 {a = [01]:i8, b = ...}` is an error
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
eq ne                        {a: T, b: T} -> i1
slt sle sgt sge ult ule ugt uge   {lhs: T, rhs: T} -> i1
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

## oymomo to BANF: a shape checker, not a normalizer

The source must already be in BANF's shape. The translator only matches it,
expands struct arguments, infers return forms, and raises `TranslationError` with
a source location on any mismatch. It generates no blocks, renames nothing, and
invents no names.
- Why: the kernel stays a direct, readable spelling of the IR, and the translator
  stays small and predictable, since every BANF line comes from one source term.
  Normalizing arbitrary expressions (nested calls, `if` in operand position) is a
  job for a higher layer that emits oymomo in this shape.

### What the shape is
- **Let**: an applied lambda, `(x -> rest) (op)`. The param form may be omitted;
  if written, it must equal the op's form:
  `(t0: i32 -> t0) (prim.eq_i32 {...})` is an error, since `eq_i32` gives `i1`.
- **Atoms**: a byte array with a known form, a let name, or `args.label`.
- **Ops**, only as a let's value: `prim.op {...}`, `defs.g {...}`, `decls.g {...}`,
  a struct literal of atoms (`MakeStruct`), a field access on an atom
  (`(x -> ...) (args.p.x)` is a `GetField` on param `p`), or `decls.g` for
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
`main = f -> {entry = args:{} -> (t0 -> t0) (decls.putchar {c = [41]:i8})}`,
not `... args:{} -> decls.putchar {c = [41]:i8}`.
- Why: a BANF `Return` takes an atom. Accepting a tail op would make the
  translator invent a name for the result; the explicit `(t0 -> t0)` keeps every
  name in the source.

### `if` only in tail position, with jumps in both arms, to different blocks
`(t -> ...) (if c then ...)` is an error, and so is
`if c then [01]:i8 else f.b {}`.
- Why: a BANF `Branch` is a terminator with two targets. An `if` whose value is
  used needs a join block, and the source writes that block explicitly.
- Why different targets: `if c then f.a {} else f.a {}` would give `a` two
  incoming edges from the same block, and an LLVM phi can't tell those edges apart.

### Let names are never renamed
A let name may not repeat a block param label, a binder (`f`, `args`, `prim`,
`decls`, `defs`), or an earlier let in the same block. These are errors:
- `args:{n: i8} -> (n -> n) (...)`: `n` is also a param label.
- `(t -> (t -> t) (...)) (...)`: shadows an earlier `t`.
- Why: BANF names are the source names. Without renaming, any shadowing would put
  two values under one BANF name, so it is rejected.

### Binders can't be used as values
`f`, `args`, `prim`, `decls` and `defs` used on their own are errors
(`'args' cannot be used as a value.`), except `args` forwarded as a whole call or
jump argument. So are `defs.g` and `decls.putchar` without an argument.
- Why: they have no runtime value. `prim` is not a struct anything could build.

### Return forms are inferred, to a fixed point
A function's return form is the form of its returned atoms, which must all agree.
It is iterated over the whole module, so a block returning a recursive call's
result resolves through another block:

```
loop = f -> {
  entry = args:{c: i1} -> if args.c then f.a {} else f.b {},
  a = args:{} -> (t -> t) (defs.loop {c = [00]:i1}),
  b = args:{} -> [07]:i8,
}
```

`a`'s return depends on `loop`'s, which `b` fixes as `i8`. A function with no
base case, like `g = f -> {entry = args:{} -> (t -> t) (defs.g {})}`, is an error.
- Why infer instead of requiring a written return form: block params and constants
  already carry forms, so the return form follows from them.

### Nested function forms are rejected, for now
A function form is accepted only as a `decls` field's whole form. These are
rejected until it's decided what they mean:
- inside a data form: `decls: {libc: {putchar: {c: i8} -> i32}}`,
- as a param or result: `decls: {g: {c: i8} -> {d: i8} -> i32}`,
- with a non-struct param: `decls: {g: i8 -> i32}`.

Unknown forms in `decls` (`{g: unknown}`) are rejected too, since nothing can infer
an import's form.

### First-order only
No closures and no escaping lambdas: the only lambdas are the program binders,
function, block and let lambdas. Everything else is an error.

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
- Unit tests per stage: `grammar_test.py`, `banf_prim_test.py`,
  `banf_terms_test.py`, `banf_translate_test.py`, `llvm_translate_test.py`.
- BANF tests build modules by hand, so they don't depend on the translator.
- Every LLVM test parses the IR with `llvmlite.binding` and verifies it.
- Golden tests (`tests/goldens/`): each `name.oymo` produces approved `name.banf`
  and `name.ll` files.

## Not yet decided / not done
- Nested function forms (in data forms, or as a function form's param or result).
- Closures and higher-order functions.
- Struct constants in LLVM.
- The `language oymomo` header at the top of `.oymo` files is checked and stripped
  by the golden test; the parser doesn't handle layers yet.
- Void functions: every function returns a value.
