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
  layer's values (`'add' {…} : g.check_add {…}`).
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
- It holds symbol entries, nested in namespaces (see Module system; this revised "flat"):
  `{lexer = {next_token = {…}}, main = {…}}`.
- No `version`: an ingot is made and translated by the same compiler. If stored text
  ever needs a version, it goes in the file header.
- No `target`: the platform reaches `clang` as `--target`, not through the ingot.
- Ingots are platform-neutral.
- Each symbol has a linkage: internal, or linked (defined here or elsewhere). Not every symbol is
  external, so private helpers of two files don't clash.
- An entry has a `type`, at most one of `body`, `init`, `value`, and an optional
  `link = 'name'` (this replaced `export`/`import`):
  - a definition with `link`: visible to the linker under that name;
  - a declaration (no body, `init` or `value`): `link` names a symbol defined elsewhere,
    and is required;
  - no `link`: internal (the default).
  The linker name is separate from the label.
- Linkage is in the term, not in meta: it changes what a program means (whether two
  files link or clash), and meta never does.
- Types are literal only. Named and opaque struct types are not needed: types don't
  reach the `.o`, and with opaque `ptr` nothing needs a recursive or opaque type.

### The `.oymo` file

- A file is a pair (layered-term, meta). A layered-term has at most two layers; with
  no layering it is a plain term.
- The calculus has no annotations: meta stays outside it.
- Meta is a database outside the calculus. It mirrors the term's nodes, so any node can
  be annotated.
- The parser builds meta; a frontend writes it. Only the translation reads it.
- The old `info` section with `spans` became the first part of meta (each term's place).
- Meta is a list of data structures (tables) that may reference each other by id.
  New kinds are added over time.
- Meta is a protobuf message, written as text format (textproto) after the `---` line.
  Later, meta may also live in a separate file, as textproto or binary.
- No version: protobuf readers skip fields they don't know, and an existing field never
  changes meaning. Skipping is safe because meta never changes what the term means.
- The bootstrap compilers ignore meta: they read the term and skip everything after
  `---`. They lose only debug info and located errors.
- No proposed target in meta: the platform comes only from the driver.
- Meta mirrors the term as a flat list, `tags`: one entry per node of the layered-term,
  in pre-order (a node, then its children; the layering node counts). Entry k holds all
  meta of node k: its place, a value range, and any field added later. No node numbers
  are written; position says which node.
- `skip: N` stands for the next N empty entries (the old `.N`).
- Meta about the whole file (module flags, the source files) sits outside `tags`.
- Not a nested tree: oymomo nests as deep as its `let` chains (a 1,000-instruction body is
  about 2,000 levels), past protobuf's default recursion limit of 100. The list holds the
  same entries; the term gives the shape.
- The schema is proto3, kept in the repository as `meta.proto`. Values are `bytes`.
- `code_md5` guards `tags`: if the code changed, `tags` is dropped with a warning.

The schema is `src/oymo/oymomo/meta.proto`. The file-level message is `Tags`:
`code_md5`, `files` (path, language, md5, lines) and `tags`, one `Tag` per term node in
pre-order. A `Tag` holds the term's place: `optional sint64 file` (unset: the parent's
place, so an empty entry; `-1`: no place; `k ≥ 0`: `files[k]`), `start` and `length` in
bytes within that file; `skip: N` for N empty entries. There is no span concept: no packed
integer, no global numbering of files, no length cap. In memory every term holds `tag: Tag`
(a frozen dataclass whose place refers to a `File` object, or `None`); copies share it.
Errors and ingot objects carry a `Tag` too. Hashes are hex strings. `range`, module flags
and ids come when first needed. Generated Python (`meta_pb2.py`, `.pyi`) is checked in;
`hatch run proto:generate` regenerates it, and a test checks it matches `meta.proto`.
(The name `Tag` was chosen over `Node`, `Gloss`, `TermMeta`; "tag" also names type tags in
field 0, so those are called type tags.)

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
- Decided: precedence of `:`; see the operators section below.

### 1b. Operators: precedence and associativity

- Idea: as in Scala, an operator's precedence comes from its first character, and its
  associativity from its last (an operator ending in `:` is right-associative).
- Decided: oymomo does not take this rule: the kernel has no user operators (a frontend
  may take it).
- Decided: `:` binds more loosely than application and projection and more tightly than
  λ, `let`, `if`: `f a : g b` is `(f a) : (g b)`, `λx. t₁ : t₂` is `λx. (t₁ : t₂)`. The
  choice changes meaning (`λx. (t₁ : t₂)` vs `(λx. t₁) : t₂` separate differently).
