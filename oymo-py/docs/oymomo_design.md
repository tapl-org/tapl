# Oymomo redesign

Oymomo is the main target. Alcor, Mizar and the rest wait until this design is done.
This document holds what is decided and what is still open. When a part is settled, it
moves into `doc/oymomo-calculus.tex`.

## Bird view

```text
a.oymo = (term, meta)
   │  reduce
   ▼
low ingot ─► low.ll ─► clang -c ─► low.o ─┐
high ingot ─► high.ll ─► clang -c ─► high.o ┤  (high is optional)
                                           ▼
                        the platform's linker joins .o files by name
```

- One `.oymo` file reduces to one ingot, or to two ingots when it has two layers.
- Each ingot becomes its own `.ll`. Oymomo stops at `.ll`; `clang` makes the `.o`.
- Linking `.o` files into an executable is the platform's job, not oymomo's.
- The `.ll` files link with each other, across files and across layers: the low or high
  layer of one file may depend on the low or high layer of another.

## Decided

### Layers

- A file has one layer or two. Two layers are supported, not required.
- No more than two.
- Inside one file, the two layers don't read each other. Across files, any layer may
  import any layer.
- The import graph has a node per (file, layer). Only that graph must be acyclic.

### Ingot

- An ingot is one compilation unit, and becomes one `.ll`.
- It is flat: only the symbol entries, `{gcd = {…}, main = {…}}`.
- No `version`: an ingot is made and translated by the same compiler. If stored text
  ever needs a version, it goes in the file header.
- No `target`: the platform reaches `clang` as `--target`, not through the ingot.
- Ingots are platform-neutral.
- Each symbol has a linkage: internal, exported or imported. Not every symbol is
  external, so private helpers of two files don't clash.
- Types are literal only. Named and opaque struct types are not needed: types don't
  reach the `.o`, and with opaque `ptr` nothing needs a recursive or opaque type.

### The `.oymo` file

- A file is a pair (term, meta).
- The term is plain λ-calculus: the calculus has no annotations.
- Meta is a database outside the calculus. It mirrors the term's nodes, so any node can
  be annotated.
- The parser builds meta; a frontend writes it. Only the translation reads it.
- Today's `info` section with `spans` is the first part of meta.

### Meta and reduction

- Meta never changes what a term means.
- Each reduction rule says what meta the result gets.
- Meta does not have to be confluent: the strategy `⟶w` fixes its value.

## Open

### 1. What is a layer?

- A. Container: the file's term reduces to `{low, high}`, two ordinary programs. The
  calculus and the Lean proofs don't change.
- B. Layered terms: every node is `t : T`, split into two programs before shaping. The
  `t~F` forms were dropped (D12) because a kept `let` lost its type after the split.
- Proposed: A in the kernel; B, if wanted, as a sugar that rewrites to A.
- Proposed: the high layer runs on the host at build time; the low layer runs on the
  target.

### 2. Module system

Why oymomo needs one at all:

- Separate compilation: reduction is slow, so a change to one file should rebuild one
  ingot, not the whole program.
- Code not written in oymomo: libc and C libraries are only reachable as declarations
  joined by the linker.
- Hiding: a file's private helpers must not clash with another file's; this needs
  linkage on each symbol (see Ingot).
- Compiled libraries: a library can ship as `.o` or `.a`, with no source.
- Sharing build-time code: many files use one high layer (types, generics) without
  copying it.
- Collaboration: people work on separate files.

Two kinds of dependency:

- Reduce-time: another file's term is substituted and reduced (inlined, instantiated).
  Today this is the glue: the driver applies files to each other, and a file never names
  another file.
- Link-time: only declarations, joined by the linker by name.

Open:

- Decide: what oymomo itself needs, beyond the glue and the linker.
- Decide: how a file names what it depends on, and in which layer.
- Decide: the words for linkage, and where they are written (entry field or meta).

### 3. Meta

- Decide: the row kinds (span, value range, aliasing, loop hints, module flags, …).
- Decide: how rows attach to nodes. Spans already use pre-order positions with `.`
  for "same as parent".
- Decide: where module-level rows go (on the root node, or a section of their own).
- Decide: the meta of a reduction's result, rule by rule (E-Beta, E-Opcode, E-Proj,
  E-Index, E-Default, E-FixProj, E-FixApp).
- Decide: inlined code: keep the helper's lines (decided for spans, no `inlined_at`), or
  record where it was inlined.
- Decide: how the meta of several files merge when their terms are combined.

### 4. Platform-neutral ingots

- Decide: how a size that depends on the platform (`usize`, a C struct's layout) stays
  out of the ingot until translation.

### 5. Linking across layers

- If a high layer depends on a low layer, that low ingot is also compiled for the host.
- Decide: how the driver builds an ingot for both host and target.
