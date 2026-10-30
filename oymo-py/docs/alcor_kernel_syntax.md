# Alcor kernel syntax

Alcor has modern common-sense syntax that any programmer who knows a mainstream
language reads at once, a type is a layer-1 expression, and it lowers simply to oymomo.
This document holds the kernel syntax that is chosen, one numbered decision per topic.
Sugar waits until the kernel is complete; its notes are in
[alcor_sugar_syntax.md](alcor_sugar_syntax.md). The comparison both rest on is in
[alcor_survey.md](alcor_survey.md); "from" names the surveyed languages a choice is
borrowed from.

> [!IMPORTANT]
> Each decision is marked **Decided** (accepted) or **Proposed** (written by the agent,
> waiting for review). Only Decided parts are final.

## Rules

- Keep the form mainstream languages share (C's first) unless fixing a known problem.
- Two levels, as in oymomo: the **kernel** is the small core, and **sugar** is defined
  by rewriting into the kernel. Both are one language, `language alcor`: every kernel program is an Alcor program, and
  the docs call the subset the "Alcor kernel". The kernel is settled first; sugar comes
  after.
- Whatever sugar can write, the kernel can write too, just maybe more verbosely: sugar
  adds no power, only shorter forms.
- Everything is an expression; a block's value is its last expression.
- The kernel hides nothing (as Zig): no implicit conversions, no hidden calls, no
  operators that dispatch on a value's kind. What the kernel does is what it says;
  shorter forms come later as sugar.
- A left-out type means the dynamic type `Value` where there is no value to take a type
  from: a function parameter or a struct field. Layer-1 code is written this way, as in
  Python or Lua (gradual typing).
- A type is a layer-1 expression. (How kernel types are written, for example as calls
  such as `Ptr(T)`, is not decided yet.)
- Lowers to two oymomo programs: one evaluates the program (layer 0), the other
  type-checks it (layer 1).
- Borrowed, not invented: when two surveyed languages agree, take that.
- The kernel has no indentation syntax; indentation can come as sugar.
- Only what the compiler needs goes into Alcor (no floats, threads, atomics or SIMD).

## Decisions

### 0. Aim

**Decided:** a small systems language whose types are ordinary code, so checking is
written as programs, not built into the compiler.

1. **Modern common-sense syntax.** Any programmer who knows a mainstream language (C,
   Java, Go, Swift, Kotlin, Rust, Scala, …) reads it at once, without studying its
   syntax first. It is an expression language: `if`, `switch` and blocks give values.
2. **Two layers in one file.** Layer 0 is the program; layer 1 is code that computes and
   checks layer 0's types, including dependent and substructural types for memory safety
   where the code asks for it. The compiler has no type checker: checking is layer-1 code
   plus hand-written assertions, and raw pointers and C stay unchecked. Alcor writes one
   oymomo program per layer, and a closed program's layer 1 reduces to constants.
3. **Small.** Only what the compiler needs; the compiler itself will be written in Alcor.
4. **Mixes with C with no glue.** It calls C directly, can be called from C, and lowers
   through oymomo to LLVM and `clang`.

Common-sense syntax means the fixes most modern C successors share (counts are out of
the seventeen surveyed languages). The examples show the idea; the exact forms are
decided in their own sections below.

| Fix | C | Alcor |
|---|---|---|
| Declarations read left to right (12) | `char *(*f)(int);` | `let f: Ptr(Fn(i32, Ptr(u8))) = g;` |
| No fallthrough in `switch` (16) | `case 1: a(); break;` | `case 1: a();` (`fallthrough;` when wanted) |
| `.` works through pointers (10) | `p->x = 1; s.x = 1;` | `p.x = 1; s.x = 1;` |
| `defer` for cleanup (10; C's TS 25755) | `if (!f) goto fail; … fail: fclose(f);` | `defer fclose(f);` |
| Modules instead of headers (16) | `#include "list.h"` | `let list = import("list.oymo");` |
| Sized integer names (7) | `unsigned long n; int32_t x;` | `var n: u64 = 0; let x: i32 = 1;` |
| Braces always required ("goto fail") | `if (ok) a(); b();` | `if (ok) { a(); } b();` |
| Labelled break (11; C2y) | `goto done;` out of nested loops | `outer: for (…) { … break outer; }` |
| Number literals without traps (`_` 12, `0o` 7) | `0755`, `1000000` | `0o755`, `1_000_000` |
| Nesting block comments (9) | `/* a /* b */` ends at the first `*/` | `/* a /* b */ c */` is one comment |
| Tagged unions with a checked `switch` (8) | `struct { int kind; union { … } u; }` | `union Shape { circle: i32; rect: Point; }` |

What stays exactly as in C: `;`, braces, `if`/`while`/`for`, `return` (to leave early),
`&&`, `||`, `!`, `&x`, `*p`, `+=`, `//` comments, string escapes. C's `?:` goes: `if` is
an expression.

### 1. Declarations

**Decided:**

- `name: Type`, the name first and the type after a colon.
- Every declaration starts with a keyword, and bindings are immutable by default (from
  Swift, Carbon; Rust's `let`/`let mut`): `let` binds a value that can't be assigned
  again, `var` a variable. The type may be left out: it is the type of the value, and a
  literal's type comes from the literal itself (`0` an integer; a `Value` literal is
  marked, for example `0v`, spelling not decided).

  ```
  let total = 0;
  var count: i32 = 0;
  count += 1;
  ```

- No `const` keyword (as Zig: one keyword for every immutable binding). Whether a value
  must be known at build time comes from its use: in a type position, layer
  1 computes it and layer 0 gets the constant; a value used both ways exists in both
  layers. Using a run-time value there is a layer-1 error. A top-level `let` is
  read-only data; the translation folds it or stores it once.

  ```
  let N = 16;
  let buf: Array(u8, N) = undefined;    // N is known at build time
  let k = read_input();
  let bad: Array(u8, k) = undefined;    // layer-1 error: k is known only at run time
  let TABLE = "0123456789abcdef";       // top level: read-only data
  ```

- Every `let` and `var` needs a value (from Zig). `= undefined` says "no value yet" on
  purpose: `var buf: Array(u8, 64) = undefined;`. Later, a layer-1 check that a
  variable is assigned on every path before it is read will allow `var x: i32;` with no
  value (roadmap `assigned-before-use`).
- Immutability is checked by layer-1 code: each assignment's layer-1 version checks that
  its target is a `var`.
- Rejected: no keyword with `:=` (Odin, Jai, Cpp2), mutable by default (C), zero by
  default (Odin, Jai, D: a zero that should have been set looks valid, and no tool can
  catch it), C's indeterminate default, a `const` keyword for build-time values (Rust,
  C23 `constexpr`; a type position already marks build time), `::` constants (C++'s
  scope operator), `==` constants (Cpp2; a comparison to C readers).

### 2. Functions

**Decided:**

- The `fn` keyword, parameters as `name: Type`, the result after `->`:

  ```
  fn add(a: i32, b: i32) -> i32 { a + b }
  ```

- The body's last expression is the result (from Scala, Kotlin, Rust); `return` leaves
  early. `;` only separates: `{ a + b; }` also gives `a + b` (from Scala, Kotlin, not
  Rust's rule where `;` throws the value away). A function with no `->` ignores its
  body's value; a last expression of the wrong type is a layer-1 error.

- No `->` means no result (from Rust, Swift, Goose, Carbon, Odin, Jai):
  `fn log(s: Ptr(u8)) { … }`.
- A parameter with no type is a `Value`: `fn Ptr(T) -> Value { … }` takes any value. A
  function returning a `Value` still writes `-> Value`.
- No named or default arguments, as in C. An options struct does the job with no new
  feature (its literal waits for the struct literal, decision 4).
- No overloading, as in C: one function per name, so layer 0 can lower a call without
  layer 1 choosing among overloads.
- Parameters are immutable, like `let`; copy into a `var` to change one:
  `fn f(n: i32) { var m = n; m += 1; }`.
- Arguments are passed by value only; a pointer lets a function change the caller's
  data: `fn bump(p: Ptr(i32)) { *p += 1; }`.
- Several results are one struct: a declared struct type, or a struct type written in
  place with no name.
- A function takes one argument: its parameter list is a struct, so `add(1, 2)` passes
  one struct with two positional fields (decision 3).
- Rejected: Swift's argument labels in the function name, parameter modes (`in`,
  `inout`, `out`), `var` parameters, contracts (later, if needed).

### 3. Types

**Decided:**

- Integers are `i8 i16 i32 i64 u8 u16 u32 u64 usize isize` (from Zig, Odin, Hare, Goose,
  Carbon, Rust, Cpp2), and `bool` with `true`/`false`. There is no plain `int`. These are
  ordinary layer-1 names, not keywords.
- The kernel's types, written as calls for now (the spelling is not decided yet):

  | Kernel | Meaning |
  |---|---|
  | `Ptr(T)` | pointer to one `T`, never null, no arithmetic |
  | `Many(T)` | many-item pointer: `p[i]`, `p + 1` (from Zig, Odin, Hare) |
  | `Slice(T)` | pointer and length, bounds checked |
  | `Array(T, N)` | `N` values of `T`, a value that never decays |
  | `Option(T)` | maybe none (from Kotlin, Swift; Rust `Option<T>`) |
  | `Fn(T, R)` | function from `T` to `R` |

- `&x` takes an address and `*p` loads through a pointer, as in C, Go, Rust.
- A pointer is never null. Layer-1 code checks that an optional is tested before it is
  used (from Zig, Kotlin, Swift, Rust, Hare, Carbon). An optional pointer costs nothing
  at run time: null is "none". C's pointers come in as optionals.
- Every function takes exactly one argument; a struct with positional fields (a tuple)
  passes several values. `fn add(a: i32, b: i32) -> i32` takes a struct with fields
  `a` and `b`, so its type is `Fn(T, i32)` with `T` that struct type.
- `x as T` converts explicitly (from Rust, Kotlin, Hare, Goose, Carbon, Cpp2):
  `let b = n as u8;`. A value that doesn't fit in `T` is undefined behaviour: the checked
  build traps, the optimized build assumes it doesn't happen (decision 11). To truncate on
  purpose, make the value fit first: `(n & 0xff) as u8`.
- No implicit conversions (from Go, Rust, Kotlin, Swift, Odin, Hare): every conversion
  is written, so sugar will never need types to be rewritten.
- A string literal is a byte slice with a length, not NUL-terminated (from Go, Rust,
  Odin). A C string is written by hand: `"hi\0".ptr`, a `Many(u8)`.
- `Value` is a hand-made type, not a primitive: a tagged union in a library, with
  Lua-like kinds (integer, bool, bytes, table, function, type). In the kernel, working on
  a `Value` is explicit calls (`value_add(a, b)`); types are `Value`s too, so a type
  expression is an ordinary call on `Value`s (`Ptr(i32)`). (Proposed: the kinds and the
  names.)
- (Proposed) `Value` memory: an arena until the bootstrap, a pointer that moves forward
  and never frees (the layer-1 process exits and the operating system frees it). After
  the bootstrap a Lua-style incremental mark-and-sweep collector replaces it with the
  same interface (roadmap `value-gc`). `Value`s may be mutable; there is no reference
  counting. All allocation goes through the `Value` library and no program frees a
  `Value`, so the switch changes no program. Until then, a `Value` used at run time in
  long-running layer-0 code leaks.

### 4. Structs, enums, unions

**Decided:**

- No `struct` keyword: a struct type is a value bound with `let`, as in oymomo, where a
  struct of types is a struct type.
- A field with no type is a `Value`.
- Structs have C layout: fields in written order, with C's padding (from C, C3, Odin,
  Go, D, Zig `extern struct`).
