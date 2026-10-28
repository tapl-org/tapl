# Alcor syntax

Alcor is "C, but modern": a C programmer reads it at once, a type is a layer-1
expression, and it lowers simply to oymomo. This document holds the syntax that is
chosen, one numbered decision per topic. The comparison it rests on is in
[alcor_survey.md](alcor_survey.md); "from" names the surveyed languages a choice is
borrowed from.

> [!IMPORTANT]
> Each decision is marked **Decided** (accepted) or **Proposed** (written by the agent,
> waiting for review). Only Decided parts are final.

## Rules

- Keep C's form unless fixing a known C problem.
- A type is a layer-1 expression: types are written as ordinary calls (`Ptr(T)`,
  `Array(u8, ^16)`), never as type-only syntax.
- Lowers simply to oymomo.
- Borrowed, not invented: when two surveyed languages agree, take that.
- No indentation syntax.
- Only what the compiler needs goes into Alcor (no floats, threads, atomics or SIMD).

## Decisions

### 0. Aim

**Decided:** a small systems language whose types are ordinary code, so checking is
written as programs, not built into the compiler.

1. **C, but with modern common-sense syntax.** A C programmer reads it at once: someone
   who knows C can read Alcor code without studying its syntax first.
2. **Two layers in one file.** Layer 0 is the program; layer 1 is code that computes and
   checks layer 0's types, including dependent and substructural types for memory safety
   where the code asks for it. The compiler has no type checker: checking is layer-1 code
   plus hand-written assertions, and raw pointers and C stay unchecked. Alcor writes one
   oymomo program per layer, and a closed program's layer 1 reduces to constants.
3. **Small.** Only what the compiler needs; the compiler itself will be written in Alcor.
4. **Mixes with C with no glue.** It calls C directly, can be called from C, and lowers
   through oymomo to LLVM and `clang`.

Common-sense syntax means the fixes most modern C successors share (counts are out of
the thirteen surveyed languages). The examples show the idea; the exact forms are
decided in their own sections below.

