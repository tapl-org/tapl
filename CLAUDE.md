# CLAUDE.md

Guidance for Claude Code in this repository. It is a monorepo of several independent
language projects; each Python project has its own `pyproject.toml` and its own hatch
environment, so run commands from inside that project's folder.

## Projects

| Folder | What it is | Status |
|---|---|---|
| `oymo-py/` | **Oymo**: the oymomo language and its compiler to LLVM IR (Python, llvmlite), with Lean proofs | **active**: almost every recent commit |
| `oymo/` | future home of Oymo after the bootstrap; holds only `README.md` | don't put work here yet |
| `python/tapl-lang/` | **TAPL**: typed Python-like language compiled to Python (the published `tapl-lang` package) | stable; has its own `CLAUDE.md` |
| `gap/` | Gap: a partial evaluator between a frontend and SSA (`spec.md` is the spec) | dormant |
| `llvm/` | early C++/Bazel experiment (`chunk`, `syntax`) | dormant |
| `doc/` | LaTeX papers: `theta-calculus.tex` (TAPL), `oymomo-calculus.tex` (Oymo) | built by `make -C doc` |
| `docs/` | Jekyll site for tapl-lang.org; CI (`.github/workflows/pages.yml`) builds `doc/*.pdf` into it on push to `main` | |
| `.draft/` | scratch sketches | ignore |

## oymo-py (the active project)

**Before any work in `oymo-py/`, read `oymo-py/AGENTS.md` and follow what it says.** It
leads to the agent's rules for this project: the user's standing orders, which files the
agent must not edit, how docs and the roadmap are laid out, and how to ask questions
(multiple-choice quizzes). Those rules take precedence over this file. One of them: no
file other than `oymo-py/AGENTS.md` may link to the agent's knowledge base, so don't add
such a link here or anywhere else.

### Commands (from `oymo-py/`)

```bash
hatch run full-check      # hatch check --fix, then hatch test: the pre-commit check
hatch check --fix         # ruff lint + ruff format + Pyrefly type check (not mypy)
hatch test                # all tests (~1000, a few seconds)
hatch test tests/oymomo/strategy_test.py::test_name   # one test
hatch run python -m oymo.cli normal FILE.oymo   # also: build, check, fmt, emit-llvm, emit-header
cd proofs && lake build Oymomo                  # Lean proofs (toolchain in proofs/lean-toolchain)
hatch run proto:generate                        # regenerate meta_pb2.py(i) from meta.proto
```

Python ≥ 3.12. Ruff: line length 120, single quotes. Test files are `*_test.py`. `clang`
is needed only for the tests that link and run the generated `.ll`.

### Pipeline

Oymomo is a small untyped λ-calculus (`λx. t | t t | b | {lᵢ = tᵢ} | t.l | fix t`, byte
arrays `b`, opcodes applied to structs) whose normal forms are lowered one-to-one to LLVM
IR. Everything is in `src/oymo/oymomo/`; each module has a same-named test in
`tests/oymomo/`.

```
.oymo file ─source.read (grammar.parse; meta/tags)→ term
  ─layers.separate→ low and high layers (if the program has a layering `low : high`)
  ─reduction.resolve→ de Bruijn indices ─strategy.normalize→ normal form
  ─ingot.read_ingot (anf checks)→ Ingot ─llvm_translate (+ llvm_opcodes)→ LLVM IR (.ll)
```

| Module | Role |
|---|---|
| `terms.py` | term dataclasses; `core/syntax.py` has the base `Term`, `Layers`, `LayerSeparator` |
| `source.py`, `grammar.py`, `rule_names.py`, `printer.py` | file format (`language oymomo`, code, optional `---` meta section), PEG parser (on `core/peg.py`, `core/terminals.py`), printer that round-trips |
| `meta.py`, `meta.proto`, `meta_pb2.py*` | `Tag`: a node's source place, carried through reduction; `meta_pb2*` is generated, don't edit |
| `layers.py` | separate a layered program into two layers, and `merge` them back |
| `reduction.py`, `strategy.py` | computation rules at the root, values, stuck parts; `sstep`/`normalize` follow Lean's `Oymomo.SStep` |
| `opcodes.py`, `unit_ops.py`, `driver.py` | opcode table (LLVM ops, constant folding); `unit.*` tools that build a unit's namespace; `driver.*` opcodes that read files/config during a build session |
| `anf.py`, `ingot.py` | the ANF body grammar; reading a normal form as an `Ingot` (namespaces of entries: definitions, globals, constants, declarations) |
| `llvm_translate.py`, `llvm_opcodes.py` | ingot → llvmlite module; LLVM types come from use sites |
| `header.py`, `build.py` | a unit's header `unit.h.oymo`; `oymo build` outputs (`oymo-out/unit.ll`, `unit.guard.ll`) |
| `../cli.py` | the `oymo` command |

`proofs/Oymomo/*.lean` mirrors the calculus (syntax, substitution, reduction, confluence,
strategy, ANF, unit ops). Python docstrings name the Lean theorems they follow; keep the
two in step when changing the rules.

### Tests and goldens

- `tests/golden_test.py` (approvaltests): each `tests/goldens/NAME.oymo` has an expected
  `NAME.ll`, and `NAME.normal.oymo` only when the normal form differs from the source.
  Folders such as `diamond/`, `say/`, `unit/`, `template/` are multi-file units with a
  `root.oymo`. A changed output is written as `*.received`; approve it by renaming it over
  the expected file (after checking the diff).
- `tests/oymomo/strategy_test.py` includes a randomized check that the strategy agrees
  with every reduction order.

### Conventions

- Code (`src/`, `tests/`, `proofs/`) never refers to `doc/oymomo-calculus.tex` or to its
  section, rule-table or decision numbers; say what is meant (a rule name like E-Beta is
  fine). The doc may name Lean theorems.
- Every source file uses the extension `.oymo`, for every language (oymomo, Alcor,
  Mizar); its first line `language <name>` says which.
- Nothing in oymomo is automatic; before 1.0 the syntax, API and CLI may change freely.
- Don't edit `oymo-py/README.md` or `oymo-py/docs/story.md`. Edit
  `doc/oymomo-calculus.tex` only as the user directs.
- Design docs live in `oymo-py/docs/`: `roadmap.md` (tree of leaves with short ids),
  `oymomo_design.md`, `ll_coverage.md`, `alcor_*.md` (Alcor, the next language).
- Commit messages: `area: lowercase summary`, e.g. `oymomo: …` (code), `calculus: …`
  (`doc/oymomo-calculus.tex`), `docs: …`. Language changes usually land as a `calculus:`
  commit followed by an `oymomo:` commit.

## python/tapl-lang

See `python/tapl-lang/CLAUDE.md`. In short: `hatch run full-check` (mypy via
`hatch run types:check`, `hatch fmt`, `hatch test`); Python ≥ 3.9 with no runtime
dependencies; `.tapl` compiles into an evaluate layer `name.py` and a typecheck layer
`name1.py`; goldens in `tests/tapl_lang/pythonlike/goldens/`.

## gap, llvm, doc

- `gap/`: `hatch run full-check`, `hatch test`, same layout as oymo-py.
- `llvm/`: Bazel (`bazel test //src:chunk_test`); setup in `llvm/setup.md`.
- `doc/`: `make -C doc` builds both papers with two `pdflatex` passes; PDFs are git-ignored.

Hand-written source files carry the header
`SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception` (generated files don't).
