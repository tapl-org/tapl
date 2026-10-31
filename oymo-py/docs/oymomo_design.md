# Oymomo redesign

Oymomo is the main target. Alcor, Mizar and the rest wait until this design is done.
This document holds what is decided and what is still open. When a part is settled, it
moves into `doc/oymomo-calculus.tex`.

## Philosophy: the tower

An analogy: a CEO (L3), a VP (L2), a manager (L1) and a worker (L0). Each one may only do
what the one above allows.

```text
a.oymo   L3        one layer; guards itself at run time (Value-style)
b.oymo   L2 : L3   b's L3 part uses a, and guards b's L2 part
c.oymo   L1 : L2   c's L2 part uses b's L2 part, and guards c's L1 part
d.oymo   L0 : L1   d's L1 part uses c's L1 part, and guards d's L0 part
```

- A file has at most two layers; a tower of any height is a chain of files.
- Low and high are roles inside one file. One file's low layer can be the material
  another file's high layer is written with.
- The top of a tower is a one-layer file that guards itself.
- The guard runs first. It returns data: if the data is not an error, the lower layer is
  safe to run; if it is an error, the lower layer doesn't run. This is how the manager
  stops the worker.
- Usually the guard runs at build time, on the host, and its result decides whether the
  lower layer may run at its own run time.
- If the guard depends on a run-time value, it runs inside the program, just before the
  worker starts. This is usually done by a third file that imports the guard and the
  lower code into its own low layer and calls them one after the other.
- By convention an error is a tagged struct, such as `{'error', message, span}`.
- The guard knows what the worker will do by its shape: separation gives both layers the
  same structure and binders, so the guard runs the worker's program on the high
  layer's values (`'add' {…} : m.check_add {…}`).
- A guard is trusted because it only calls the API it imports from above, which that
  layer's own guard already cleared. The chain ends at the top, which guards itself.
  This is a best practice, not enforced by oymomo or the driver.
- So the (file, layer) graph must be acyclic, and the low ingot a guard imports is built
  for the host, where the guard runs.

## Bird view

```text
a.oymo = (layered-term, meta)
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

- A file is a pair (layered-term, meta). A layered-term has at most two layers; with
  no layering it is a plain term.
- The calculus has no annotations: meta stays outside it.
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

- Decided: layered-terms. A node may be written `t : T`; `t` is low, `T` is high.
- Decided: separate first. A syntactic step splits the file's term into a low term and a
  high term before any reduction; each reduces on its own. Reduction rules don't change.
- Decided: separation as in θ-calculus (`doc/theta-calculus.tex`, Section 5):
  - A term with no `:` is single-layer and is never separated. A file with no `:` is
    one layer.
  - A single-layer term is cloned into both layers only where it meets a multi-layer
    term (S-Clone1/2).
  - `λ` and application are pushed through `:` (S-Abs, S-Split, S-App1/2, S-Zip):
    `λx. (t₁:t₂)` → `(λx. t₁) : (λx. t₂)`; `(t₁:t₂) (t₃:t₄)` → `(t₁ t₃) : (t₂ t₄)`.
  - Added for oymomo: a struct clones its single-layer fields, then zips
    (`{a = t₁:t₂, b = t₃:t₄}` → `{a = t₁, b = t₃} : {a = t₂, b = t₄}`);
    `(t₁:t₂).l` → `t₁.l : t₂.l`; `fix (t₁:t₂)` → `fix t₁ : fix t₂`.
  - Separation ends at a single-layer term (one layer) or `t₁ : t₂` (low, high).
- Decided: in `t : T`, both sides are single-layer (no third layer).
- Decided: no unlayering (`θ.`): inside a file, a layer never reads the other.
- Decided: a cloned node keeps its meta row in both layers.
- Decided: for now, the low and high ingots may define the same symbols (cloning gives
  the high ingot low's symbols). Linking both into one program would clash; left for later.
  Known limit: the run-time guard pattern (a file that imports a guard and its lower
  code and calls them in turn) links both ingots into one program, so it hits this clash.
- Decided: the two layers are equal in oymomo; the driver picks where each runs (build
  time on the host, the target binary, or both).
- Decide: precedence of `:` (θ's: tightest); see the operators leaf below.

### 1b. Operators: precedence and associativity

- Idea: as in Scala, an operator's precedence comes from its first character, and its
  associativity from its last (an operator ending in `:` is right-associative).
- Decide: whether oymomo takes this rule, and for which operators (`:`, `.`,
  application, later sugar).

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
- Decided: output names. One layer: `a.oymo` → `a.ll`. Two layers: layer 0 keeps
  `a.ll`, so adding the first `:` never renames an existing output; layer 1 writes
  `a.guard.ll`. The names live only in file names, never inside the `.ll`.
- Decided: in prose, layer 1 is the guard and layer 0 the guarded layer; a guarded layer
  is safe to run when its guard returns non-error.
- Decided: the calculus keeps `low` and `high` (where a part goes); guard and guarded
  (what it does) are a convention above the calculus. High is the guard, low the
  guarded layer.
- Decide: how the driver builds an ingot for both host and target.
