# LLVM LangRef coverage

Every construct in LLVM's Language Reference Manual (LLVM 21): how oymomo writes it (with
its point in `doc/oymomo-calculus.tex`), which leaf in [roadmap.md](roadmap.md) owns it
(`ll-bootstrap` before the bootstrap, `ll-coverage` after it), or `not planned`.

## 1. Module level and symbols

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| `target datalayout`, `target triple` | — (`clang` supplies the target's) | not planned |
| `source_filename` | from meta (`Tags.files`) | `ll-instr-metadata` |
| `module asm` | *to decide* | `ll-module-level` |
| `define` | `{type = {'function', params, t}, body = λg. λp. R}`, optional `link = b` (9.4, 10.10) | done |
| `declare` (function or global) | `{type = …, link = b}` (9.4, 10.10) | done |
| `global`, `constant` | `{type = t, init = …}`, `{type = t, value = …}` (9.4, 9.7, 10.10) | done |
| External vs `internal` linkage | `link = b` vs no `link` (9.5, 10.10) | done |
| Other linkages (`private`, `weak`, `linkonce_odr`, `extern_weak`, `common`, `appending`, …), visibility (`default`, `hidden`, `protected`), `dso_local`, `unnamed_addr`, `local_unnamed_addr`, `section`, `comdat`, `externally_initialized` | in the entry slot (`attr-slots`) | `ll-symbol-fields` |
| Global `align` | in the entry slot (`attr-slots`) | `ll-symbol-fields` |
| `thread_local` (`localdynamic`, `initialexec`, `localexec`, general-dynamic) | in the entry slot (`attr-slots`) | `ll-tls` |
| Calling conventions (`ccc`, `fastcc`, `coldcc`, `tailcc`, …) | `cc` slot in the function type (`attr-slots`) | `ll-function-attrs` |
| `noalias` on parameter or result | in the parameter and result slot (`attr-slots`) | `noalias` |
| `zeroext`, `signext` | in the parameter and result slot | `attr-slots` |
| Other parameter and result attributes (`noundef`, `nonnull`, `dereferenceable(n)`, `captures(none)`, `readonly`, `returned`, `byval`, `sret`, `range(…)`, …) | in the parameter and result slot (`attr-slots`) | `ll-function-attrs` |
| `sanitize_address` | in the entry slot | `attr-slots` |
| Other function attributes (`nounwind`, `noreturn`, `noinline`, `alwaysinline`, `cold`, `willreturn`, `memory(…)`, `uwtable`, …), `prefix`, `prologue` | in the entry slot (`attr-slots`) | `ll-function-attrs` |
| Variable arguments (`...`), in definitions and in calls | — (9.4c) | not planned |
| `alias` (`@a = alias …`) | *to decide* | `ll-module-level` |
| `@llvm.used`, `@llvm.compiler.used`, `@llvm.global_ctors`, `@llvm.global_dtors` | globals with `appending` linkage (entry slot) | `ll-symbol-fields` |
| `ifunc`, `dllimport`, `dllexport`, `gc`, `personality`, target string attributes (`"target-cpu"`, `"target-features"`), `uselistorder` | — | not planned |

## 2. Types

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| `void` | `'void'` as a function's result type; its one value is `[]` (10.2d, 10.4) | done |
| Function type `t (t0, …)` | `{'function', {x_i = t_i}, t}` in an entry's `type` (9.4, 10.2h) | done |
| `i1`, `i8`, `i16`, `i32`, `i64` | `'i1'`, `'i8'`, `'i16'`, `'i32'`, `'i64'` (10.2a) | done |
| Other `iN` (`i128`, …) | `'iN'` (10.2a; folding in `wide-ints`) | `wide-ints` |
| `half`, `bfloat`, `float`, `double`, `fp128`, `x86_fp80`, `ppc_fp128` | `'half'`, `'bfloat'`, `'float'`, `'double'`, `'fp128'`, `'x86_fp80'`, `'ppc_fp128'` (10.2c) | `float-forms` |
| `ptr` (address space `0`) | `'ptr'` (10.2b) | done |
| `ptr addrspace(n)` (non-zero `n`, and global `addrspace`) | — | not planned |
| Fixed vector `<n x t>` | `{'vector', n, t}` (10.2f; opcodes in `ll-vectors`) | `ll-vectors` |
| Scalable vector `<vscale x n x t>` | — | not planned |
| Array `[n x t]` | `{'array', n, t}` (10.2f) | done |
| Struct `{t0, …}`, packed `<{t0, …}>` | `{l_i = t_i}`, `{'packed', t0, …}` (10.2e, 10.2g) | done |
| Named and opaque struct types (`%T = type …`) | — | not planned |
| `label` | region blocks `r.l` (8.3); first-class `label` values not planned | done / not planned |
| `metadata` | emitted from `meta.proto`, never a value type | `line-tables`, `ll-debug-info`, `ll-instr-metadata` |
| `token`, `target("…")`, `x86_amx`, 8-bit FP types | — | not planned |

## 3. Constants and constant expressions

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| Integer constants (`true`, `false`, `42`) | byte arrays `b`, little-endian, typed by use or byte length (10.3) | done |
| Floating-point constants | byte arrays `b`, IEEE 754 bits little-endian (10.3g) | `float-forms` |
| `null` pointer | `{}` at `'ptr'`, and `''` in `init` or `value` (10.11a, 10.11c); `'null' {}` open in `ptr-compare` | done (`ptr-compare` for `'null' {}`) |
| Struct, array and vector constants, `c"…"`, `zeroinitializer` | predefs `{l_i = Q_i}`, byte array for `{'array', n, 'i8'}` in `init`/`value`, `{}` (10.7, 10.11) | done |
| Global and function addresses `@name` | path `g.l_1.….l_n`, under `λg` in `init` or `value` (8.4c, 9.7, 10.11a) | done |
| `poison`, `undef` | *spelling in `opcode-options`* | `ll-module-level` (initializers), `ll-poison` (bodies) |
| Size, offset and alignment `getelementptr` / `ptrtoint` on `null` | `'layout.size' {t}`, `'layout.offset' {t, i}`, `'layout.align' {t}` (10.5) | done |
| Initializer constant expressions (`getelementptr`, `ptrtoint`, address difference) | *to decide* | `ll-module-level` |
| `blockaddress`, `dso_local_equivalent`, `no_cfi`, `ptrauth`, `none` (`token`) | — | not planned |

## 4. Terminator instructions

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| `ret t v` | return terminal `Q` (8.3e, 10.8c) | done |
| `ret void` | `[]`, written as such, returned from a `'void'` function (10.4a) | done |
| `br label %b` | jump `r.l Q_1 … Q_n` (8.3d, 10.8c) | done |
| `br i1 c, label %t, label %f` | two-arm branch `{J_0, J_1} P` on an `'i1'` (`if P then J_1 else J_0`, 10.8d) | done |
| `switch iN c, label %d […]`, cases `0` to `k-2` | branch `{J_i} P` (10.8d) | done |
| `switch` with any other case values | *to decide* | `sparse-switch` |
| `unreachable` | `'unreachable' {}` (*exact form to decide*) | `undefined` |
| `invoke`, `resume` | — | not planned |
| `indirectbr`, `callbr`, `catchswitch`, `catchret`, `cleanupret` | — | not planned |

## 5. Unary, binary, vector, aggregate, memory, conversion and other instructions

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| `add`, `sub`, `mul`, `udiv`, `sdiv`, `urem`, `srem`, `shl`, `lshr`, `ashr`, `and`, `or`, `xor` | `'add' {t, a, b}`, … (5.4; `'i1'`/`'i8'`/`'i16'`/`'i32'`/`'i64'` done) | done (`wide-ints`, `ll-vectors`) |
| Poison flags (`nsw`, `nuw`, `exact`, `disjoint`, `nneg`, `samesign`) | passed as `opcode-options` decides | `ll-poison` |
| `fneg`, `fadd`, `fsub`, `fmul`, `fdiv`, `frem` | `'fneg' {t, value}`, `'fadd' {t, a, b}`, … | `float-arith` |
| Fast-math flags (`nnan`, `ninf`, `nsz`, `arcp`, `contract`, `afn`, `reassoc`, `fast`) | — | not planned |
| `extractelement`, `insertelement`, `shufflevector` | `'extractelement'`, `'insertelement'`, `'shufflevector'` | `ll-vectors` |
| `extractvalue`, `insertvalue` | `'extractvalue' {t, a, i, …}`, `'insertvalue' {t, a, v, i, …}` (8.9) | done |
| `alloca` | `'alloca' {t}`, `'alloca' {t, count}` (optional `align` in `opcode-options`) | done (`opcode-options`) |
| `load`, `store` | `'load' {t, ptr}`, `'store' {t, value, ptr}` (5.4d, 5.4e) | done (`opcode-options`, `ll-volatile-asm`, `ll-atomics`) |
| `getelementptr` | `'getelementptr' {t, ptr, i_0, …}`; `inbounds`, `nuw`, `nusw` in `ll-instructions` | done (`ll-instructions`) |
| `fence`, `cmpxchg`, `atomicrmw` | `'fence'`, `'cmpxchg'`, `'atomicrmw'` (*field shapes to decide*) | `ll-atomics` |
| `trunc`, `zext`, `sext` | `'trunc' {t, value, to}`, `'zext' {t, value, to}`, `'sext' {t, value, to}` | done (`wide-ints`, `ll-vectors`) |
| `fptrunc`, `fpext`, `fptoui`, `fptosi`, `uitofp`, `sitofp`, `bitcast` | `'fpext' {t, value, to}`, …, `'bitcast' {t, value, to}` | `float-convert` |
| `ptrtoint`, `inttoptr` | `'ptrtoint' {'ptr', p, t}`, `'inttoptr' {t, n, 'ptr'}` | `ptr-casts` |
| `addrspacecast` | — | not planned |
| `icmp` | `'icmp' {pred, t, a, b}` (integers done; `'ptr'` in `ptr-compare`, vectors in `ll-vectors`) | done (`ptr-compare`, `ll-vectors`) |
| `fcmp` | *shape in `opcode-options`* (`fcmp false` and `fcmp true` not planned) | `float-compare` |
| `phi` | block parameters `λx_1. … λx_n. E` (10.6, 10.8e) | done |
| `select` | `'select' {t, c, a, b}` | `ll-instructions` |
| `freeze` | `'freeze'` | `ll-poison` |
| `call` (direct) | `g.l {x_i = Q_i}` (8.8, 10.4b, 10.8b); `musttail` in `ll-tail-calls`; `tail` / `notail` as meta hints in `ll-instr-metadata` | done (`ll-tail-calls`, `ll-instr-metadata`) |
| `call` (indirect through `'ptr'`) | *to decide* | `fn-address` |
| `landingpad` | — | not planned |
| `va_arg`, `catchpad`, `cleanuppad`, operand bundles (`[ "bundle"(…) ]`) | — | not planned |

## 6. Intrinsics and inline assembly

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| Any intrinsic `@llvm.*` with supported types | declaration `{type = {'function', …}, link = 'llvm.…'}` called via `g` (9.5) | done |
| `llvm.memcpy`, `llvm.memmove`, `llvm.memset` | `'memcpy' {dst, src, len}`, `'memmove' {dst, src, len}`, `'memset' {dst, byte, len}` | `bulk-memory` |
| `llvm.bswap` | `'bswap' {t, x}` | `bswap` |
| Exact FP intrinsics (`sqrt`, `fabs`, `floor`, `ceil`, `round`, `roundeven`, `trunc`, `copysign`, `minnum`, `maxnum`, `minimum`, `maximum`, `fma`) | `'sqrt' {t, value}`, … (transcendentals are `libm` declarations) | `float-intrinsics` |
| Integer, bit and hint intrinsics (`ctpop`, `ctlz`, `cttz`, `bitreverse`, `fshl`, `fshr`, `abs`, `smin`, `smax`, `umin`, `umax`, `*.with.overflow`, `*.sat`, `assume`, `expect`, `lifetime.start`/`end`, `trap`, `stacksave`/`stackrestore`, `returnaddress`, `prefetch`) | *opcode vs declaration to decide* (`fptosi.sat`, `fptoui.sat` in `float-convert`) | `ll-intrinsics` |
| Inline `asm` | `'asm'` | `ll-volatile-asm` |
| Variable-argument (`llvm.va_*`), constrained FP (`llvm.experimental.constrained.*`), coroutine (`llvm.coro.*`), GC (`llvm.gcroot`, `llvm.experimental.gc.statepoint`), convergence, ObjC ARC intrinsics | — | not planned |

## 7. Metadata and debug info

| LLVM construct | Oymomo spelling | Status / leaf |
|---|---|---|
| `DICompileUnit`, `DIFile`, `DISubprogram`, `DILexicalBlockFile`, `!DILocation`, `!llvm.dbg.cu` | `File` and `Tag` places in `meta.proto` (`-g`) | `line-tables` |
| `DILocalVariable`, `DIBasicType`, `DIDerivedType`, `DICompositeType`, `#dbg_declare`, `#dbg_value` | `meta.proto` DWARF fields | `ll-debug-info` |
| `!alias.scope`, `!noalias` | `meta.proto` scoped-aliasing fields | `alias-scopes` |
| `!range`, `!nonnull`, `!noundef`, `!tbaa`, `!prof`, `!llvm.loop`, `!invariant.load`, `!llvm.module.flags` | `Tag` and `Tags` fields in `meta.proto` | `ll-instr-metadata` |
