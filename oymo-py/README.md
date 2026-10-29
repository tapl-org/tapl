# Oymo

Oymo is another codename for Tapl. It has a separate name because it uses an LLVM backend, while Tapl uses CPython.

```bash
hatch run full-check          # checks and tests, the pre-commit check
hatch check --fix             # lint, format, and type check
hatch test                    # all tests
hatch test tests/hello_test.py::test_hello_default   # a single test
```
