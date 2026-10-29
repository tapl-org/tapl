# Alcor sugar syntax

Sugar is defined by rewriting into the kernel ([alcor_kernel_syntax.md](alcor_kernel_syntax.md)).
It waits until the kernel is complete: nothing here is in use now. These are the sugar
decisions and ideas collected so far, to pick up then.

## Rules

- Every piece of sugar rewrites into kernel syntax, without needing types (decision 3 of
  the kernel: no implicit conversions, so no type-directed rewriting).
- Whatever sugar can write, the kernel can write too, just maybe more verbosely: sugar
  adds no power, only shorter forms (a rule of the kernel doc).

## Collected (decided earlier, on hold)

- Short forms of kernel types (the symbols most surveyed languages share; all prefix):

  | Sugar | Kernel |
  |---|---|
  | `*T` | `Ptr(T)` |
  | `[*]T` | `Many(T)` |
  | `[]T` | `Slice(T)` |
  | `[N]T` | `Array(T, ^N)` |
  | `T?` | `Option(T)` |
  | `T -> R` | `Fn(T, R)` |
  | `(A, B)` | a struct type with positional fields |

- `c"hi"` for the C string `"hi\0".ptr` (from Rust).
- `let q, r = f();` takes a tuple or struct apart into variables, with no parentheses
  (from Go, Zig).
- `p.len()` means `len(p)`, and `p.add(q)` means `add(p, q)` (UFCS; extension functions
  in Kotlin, Scala, Swift; D, Goose, Cpp2). With no overloading, two types each needing a
  `write` need a receiver namespace, such as `fn File.write` (roadmap `interfaces`).

## Open

- Indentation syntax (blocks by indentation instead of braces), as sugar over the
  kernel's braces.
- How `T?` combines with prefix sugar: `*u8?` as `Option(Ptr(u8))` (`?` applies to the
  whole type to its left), or Zig's prefix `?*u8`.

## Dropped

- `type Name = T` for `let Name = Named("module.Name", T)`.
- Lossless widening (from Zig, Java, C3, D): it would need types to rewrite.