- Decided: `:` is non-associative; `a : b : c` is a parse error.

### 2. Module system

Written by topic; the discussion and every user quote are in `agent_wiki.md`
(`redesign-modules`). The calculus (Sections 9 and 10) is not yet updated for this.

#### Why modules

- Code that isn't oymomo (libc, C libraries) is the only reason that forces modules; a
  declaration with a `link` name and the platform linker already handle it.
- Reuse and people are the other reasons that count.

#### Units

- People split a program as in Go and Rust: a unit is several files reduced into one
  ingot and one `.ll`. Inside a unit everything is shared, files may refer to each other in
  cycles, and code may be copied.
- Between units there are only headers and the platform linker. Link-time references may
  form cycles (as C object files do); only the build order must be acyclic: a unit that
  reads another's generated header needs that unit built first, and a handwritten header
  breaks such a cycle.
- A unit has no name in oymomo: the importer picks the label when mounting a header, and
  the driver names the output files (after the root file, or a flag). Carbon needs
  package names because C++-style open namespaces collide across libraries; ours never
  cross units.
- Two dependency kinds: reduce-time (a term read and reduced into the unit) and link-time
  (declarations joined by the linker).

#### Three name realms

- File names appear only as operands of the read opcodes (and in meta), resolved by the
  driver inside a virtual directory.