- A tuple's fields are `t.0`, `t.1` (from Rust, Swift).

**Open:**

- The struct literal, for later: oymomo's `{x = 1, y = 2}` clashes with blocks
  (`{ x = 1 }` is also a block that assigns). Wanted: a form that mixes the two layers.
- Nominal types: leaning to a tag only layer 1 sees, written in the kernel as
  `let Meters = Named("app.Meters", f64);`, with layer 0 lowering `f64`.
- Virtual methods: roadmap leaf `interfaces`.
- Field defaults, `.` through pointers, plain enums, tagged unions (`enum` with payloads,
  or a tagged `union`).

### 5. Control flow

**Proposed:**

- `if (c) { … } else { … }`, `while (c) { … }` and C's `for (var i = 0; i < n; i += 1)`
  stay, with parentheses. Braces are required (C's dangling `else` and "goto fail").
- An each loop with `in` (from Odin, Swift, Rust, Goose, Carbon): `for (x in xs) { … }`,
  `for (i in 0..n) { … }`; `0..n` excludes `n`.
- `switch` keeps C's `case` shape, but a case ends without `break` (from C3, Swift);
  `fallthrough;` goes on to the next (from Odin, Swift). A `switch` on an enum or union
  must cover every case or have `default`. A case on a union binds the payload:

  ```
  let area = switch (s) {
    case .circle(r): 3 * r * r;
    case .rect(q):   q.x * q.y;
  };
  ```

- `defer` runs an expression at block exit, last first (from ten of seventeen, and C's TS
  25755): `defer fclose(f);`.
- Labelled loops, as C2y (from Odin, Swift, D): `outer: for (…) { break outer; }`.
- `i++` and `i--` give no value (from Goose, Cpp2): `a[i++]` is not allowed.
- `if`, `switch` and blocks are expressions (decision 2):
  `let x = if (c) { 1 } else { 2 };`. Loops and assignments give `{}`.
- Rejected: `goto`; implicit fallthrough; `=>` arms; C's `?:` (`if` does its job).

### 6. Errors

**Proposed:**

- An error is an ordinary tagged union. `Result(T, E)` and `Option(T)` are layer-1
  functions returning union types; there are no exceptions.
- `try e` returns the error from the current function, else gives the value (from Zig,
  Swift): `let n = try parse(s);`.
- Handling is a `switch` on the union.
- `unreachable;` marks code that must never run (from Zig, C23 `unreachable()`); in the
  checked build it traps.
- Rejected: exceptions and unwinding (C++, D); postfix `?` (easy to miss at the end of
  a line; `try` at the front shows where a function can return); Zig's error codes
  without data.

### 7. Compile-time code

**Proposed:**

- One build-time language: layer 1. There is no preprocessor, no macros, no `$if` or
  `#if` sublanguage.
- How a layer-0 value enters a type (the plan's `^`, as in `Array(u8, ^16)`) is decided
  later, with dependent types.
- Values needed at build time are computed by ordinary functions (as Zig, D, Jai).
- Conditional compilation is an ordinary `if` on a build-time condition, folded at build
  time: `if (TARGET.os == .linux) { … }`.
- Build-time functions replace the special forms: `embed("logo.png")` reads a file
  (C's `#embed`), `c_import("stdio.h")` reads a C header (decision 9).
- Rejected: Zig's `comptime` keyword (layer 1 makes it unneeded), C3's `$` names, Jai's
  `#run` with I/O (builds stay hermetic), Terra's second language.

### 8. Generics

**Proposed:**

- A type parameter is an ordinary layer-1 parameter of type `Type` (as the roadmap's
  `alcor-generics`):

  ```
  fn List(T: Type) -> Type { /* a struct type with fields items: Slice(T), len: usize */ }
  fn get(T: Type, l: List(T), i: usize) -> T { l.items[i] }
  let x = get(i32, nums, 3);
  ```

- Written as calls, `List(i32)`, `Map(K, V)` (from Zig, Carbon, Terra, Jai).
- Type arguments are explicit in the first version; inference stays open
  (`alcor-generics`).
- Lowering: one copy per type argument (from twelve of seventeen).
- Rejected: `<T>` (parsing ambiguity, C++'s `template`, Rust's `::<>`), `$T`, D's `!`.

### 9. Modules and C

**Proposed:**

- A file is a module. `import` is a build-time function returning the module's struct
  (from Zig): `let io = import("io.oymo");`, then `io.print(…)`.
- Names are private unless marked `pub` (from Zig, Hare, Rust, Swift).
- A C function is declared with `extern` (from Zig, C3, Goose, Rust, C++, D):
  `extern fn puts(s: Ptr(c_char)) -> i32;`. `export fn` gives an Alcor function C's name
  and ABI.
- C headers are imported by a build-time function, through libclang (from Carbon, Swift,
  Terra, D): `let c = c_import("stdio.h");`, then `c.puts("hi")`. The prefix keeps C
  names visible (as Carbon's `Cpp.`, Terra's `C.`).
- Rejected: header files; public by default; bindings generated by a separate tool
  (Rust's `bindgen`, Jai).

### 10. Memory

**Proposed:**

- Code that allocates takes the allocator as an explicit parameter (decided earlier for
  the memory model, from Zig, C3): `let p = alloc(a, Point);`, `free(a, p);`.
- `defer` frees: `defer free(a, p);`.
- No hidden allocation, no destructors, no GC in the language.
- Unchecked conversions (`Ptr(T)` to `Own(T, A)`) go in an `unsafe { … }` block (from
  Rust; Swift's strict mode). The owned and borrowed types themselves are
  `alcor-safety-syntax`.
- Rejected: Odin's and Jai's implicit context (a hidden parameter on every call), RAII
  (invisible calls), D's function-level `@trusted`.

### 11. Undefined behaviour

**Proposed:**

- Two build modes (the `alcor-ub` proposal, as Zig and C3): **checked** traps with a
  message and location on overflow, out of bounds, null and `unreachable`;
  **optimized** leaves them undefined, as C and LLVM.
- Explicit wrapping operators `+%`, `-%`, `*%` are defined in both modes (from Zig; Swift
  `&+`, Rust `wrapping_add`).
- Every variable starts with a value (decision 1), so uninitialized reads come only
  from `= undefined`.
- Rejected for now: a third "hardened" mode (Carbon), per-scope opt-out (Zig, Odin,
  Jai), wrapping signed overflow by default (C3, Odin, D: hides bugs).

### 12. Lexical details

**Proposed:**

- `;` separates expressions and declarations, as in C; it may end a block's last
  expression without changing its value; not needed after a closing `}` of a function
  or type.
- Comments: `//` and `/* */`; block comments nest (from C3, Odin, Jai, Goose, Swift,
  Rust, D).
- Numbers: `0x`, `0o`, `0b`, `_` separators (`1_000_000`, from twelve of seventeen); a
  leading `0` is an error (as D), not octal.
- Strings: `"…"` with C escapes; raw strings in backticks, which may span lines (from C3,
  Odin, Hare, D). `'a'` is a `u8`.
- Operators: C's `&& || !`, no `and`/`or` words.
- A small keyword set; type names (`i32`, `bool`) and built-ins (`alloc`, `import`) are
  ordinary names.
- Rejected: optional semicolons (Odin, Swift), `'` digit separators (C23, C++),
  `//`-only comments (Zig, Hare, Carbon).
