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
- It holds symbol entries, nested in namespaces (see Module system; this revised "flat"):
  `{lexer = {'namespace', next_token = {…}}, main = {…}}`.
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
- Today's `info` section with `spans` is the first part of meta.
- Meta is a list of data structures (tables) that may reference each other by id.
  New kinds are added over time.
- Meta is a protobuf message, written as text format (textproto) after the `---` line.
  Later, meta may also live in a separate file, as textproto or binary.
- No version: protobuf readers skip fields they don't know, and an existing field never
  changes meaning. Skipping is safe because meta never changes what the term means.
- The bootstrap compilers ignore meta: they read the term and skip everything after
  `---`. They lose only debug info and located errors.
- No proposed target in meta: the platform comes only from the driver.
- Meta mirrors the term as a flat list, `nodes`: one entry per node of the layered-term,
  in pre-order (a node, then its children; the layering node counts). Entry k holds all
  meta of node k: its span, a value range, and any field added later. No node numbers
  are written; position says which node.
- `skip: N` stands for the next N entries with no meta (as today's `.N`).
- Meta about the whole file (module flags, the source files) sits outside `nodes`.
- Not a nested tree: oymomo nests as deep as its `let` chains (a 1,000-instruction body is
  about 2,000 levels), past protobuf's default recursion limit of 100. The list holds the
  same entries; the term gives the shape.
- The schema is proto3, kept in the repository as `meta.proto`. Values are `bytes`.
- `code_md5` guards `nodes`: if the code changed, `nodes` is dropped with a warning.

First sketch of the schema:

```proto
syntax = "proto3";
package oymo.meta;

message Meta {
  bytes code_md5 = 1;
  repeated File files = 2;        // source files that spans point into
  repeated Node nodes = 3;        // one per term node, in pre-order
  repeated ModuleFlag flags = 4;  // the whole module
}
message File {
  uint64 id = 1; uint64 start = 2; uint64 length = 3;
  string path = 4; string language = 5; bytes md5 = 6; repeated uint64 lines = 7;
}
message Node {
  uint64 span = 1;                // start << 16 | length; 0: the parent's
  Range range = 2;
  uint64 skip = 15;               // this and the next N-1 entries have no meta
}
message Range { bytes lo = 1; bytes hi = 2; }
message ModuleFlag {
  enum Behavior { ERROR = 0; WARNING = 1; REQUIRE = 2; OVERRIDE = 3;
                  APPEND = 4; APPEND_UNIQUE = 5; MAX = 6; MIN = 7; }
  Behavior behavior = 1; string name = 2; bytes value = 3;
}
```

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

- Decided (in Ingot): linkage is the `link` entry field, internal by default.
- Decided: the reasons that count are code that isn't oymomo (the only one that forces
  modules; already solved by declarations with `link` and the platform linker), reuse,
  and people.
- Decided: reuse is per symbol, by the fields shipped. `body` makes the source reusable,
  `link` on a definition makes a compiled symbol, and `{type, link}` alone is a header. The user
  picks per use: `{type = math.gcd.type, body = math.gcd.body}` (source, internal) or
  `{type = math.gcd.type, link = math.gcd.link}` (compiled). Withholding source is
  done by shipping only the header and the `.o`.
- Decided: people split a program as in Go and Rust. A unit is several files joined into
  one term (one namespace, cycles allowed), reduced to the unit's ingot(s); units form a
  DAG. Inside a unit everything is shared; between units the default is linking, with
  copying only where the defining author allows it.
- Decided: a unit's root is oymo code. The driver supplies two reduce-time opcodes,
  `'read_low' {path}` and `'read_high' {path}`, each returning one layer of the file as a
  plain term, usable on either side (this is how a bridge takes another file's layer).
  The projection is done by the opcode, outside the calculus. Both layers of a file:
  `let c = ('read_low' 'c.oymo' : 'read_high' 'c.oymo') in …`. No plain `'read'`:
  this layering does its job. The driver records the paths read, which gives it the
  dependency graph.
- Decided: E-Opcode fires on `b A`, `A` an opcode operand: a byte array (so
  `'read_low' 'c.oymo'`), a struct of operands, or a closed `λ` (so struct tools work on
  module entries). Its result may be any closed term. Opacity: an opcode may move, copy
  or drop a `λ`, but its result must not depend on what the `λ` contains (else it could
  tell `λx. (λy. y) x` from `λx. x`). Data `D` (`λ`-free) moves to
  the ANF grammar (8.3): it is used only there and below (ANF operands, `init`/`value`,
  types).
- Decided: separation stays before reduction (calculus 4.2). Moving it into reduction was
  considered and dropped; so the read opcodes return plain terms.
- Closed: how a copied body's dependencies come along. Code is copied only inside a unit,
  where every path is valid; between units, headers hold declarations only.
- Decided: building a unit also writes a header, `lexer.h.oymo`: a one-layer oymo file
  with `{type, link}` for each linked definition, keeping the unit's namespaces. Other units
  read it like any file; a handwritten header (`libc.h.oymo`) has the same shape. An
  unchanged header means units that read only it need no rebuild.
- Decided: a header has declarations only, never a `body`. So reuse between units is
  compiled only, and nothing is copied between units: a declaration has no `λ` and no
  `m`, so it can be mounted under any label. Inlining across units comes back by LTO
  (`clang -flto` on the `.ll` files); generic code is shared by merging the author's
  source files into one's own unit.
- Decided: a two-layer unit has one header file with a layering,
  `(low declarations : high declarations)`; `'read_low'`/`'read_high'` pick a side.
- Decided: a generated header's meta keeps spans into the original source (its `files`
  table lists the source files), so errors point at the definition, not the header.