- Labels and paths appear only inside a unit (`g.lexer.helper`).
- A label (and a variable's name) is any bytes but 00: a name, or quoted with LLVM's
  escapes, `\HH` and `\\` (`{"\FF\01" = x}`); `""` is the empty label, the same as no
  label. As LLVM's names: any bytes but 00 (`llvm.` and a leading 01 are left to LLVM).
- Link names appear only in `link` fields, across units.
- They are independent: renaming in one never changes meaning in another. They meet only
  in the `.ll` symbol table: internal symbols are named by their path by default, and the
  translation may choose another name (internal names carry no meaning); link names are
  emitted exactly.

#### The ingot (revises the flat ingot and `export`/`import`)

- An ingot is itself a namespace, and nests namespaces: `{lexer = {…}, parser = {…}}`.
  One shape for the ingot and every namespace in it. No tags: a struct with a `type`
  field is an entry, any other struct is a namespace, so no symbol may be named `type`
  (every entry has a `type`); an entry's other fields are among `body`, `init`, `value`,
  `link`. (The `'namespace'` tag was dropped; tagging entries was considered.)
- A namespace is just a struct reached by paths; the calculus gets nothing new.
- An entry has a `type`, at most one of `body`, `init`, `value`, and an optional
  `link = 'name'`:
  - a definition without `link` is internal (the default);
  - a definition with `link` is visible to the linker;
  - `{type, link}` declares a symbol defined elsewhere;
  - `{type}` is a hole: merge fills it with an entry of the same type that brings a body or
    a `link`; a hole still unfilled at verification is rejected. A declaration without
    `link` is rejected when the ingot is verified or translated.
- After reduction, an ingot holds only namespaces and entries; anything else is rejected
  ("reduce-time value left in the ingot").
- Link names are opaque to the unit: no unit logic reads them. The translation emits one
  `declare` or `define` per link name, as the linker would (same type, at most one
  definition, else rejected).
- Symbol addresses in data (`value = 'counter'` for a `'ptr'`, calculus 10) are dropped for
  now: a label written as bytes mixes the label realm into data and doesn't survive
  namespaces or reduction. To be redesigned; until then pointer tables are filled at run
  time.

#### Building a unit

- The root is the file the driver starts from; its result is the unit. Any file may read
  other files; the driver records the paths read.
- Driver-supplied opcodes:
  - `'driver.read_low' path`, `'driver.read_high' path`: one layer of an oymo file as a plain term, usable
    on either side (a bridge takes another file's layer this way); both layers:
    `('driver.read_low' 'c.oymo' : 'driver.read_high' 'c.oymo')`;
  - `'driver.read_bytes' path`: a raw file as a byte array (as C23 `#embed`);
  - `'driver.config'`: build flags, later platform facts (as Rust `cfg!`, Zig `builtin`).
- Separation stays before reduction (calculus 4.2), so the read opcodes return plain
  terms.
- Read paths are relative to the top of a virtual directory the driver provides (nested,
  built by the user); libraries are mounted into it, so there are no search paths. As in
  Blaze, its top is the **workspace**, the current directory where `oymo` runs: every read
  path is from there (`calc/root.oymo` reads `'driver.read_low' 'calc/lexer.oymo'`), and a
  root file outside it is an error. A folder outside the workspace is mounted with
  `--mount VPATH=DIR` (repeatable): `--mount vendor/math=../math/oymo-out` makes
  `'vendor/math/unit.h.oymo'` read `../math/oymo-out/unit.h.oymo`. A mount path may not
  clash with a project file or folder, overlap another mount, or leave the top; `DIR` must
  be a folder.
- `g` (for global) in a body is the whole unit, and the kernel uses absolute paths only
  (as C++'s compiled names are fully qualified); short names are the frontend's job. It
  was `m`, renamed because it read as "module".
- A namespace's label is declared by the file (taken from C++ namespaces: open, nested) or
  picked by the root.
- Tools, at the user's choice:
  - merge, `'unit.merge' {X₁, X₂, …}`, deep: same-labeled namespaces combine (merge recurses into
    structs without `type`), equal λ-free entries merge, a declaration `{type, link}` meets
    the definition of the same type and `link` (what the linker would join), a λ entry
    defined twice gets no step and is rejected with both places;
  - rebase, `'unit.rebase' {prefix, X}`: prefixes every `g.…` path in X's bodies and
    places X under the prefix (`g.lib.step` becomes `g.dbl.lib.step`), so two libraries with
    the same labels fit in one unit. It fires only when every body in X is closed, in
    normal form, and uses `g` only as the head of paths. Mounting a header is a
    rebase of a λ-free struct. (`'struct.check_data'`, a guard for mounting, was dropped:
    rebasing a source file is correct, so mounting one is no longer a mistake.)
  - make reducible, `'unit.make_reducible' I`: gives `t = λg. N`, each definition's own `λg`
    moved out to one shared `λg` and each region `'R' (λr. u)` turned into
    `(fix (λr. u)) [00]`; other entries stay. `fix t` runs the unit by reduction; other
    units are merged in first: `fix ('unit.make_reducible' ('unit.merge' {I, U}))`. It
    returns `t`, not `fix t`, to leave room for mocks and wrappers.
    The reducible form is for running: under reduction anywhere each `(fix R) [00]` unfolds,
    so a loop-free unit's form reduces to plain bodies, but a unit with a loop has no
    normal form (the back edge unfolds forever). A call with known arguments still reaches
    its value (`(fix t).gcd {…}` gives `[06000000]`).
- The translation adds nothing (Nov 5, a rule): every LLVM block, `br` and instruction is
  written; a jump to field 0 is rejected, so a loop head is a block of its own.
- Predefs (Nov 5): operands are `Q ::= P | b | {lᵢ = Qᵢ}`; a predef is an operand fixed
  before the program runs, its only paths symbol addresses `g.l₁⋯lₙ`. A struct operand is
  a predef, a type is a predef with no path, and an `init`/`value` is a predef with no path
  or `λg. C`, so global data can hold addresses: `value = λg. {g.hello, g.bye}` becomes
  `[2 x ptr] [ptr @hello, ptr @bye]`. Unit tools treat `λg. C` like a body.
- A region is `'R' (λr. {…})`: `'R'` is a marker opcode that no table computes, so a region
  never steps; `g` only heads paths. Effects stay ordered by their `let`s (an effect call
  never steps, so call-by-value never moves it); reduction never computes through memory.
- Delegates wire dependencies: a library declares a hole (`error = {type …}`), and the root
  fills it with `{type …, body = λg. λp. g.parser.report_error p}` (LLVM inlines it) or with
  `{type …, link = 'report_error'}`.
- Convention: a library refers only to its own labels and reaches outside through holes;
  an outside path breaks under rebase and is reported as a dangling path at verification.
- Another way out of a clash: build one library as its own unit and mount its header.
- The pattern is mixin composition, as a linker does (holes are undefined symbols, merge
  collects, `g` resolves). Related: mixin modules (Ancona and Zucca), the cake pattern
  (whose problems, init order and one wiring per program, don't apply), Nix fixed points.
- Goal: building a unit is as fast as merge (struct opcodes and the translation, no
  β-steps), and linear like a linker. Reduction stays possible: a unit can always be run
  by reduction (calculus 9). Later speed-ups, implementation only: parallel merge,
  resolving only reachable entries, caching each file's normalized form.

#### Opcodes and confluence

- E-Opcode fires on `b A`, `A ::= b | {lᵢ = Aᵢ} | λx. t (closed and normal)`, and its result
  may be any closed term (calculus 5). Data `D` (λ-free) is in the ANF grammar (8.3).
- So an operand never steps, and an opcode may move, copy, drop or read its λs (α-invariantly,
  with a fixed opcode table and a closed result): Mitschke's δ-rule condition, Barendregt
  §15.3. A λ that is not normal yet is not yet an operand; normal depends on the opcode
  table. Allowing any closed λ (moved only) was dropped: confluence held, but the
  strategy guarantee failed (a free variable erased by another step can create an
  E-Opcode redex the order does not see). Proved in Lean (`OpOK`: results closed and
  well formed; `isNF_iff`).
- The unit opcodes are proved to meet `OpOK` in Lean (`UnitOps.lean`: `'unit.merge'`,
  `'unit.rebase'`, `'unit.make_reducible'` give closed, well-formed results), and rebasing
  keeps meaning (it is substituting `g := g.P`). Shared cases keep the Lean and Python
  definitions in step: Python tests check them, and a generated `UnitOpsCases.lean` checks
  them by `rfl`.
- Paths stay non-values: after substitution a path may be a failing projection
  (`(λx. (λy. b) x.l) {}` is `b` inner-first, stuck outer-first).
- Opcode collections and their names (`'llvm.add'`, …) are roadmap node
  `opcode-namespaces`.

#### Kinds of file

- Source part: a namespace (`{lexer = {…}}`), merged or rebased.
- Header: declarations only, generated (`lexer.h.oymo`, one per unit, with a layering
  `(low : high)` for a two-layer unit) or handwritten (`libc.h.oymo`). Its meta keeps places
  into the original source. An unchanged header means its readers need no rebuild.
  - Generated by `oymo emit-header` (`header.header_of`): `{type, link}` for each linked
    definition at its path; internal symbols and the unit's own imports left out.
  - Two layers: one file `low header : high header` by default; `--merge` merges them
    (a layering only where they differ), for developers.
  - Written as `unit.h.oymo` to the destination folder, `oymo-out/` in the workspace or
    `--out DIR`. The destination folder is only written, never part of the virtual
    directory: another project uses the header by copying it in, or by mounting the
    folder (`--mount vendor/math=../math/oymo-out`).
  - Places into `language oymomo` files are still never written (see `header-places`, after
    the bootstrap).
- Reduce-time library: any term, applied or `let`-bound, never in the ingot; recursion by
  `fix (λself. …)`, mutual recursion tied by the root with `fix (λl. {a = A l, b = B l})`.
- Opcode provider (later): a compiled unit built for the host and loaded by the driver;
  its functions become opcodes (as Rust procedural macros); λs reach it as opaque handles;
  determinism and closed results are its contract.

#### Reuse between units

- Compiled only: headers hold declarations, never bodies, so nothing is copied between
  units. Inside a unit, an entry may be reused from source (`{type = …, body = …}`).
- Source sharing means merging (or rebasing) the author's files into one's own unit.
- Inlining across units comes back by LTO (`clang -flto` on the `.ll` files).
- Mangled link names may come from a frontend, never the kernel; symbols meant for C keep
  plain names; headers carry the final strings.

#### Proposals and open items

- Proposal: functor-style libraries: `λu. {…}`, bodies `λn. λp.` using their
  own namespace `n`, foreign symbols filled from `u`, wired by the root in `fix (λg. …)`
  with paths (not entries). As OCaml functors and recursive modules.
- Proposal: aliases: an entry that is a path (`log = g.util.log`) is that symbol for the
  translation; chains followed, cycles and dangling paths rejected.

### 3. Meta

- Decided: ids and references between messages come when a message first needs one
  (a place's `file` is an index into `files`, the first such reference).
- Decided: merging files. `tags` need no merge: each file's entries stay with its own
  term parts, which carry their meta through reduction. In memory a place refers to its
  `File` object, so nothing is renumbered; the writer numbers the files used. `flags` follow LLVM's rules. Every other whole-file message states its
  merge rule in `meta.proto`.
- Decided: after separation, each part in either layer keeps the entry of the part it
  came from; a layering node's own entry is dropped.
- Decided: the meta of a reduction's result. Every part carries its entry; four rules
  cover every reduction rule (E-Beta, E-Opcode, E-Proj, E-Index, E-Default, E-FixProj,
  E-FixApp) and separation:
  1. Keep: a part that survives a step keeps its entry
     (`((λx. (f x)⟨B⟩) [03]⟨N⟩)⟨R⟩ ⟶ (f [03]⟨N⟩)⟨B⟩`).
  2. Copy: a copy made by substitution, unfolding or cloning carries the entry of what it
     copies (`((λx. {x, x}⟨S⟩) [07]⟨N⟩) ⟶ {[07]⟨N⟩, [07]⟨N⟩}⟨S⟩`).
  3. New: a part a rule creates (E-Opcode's result) takes the redex's entry
     (`('add' {'i32', [02], [03]})⟨C⟩ ⟶ [05]⟨C⟩`).
  4. Drop: entries of removed parts are dropped: the redex's application or projection,
     the `λ`, the replaced variable, discarded fields, a layering node
     (`({a = [01]⟨A⟩, b = [02]⟨B⟩}⟨S⟩ .b)⟨P⟩ ⟶ [02]⟨B⟩`).
- Decided: origin meta (place, …) follows the part by rules 1–4. Value meta (range,
  non-null, …) describes the value, which reduction keeps, so it moves from the redex to
  the result; if the result has one already, both hold (for ranges, the intersection).
  Each field of `meta.proto` states its kind; origin is the default.
- Decided: no `inlined_at` for now: inlined code keeps the helper's lines. An
  `inlined_at` field pointing at the call site's entry may come later.
- Decided: these rules live in this document and in `meta.proto`, not in the calculus.

### 4. Platform-neutral ingots

- Decide later, when needed: how a size that depends on the platform (`usize`, a C
  struct's layout) stays out of the ingot until translation. Idea: symbolic types
  (`'usize'`, `'c_long'`) and opcodes reduction never folds (`'sizeof'`, `'alignof'`,
  `'offsetof'`), resolved by the translation from the data layout.

### 5. Linking across layers

- Decided: an oymo file imports only other oymo files (a layer of one), never a `.ll`.
  `.ll` files are only outputs; the driver and the platform link them.
- Decided: no rule on which `.ll` files are linked together; it is up to the user. A
  user may link both layers' `.ll` files into one program, or cross between layers with a
  bridge file (below), which lifts code (low to high) or lowers it (high to low),
  possibly relabeling symbols.
- Decided: relabeling is optional, with no rule: such a file may use the symbols as they
  are, or relabel either side (the code it carries across, or the other layer's).
  Avoiding a clash is the user's job.
- Decided: such a file is an ordinary oymo file that imports another file's layer into
  a different layer of its own. What it does with the symbols (keep, rename, pick some)
  is its own code, using the struct tools. No new calculus feature and no special file
  kind. In docs it is called a bridge file, which lifts (low to high) or lowers (high to
  low) code.
- Decided: in prose, layer 1 is the guard and layer 0 the guarded layer; a guarded layer
  is safe to run when its guard returns non-error.
- Decided: the calculus keeps `low` and `high` (where a part goes); guard and guarded
  (what it does) are a convention above the calculus. High is the guard, low the
  guarded layer.
- Decided: the build model, kept simple (user: "things get so complicated. lets simplify
  them first"):
  - One project, one unit, named `unit`. The project is the workspace; the unit's root is
    the file given to `oymo build FILE`.
  - `oymo-out/` (or `--out DIR`) is only an output, flat, with fixed names: `unit.ll` (the
    low layer, or the only one), `unit.guard.ll` (two layers), `unit.h.oymo`. Adding the
    first `:` never renames an existing output. The names live only in file names, never
    inside the `.ll`. Before a build, `unit.guard.ll` is removed, so a one-layer build
    leaves no guard behind.
  - oymo ends at the `.ll` (user: "this is clang job, right? i guess oymomo should end in
    .ll file"). Linking, other projects' code and other targets are clang's job, and
    running is the user's: `clang -Wno-override-module oymo-out/unit.ll
    ../math/oymo-out/unit.ll -o app`, `clang --target=… …`. `oymo build` needs no clang
    and runs nothing; there is no `oymo run`.
  - The `.ll` holds no `target triple` and no `target datalayout`: nothing in the
    translation depends on the platform yet, so clang fills in its target's. clang warns
    that it overrides the (empty) triple; `-Wno-override-module` silences it. Byte-array
    literals stay little-endian on every target; that fixes what a literal means, not how
    memory is laid out (LLVM lays out `i32 42` per the target). Once platform-dependent
    sizes exist (`platform-sizes`), the translation will need a data layout as input.
  - Headers of other projects are copied in or mounted (`--mount`); reading one is a plain
    file read, so there is no dependency graph.
  - This is the driver's job, not oymomo's, so "nothing automatic in oymomo" still holds.
