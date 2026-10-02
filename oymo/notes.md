
## Type vs Machine representation terminology

Type = semantic/program meaning
Form = logical structure/arrangement of components
Layout = physical memory representation

a TYPE may have multiple FORMs, and a FORM may have multiple LAYOUTs.

For examples
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
  form: (x:Int, y:Int)
  LLVM layout: { i32, i32 }
```

## Punctuation

{} braces denote structs (ordered fields), both terms `{x = 1}` and forms `{x: i32}`
() parentheses are used only for grouping
[] brackets denote byte arrays `[2a 00 00 00]`

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
// comment                   line comment
```

### Struct, not record
Fields keep their declaration order, and the order matters for layout. "Struct"
says that; "record" suggests an unordered set of labels.

### {} for structs, not []
Structs are written with braces, as in C and Rust. A struct term and a struct form
share `{}` and are told apart by `=` (term) vs `:` (form). This replaces the earlier
plan to use `[]`, which freed `[]` for byte arrays.

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
The arrow can be written `->` or `→` (U+2192); both mean the same. `→` reads like
the math notation, and `->` is easy to type on any keyboard. A printer emits `->`, so
generated code is plain ASCII. Lambda and `if` extend as far right as possible, so a lambda argument needs parens:
`f (x -> x)`.

### Forms are optional; omitted means "unknown"
Every `: form` may be left out: lambda params (`x -> body`), byte arrays (`[2a]`),
and struct form fields (`{x, y: i32}`). An omitted form is the string `'unknown'`,
the same as writing `: unknown`. `unknown` is an ordinary form name, not a reserved
word. This keeps quick sketches short while later stages decide what to infer.

### Byte arrays are bracketed hex: `[2a 00 00 00] : i32`
- The kernel has only byte arrays, so literals are written as bytes, not numbers.
- Bytes are in memory order: `[2a000000] : i32` is 42 on little-endian. Nothing is
  reinterpreted, so the source shows exactly what is stored.
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
  can have many forms.
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
- A printer quotes a name only when it is not a plain identifier.
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
  what callers use.
- Right-associative: `{a: i8} -> {b: i8} -> i32` is `{a: i8} -> ({b: i8} -> i32)`.
- An arrow form is allowed only as the form of a struct-form field or inside
  parentheses: `{putchar: {c: i8} -> i32}`, `x: ({c: i8} -> i32) -> x`. The form
  after a lambda's or byte array's `:` is a name, a struct form, or a parenthesized form.
- Why: in `decls: {...} -> defs -> body`, an unrestricted arrow form would parse
  `{...} -> defs` as one function form and swallow the `defs` binder.

## Program shape

```
prim -> decls: {putchar: {c: i8} -> i32, errno: i32} -> defs -> {
  main = f -> {entry = args:{} -> (t0 -> t0) (decls.putchar {c = [41]:i8})},
}
```

- `prim` is the struct of machine primitives (arithmetic, logic, comparison,
  conversions).
- `decls` is the struct of imports. Its form lists them, and each field can be any
  form: a function form declares an imported function, any other form declares
  imported data. The linker provides its value, so it has no body in the source.
  A module with no imports writes `decls: {}`.
- `defs` is the module's own struct of definitions, passed back in so its functions
  call each other by field access: `defs.increment {a = [00]:i8}`.
- Every `decls` and `defs` field becomes one symbol. A name in both is an error.
- An oymomo lambda takes exactly one argument. When a program is translated to
  BANF, every function's argument must be a struct, including every prim op's and
  every imported function's. Each prim op chooses field names that fit it:
  `prim.add_i32 {a = x, b = y}`, `prim.sub_i32 {minuend = x, subtrahend = y}`.
- Prim ops are monomorphic: each unique signature is a separate op, named by its
  forms (`add_i32`, `eq_i8`, `zext_i8_i32`).
- The translation to BANF expands the struct one level into multiple BANF
  parameters, which map one-to-one onto LLVM parameters.
- Function forms nested inside data forms are rejected for now.

### BANF
BANF: block-based ANF; SSA with block parameters instead of phi nodes, as in MLIR
and Cranelift.

The source is already written in BANF's shape; translation checks it and does no
normalization:
- A function is a struct of blocks: `f -> {entry = args:{n: i32} -> ..., ...}`.
  The binder `f` is the function's own blocks, so `f.then0 {...}` jumps to a
  sibling block. The first field is the entry block, whatever its name. Nothing
  jumps to the entry block.
- A block is a lambda taking one struct. Its fields become the block's params.
  Blocks are closed: a block sees only its own params and lets, so values from
  another block are passed in through jumps.
- A let is an applied lambda: `(t0 -> rest) (prim.eq_i32 {a = args.n, b = x})`.
  Its param form may be omitted.
- Operands are atoms: byte arrays, let names, or `args.label`. Ops (calls, struct
  literals, field accesses, imported data) appear only as a let's value.
- A block ends with a jump `f.label {...}`, a branch
  `if c then f.a {...} else f.b {...}`, or an atom that is returned.
- Let names are never renamed, so a let name may not repeat a param label, a
  binder, or an earlier let in the same block.

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