- Decided: three name realms, independent: file names (only as operands of the read
  opcodes, resolved by the driver), labels and paths (inside a unit), link names (only in
  `link` fields, across units). They meet only in the `.ll`, where internal path names and
  link names share LLVM's symbol table (a clash there is rejected).
- Decided: the driver provides a virtual directory (nested); the user builds it and
  picks one file as the root of a unit; by default the project folder. Read paths are
  relative to the virtual directory's top; libraries are mounted into it, so no search
  paths. Decouples oymomo from the host file system. How the user describes it is left
  to the driver design.
- Decided: internal LLVM names are not meaning: by default an internal symbol is named by
  its path, and the translation may choose another (deterministically) to avoid a clash.
  Link names are emitted exactly.
- Decided: a hole is an entry with a `type` and no `body`, `init`, `value` or `link`. Merge
  fills it with an entry of the same type that brings a body (a definition) or a `link`
  (a declaration of a symbol elsewhere). A hole still unfilled at verification is
  rejected. Comparing types compares λ-free data, and a body is only moved, so opacity
  holds.
- Decided: dependencies inside a unit are wired by delegates: a library declares a hole
  (`error = {type …}`), and the root fills it, e.g. with
  `{type …, body = λm. λp. m.parser.report_error p}` (LLVM inlines it), or with
  `{type …, link = 'report_error'}`.
- Decided: a label clash between two body-carrying libraries is worked around by building
  one of them as its own unit and mounting its header under another label; inlining across
  the boundary comes back by LTO.
- Decided: a namespace is just a struct, reached by paths through a variable
  (`m.lexer.next_token`). The calculus gets nothing new.
- Decided: the ingot nests namespaces, `{lexer = {'namespace', …}, parser = {'namespace', …}}`,
  tagged `'namespace'` in field 0 as types are. Internal LLVM names are paths
  (`@"lexer.next_token"`). Inside a unit, files refer to each other only by path; between
  units only through `link` names. (Revises the flat ingot.)
- Decided, taken from C++ namespaces: each file declares its own namespace label (`lexer.oymo` is
  `{lexer = {'namespace', …}}`), and namespaces are open: the root deep-merges files with
  `'struct.concat'`. Same-labeled namespaces combine (so the `'namespace'` tag is required: it
  says where to recurse); equal λ-free entries merge (two identical `puts` declarations);
  a λ entry defined twice gets no step and the translation rejects it.
