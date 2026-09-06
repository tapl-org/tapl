# Gap

A partial evaluator between a frontend and SSA. `spec.md` is the language spec;
the implementation under `src/gap` follows it.

```text
frontend → Gap → residual → SSA/LLVM IR → machine code
```

| Module | Role |
|---|---|
| `term.py` | AST, de Bruijn shift and substitution |
| `reader.py` | text → term, with the parse-time checks of the spec |
| `printer.py` | term → text, in the syntax the reader accepts |
| `reducer.py` | partial evaluation; what cannot reduce is the residual |

Tests live in `tests/`, one `*_test.py` per module.

```bash
hatch run full-check          # checks and tests, the pre-commit check
hatch check --fix             # lint, format, and type check
hatch test                    # all tests
hatch test tests/reader_test.py::test_read_bits   # a single test
```