| Fix | C | Alcor |
|---|---|---|
| Declarations read left to right (10) | `char *(*f)(int);` | `f: Ptr(fn(i32) -> Ptr(u8));` |
| No fallthrough in `switch` (12) | `case 1: a(); break;` | `case 1: a();` (`fallthrough;` when wanted) |
| `.` works through pointers (9) | `p->x = 1; s.x = 1;` | `p.x = 1; s.x = 1;` |
| `defer` for cleanup (9; C's TS 25755) | `if (!f) goto fail; … fail: fclose(f);` | `defer fclose(f);` |
| Modules instead of headers (12) | `#include "list.h"` | `const list = import("list.oymo");` |
| Sized integer names (7) | `unsigned long n; int32_t x;` | `n: u64; x: i32;` |
| Braces always required ("goto fail") | `if (ok) a(); b();` | `if (ok) { a(); } b();` |
| Labelled break (8; C2y) | `goto done;` out of nested loops | `outer: for (…) { … break outer; }` |
| Number literals without traps (`_` 8, `0o` 6) | `0755`, `1000000` | `0o755`, `1_000_000` |
| Nesting block comments (7) | `/* a /* b */` ends at the first `*/` | `/* a /* b */ c */` is one comment |
| Tagged unions with a checked `switch` (7) | `struct { int kind; union { … } u; }` | `union Shape { circle: i32; rect: Point; }` |

What stays exactly as in C: `;`, braces, `if`/`while`/`for`/`return`, `&&`, `||`, `!`,
`&x`, `*p`, `?:`, `+=`, `//` comments, string escapes.

### 1. Declarations

**Decided:** `name: Type`, the name first and the type after a colon, with no keyword:

```
count: i32 = 0;
```

**Proposed:**

- Type inference with `:=` (from Odin, Jai, Cpp2): `total := 0;`.
- Build-time constants with `const` (C's word; Zig, Rust): `const MAX: i32 = 100;`,
  `const MAX := 100;`. A `const` is a layer-1 value, usable in types (`Array(u8, ^MAX)`).
- Variables are mutable, as in C; no `let`/`var`.
- A variable without a value is zero (from Odin, Jai, D); `= undefined` leaves it
  uninitialized on purpose (Zig's word): `buf: Array(u8, ^64) = undefined;`.
- Rejected: `::` constants (`::` is C++'s scope operator), `==` constants (Cpp2; a
  comparison to C readers), C's indeterminate default.

### 2. Functions

**Decided:** the `fn` keyword, parameters as `name: Type`, the result after `->`:

```
fn add(a: i32, b: i32) -> i32 { return a + b; }
```

**Proposed:**

- No `->` means no result: `fn log(s: Ptr(u8)) { … }`.
- Several results are named and returned as one struct (from Odin, Jai, Cpp2):

  ```
  fn divmod(a: i32, b: i32) -> (q: i32, r: i32) { return (a / b, a % b); }
  q, r := divmod(7, 2);
  ```

- Named arguments with `:` and default values (from C3, D, Swift): `open(path, create:
  true)`, `fn open(path: Ptr(u8), create: bool = false)`. `name = value` (Odin, Jai) is
  rejected: in C, `f(x = 3)` is an assignment.
- No overloading, as in C.
- Rejected: Swift's argument labels in the function name, parameter modes (`in`,
  `inout`), contracts (later, if needed).

### 3. Types

**Proposed:**

- Integers: `i8 i16 i32 i64 u8 u16 u32 u64 usize isize` (from Zig, Odin, Hare, Rust,
  Carbon, Cpp2), `bool` with `true`/`false`. These are ordinary layer-1 names, not
  keywords.
- Every other type is a layer-1 call (as the Alcor plan already writes them):

  | Type | Meaning | C |
  |---|---|---|
  | `Ptr(T)` | raw pointer to one `T`, may be null | `T *` |
  | `Array(T, ^N)` | `N` values of `T`, a value that never decays | `T a[N]` |
  | `Slice(T)` | pointer and length, bounds checked | `T *p, size_t n` |
  | `Ptr(Array(T, n))` | pointer to `n` values, `n` known at run time | `T *` |
  | `fn(i32, i32) -> i32` | function type | `int (*)(int, int)` |

- Pointers: `&x` takes an address, `*p` loads, as in C. No pointer arithmetic on
  `Ptr(T)`; index through an array or a slice (`buf[i]`).
- Casts: no implicit conversions; `x as T` converts explicitly (from Hare, Goose, Carbon,
  Rust, Cpp2): `b := n as u8;`. Narrowing truncates, as C's cast does.
- `null` is the null `Ptr(T)`. Non-null pointers (`Ref(T)`, `Own(T, A)`) come with the
  safety types (`alcor-safety-syntax`).
- Rejected: prefix `*T`, `[]T`, `[N]T` (type-only syntax, against "a type is a layer-1
  expression"); C's decaying arrays; Swift's long pointer names.

### 4. Structs, enums, unions

**Proposed:**

- Structs keep C's form with `name: Type` fields; `struct Point {…}` is sugar for the
  layer-1 form `const Point = struct {…};`:

  ```
  struct Point { x: i32; y: i32; }
  p := Point{ .x = 1, .y = 2 };
  ```

- Literals are C's designated initializers after the type name (from C, C3, Zig, Carbon,
  C++); missing fields are zero.
- `.` works through pointers; there is no `->` (from nine of thirteen): `pp.x`.
- Enums: `enum Color: u8 { red, green, blue }`, used `Color.red`, or `.red` where the
  type is known (from Zig, Odin, Jai).
- `union` is tagged (from Zig, Odin, Hare, Goose, Carbon, Swift, Rust); `switch` checks
  every case. `extern union` is C's untagged union, for C interop.

  ```
  union Shape { circle: i32; rect: Point; }
  ```

- No methods; a call `p.len()` means `len(p)` when `p` has no field `len` (UFCS, from
  Goose, D, Cpp2). It lowers to a plain call.
- Rejected: classes, `impl` blocks, C's `struct` tag namespace, `enum` for tagged unions
  (Rust, Swift; it changes C's meaning of `enum`).

### 5. Control flow

**Proposed:**

- `if (c) { … } else { … }`, `while (c) { … }` and C's `for (i := 0; i < n; i += 1)`
  stay, with parentheses. Braces are required (C's dangling `else` and "goto fail").
- An each loop with `in` (from Odin, Swift, Rust, Goose, Carbon): `for (x in xs) { … }`,
  `for (i in 0..n) { … }`; `0..n` excludes `n`.
- `switch` keeps C's `case` shape, but a case ends without `break` (from C3, Swift);
  `fallthrough;` goes on to the next (from Odin, Swift). A `switch` on an enum or union
  must cover every case or have `default`. A case on a union binds the payload:

  ```
  switch (s) {
    case .circle(r): area = 3 * r * r;
    case .rect(q):   area = q.x * q.y;
  }
  ```

- `defer` runs a statement at block exit, last first (from nine of thirteen, and C's TS
  25755): `defer fclose(f);`.
- Labelled loops, as C2y (from Odin, Swift, D): `outer: for (…) { break outer; }`.
- `i++` and `i--` are statements only, never expressions (from Goose, Cpp2).
- `?:` stays; `if` and `switch` are statements.
- Rejected: `goto`; implicit fallthrough; `=>` arms; `if` and `switch` as expressions
  (later, if needed).

### 6. Errors

**Proposed:**

- An error is an ordinary tagged union. `Result(T, E)` and `Option(T)` are layer-1
  functions returning union types; there are no exceptions.
- `try e` returns the error from the current function, else gives the value (from Zig,
  Swift): `n := try parse(s);`.
- Handling is a `switch` on the union.
- `unreachable;` marks code that must never run (from Zig, C23 `unreachable()`); in the
  checked build it traps.
- Rejected: exceptions and unwinding (C++, D); postfix `?` (clashes with `?:` in a C
  reader's eye); Zig's error codes without data.

### 7. Compile-time code

**Proposed:**

- One build-time language: layer 1. There is no preprocessor, no macros, no `$if` or
  `#if` sublanguage.
- `^e` lifts a build-time value into a type (as the Alcor plan writes it):
  `Array(u8, ^16)`, `Matrix(^2, ^3)`.
- `const` names are computed at build time by ordinary functions (as Zig, D, Jai).
- Conditional compilation is an ordinary `if` on a `const` condition, folded at build
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
  fn List(T: Type) -> Type { return struct { items: Slice(T); len: usize; }; }
  fn get(T: Type, l: List(T), i: usize) -> T { return l.items[i]; }
  x := get(i32, nums, 3);
  ```

- Written as calls, `List(i32)`, `Map(K, V)` (from Zig, Carbon, Terra, Jai).
- Type arguments are explicit in the first version; inference stays open
  (`alcor-generics`).
- Lowering: one copy per type argument (from twelve of thirteen).
- Rejected: `<T>` (parsing ambiguity, C++'s `template`, Rust's `::<>`), `$T`, D's `!`.

### 9. Modules and C

**Proposed:**

- A file is a module. `import` is a build-time function returning the module's struct
  (from Zig): `const io = import("io.oymo");`, then `io.print(…)`.
- Names are private unless marked `pub` (from Zig, Hare, Rust, Swift).
- A C function is declared with `extern` (from Zig, C3, Goose, Rust, C++, D):
  `extern fn puts(s: Ptr(c_char)) -> i32;`. `export fn` gives an Alcor function C's name
  and ABI.
- C headers are imported by a build-time function, through libclang (from Carbon, Swift,
  Terra, D): `const c = c_import("stdio.h");`, then `c.puts("hi")`. The prefix keeps C
  names visible (as Carbon's `Cpp.`, Terra's `C.`).
- Rejected: header files; public by default; bindings generated by a separate tool
  (Rust's `bindgen`, Jai).

### 10. Memory

**Proposed:**

- Code that allocates takes the allocator as an explicit parameter (decided earlier for
  the memory model, from Zig, C3): `p := alloc(a, Point);`, `free(a, p);`.
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
- Zero-initialized variables (decision 1) remove uninitialized reads, except
  `= undefined`.
- Rejected for now: a third "hardened" mode (Carbon), per-scope opt-out (Zig, Odin,
  Jai), wrapping signed overflow by default (C3, Odin, D: hides bugs).

### 12. Lexical details

**Proposed:**

- `;` ends every statement and declaration, as in C; not after a closing `}` of a
  function or type.
- Comments: `//` and `/* */`; block comments nest (from C3, Odin, Jai, Goose, Swift,
  Rust, D).
- Numbers: `0x`, `0o`, `0b`, `_` separators (`1_000_000`, from eight of thirteen); a
  leading `0` is an error (as D), not octal.
- Strings: `"…"` with C escapes; raw strings in backticks, which may span lines (from C3,
  Odin, Hare, D). `'a'` is a `u8`.
- Operators: C's `&& || !`, no `and`/`or` words.
- A small keyword set; type names (`i32`, `bool`) and built-ins (`alloc`, `import`) are
  ordinary names.
- Rejected: optional semicolons (Odin, Swift), `'` digit separators (C23, C++),
  `//`-only comments (Zig, Hare, Carbon).