- Why C++'s model and not another:
  - Rust: the parent declares the module tree (`mod lexer;`), a file never names itself,
    and a module is closed (one file defines it). Ours: the file names itself, and
    namespaces are open.
  - Swift: no namespaces inside a module; all files of a module share one flat namespace
    (as a Go package). Ours nests.
  - Carbon: a file declares its package and library at the top (`package Foo library
    "bar";`), and `namespace N;` plus qualified declarations (`fn N.F()`) add names.
    Closest to ours; but no ADL or `using namespace` either, which we also leave out
    (short names are the frontend's).
  - From C++ we keep: the file declares its namespace, namespaces are open and nest, and
    compiled names are fully qualified. We leave out ADL and `using`.
- Decided: the kernel uses absolute paths only, from the unit's top (`m.lexer.helper`,
  as C++'s compiled names are fully qualified). Short and relative names are resolved by
  the frontend.
- Decided: `link = 'name'` replaces `export`/`import`. The entry's kind gives the
  direction: a definition with `link` is visible to the linker; a declaration's `link`
  names a symbol defined elsewhere; no `link` means internal. A declaration without
  `link` is rejected when the ingot is verified or translated. A header entry is
  `{type, link}`. (Revises the Ingot section's `export`/`import`.)
- Decided: a unit has no name in oymomo; the importer picks the label when mounting a
  header, and the driver names output files (after the root file, or a flag) (`{math = 'read_low' 'math.h.oymo'}`). Namespaces never cross units; only link
  names do. (Carbon needs packages because C++-style open namespaces collide across
  libraries.)
- Two namings: labels (inside a unit, nested paths, deep-merged) and link names (across
  units, flat strings, joined by the linker).
- Decided: in one ingot, all entries with the same link name are one symbol: same type
  (else rejected), at most one definition (else "duplicate symbol"), one `define` or
  `declare`. So `puts` declared under two labels, or declared and defined in one unit,
  works as in C. A path spelled like a link name stays an error (nothing renamed).
- Mangled linker names may come from a frontend, never the kernel: the frontend computes
  `link` strings (needing unique unit names, a frontend convention); symbols for C keep
  plain names; headers carry the final strings.
- Decided: four kinds of oymo file:
  - source part: `{lexer = {'namespace', …}}` (or `λdeps. …`), merged, becomes the ingot;
  - header: declarations only, merged (or mounted, per the decision above);
  - reduce-time library: any term (usually a struct of λs), applied or `let`-bound,
    never in the ingot; recursion by `fix (λself. …)`, mutual recursion across libraries
    tied by the root with `fix (λl. {a = A l, b = B l})`;
  - opcode provider (idea for later): a compiled unit built for the host, loaded by the
    driver, its functions become opcodes (as Rust procedural macros); λs reach it as
    opaque handles, so opacity holds by construction; determinism and closed results
    are its contract; the driver orders builds by it.
- Decided: after reduction, an ingot holds only namespaces and entries; anything else is
  rejected ("reduce-time value left in the ingot").
- Decided: the four kinds are complete. Also needed:
  - the root as a named role: the one file the driver starts from for a unit; it is
    reduce-time code that is run (not applied), and its result is the unit;
  - a driver opcode for raw data files, `'read_bytes' 'logo.png'` returning a byte array
    (as C23 `#embed`, Rust `include_bytes!`);
  - a driver opcode for driver inputs (build flags, later platform facts),
    `'driver.config'` returning a struct (as Rust `cfg!`, Zig `builtin`).
- Moved out of this redesign: opcode collections and namespaces (roadmap leaf
  `opcode-namespaces`).
- Decided: two operations, at the user's choice: merge (source parts, by their own
  labels) and mount (headers, under any label). An optional `'struct.check_data' X`
  returns `X` if it holds no λ, else has no step, so mounting a source file by mistake is
  reported at the mount. Asking whether something is a λ doesn't look inside it, so
  opacity holds. Frontends may detect mistakes earlier.
- Decided: paths stay non-values. A path is harmless only while its variable is free;
  after substitution it may be a failing projection: `(λx. (λy. b) x.l) {}` gives `b`
  inner-first but is stuck outer-first. So views that wrap bodies are dropped.
- Decided (quiz): the kernel keeps `m` = the whole unit (absolute paths). A namespace's
  label may be declared by the file or picked by the root (both allowed); a body-carrying
  file must sit where its absolute paths expect it, so a root-picked label suits headers
  and files without such paths. Merge and mount stay as tools at the user's choice.
- Proposal (functor style, kept for later): a library is `λu. {'namespace', …}`, bodies
  `λn. λp.` use only their own namespace `n`, foreign symbols are fields filled from `u`
  (`report_error = u.report_error`), and the root wires them by application inside
  `fix (λm. {lexer = lib {report_error = m.parser.report_error}, …})`. The root must pass
  paths, not entries (a copied body would rebind `n`). As OCaml functors and recursive
  modules.
- Proposal: aliases: an entry that is a path (`report_error = m.parser.report_error`)
  is read by the translation as that symbol; chains followed, cycles and dangling paths
  rejected.
- Clashes: a header is relocatable (mount it under another label); a source is not (its
  bodies hold paths), so a clash between sources is fixed by editing a label, with merge
  reporting both spans; link-name clashes are the platform linker's.

### 3. Meta

- Decided: ids and references between messages come when a message first needs one
  (none does yet; a span finds its file by its range of positions).
- Decided: merging files. `nodes` need no merge: each file's entries stay with its own
  term parts, which carry their meta through reduction. `files` are concatenated with
  positions shifted. `flags` follow LLVM's rules. Every other whole-file message states its
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
- Decided: origin meta (span, …) follows the part by rules 1–4. Value meta (range,
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
- If a high layer depends on a low layer, that low ingot is also compiled for the host.
- Decided: output names. One layer: `a.oymo` → `a.ll`. Two layers: layer 0 keeps
  `a.ll`, so adding the first `:` never renames an existing output; layer 1 writes
  `a.guard.ll`. The names live only in file names, never inside the `.ll`.
- Decided: in prose, layer 1 is the guard and layer 0 the guarded layer; a guarded layer
  is safe to run when its guard returns non-error.
- Decided: the calculus keeps `low` and `high` (where a part goes); guard and guarded
  (what it does) are a convention above the calculus. High is the guard, low the
  guarded layer.
- Decided: the driver computes which builds a (file, layer) needs from the import graph.
  Everything a guard reaches is built for the host (where the guard runs at build time);
  everything a worker reaches is built for the target; a layer reached by both is built
  for both. The ingot is platform-neutral, so there is one `.ll` and one
  `clang --target` run per platform, into separate output directories (e.g.
  `build/host/c.o`, `build/target/c.o`). This is the driver's job, not oymomo's, so
  "nothing automatic in oymomo" still holds. Example: `a.oymo` is
  `'add' {…} : c.check_add {…}`; built on x86_64 for arm64, `a.ll` goes to arm64,
  `a.guard.ll` and `c.ll` to x86_64.
- Caveat: once platform-dependent sizes exist (deferred), the host and target `.ll` of
  one layer may differ.
