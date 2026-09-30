
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