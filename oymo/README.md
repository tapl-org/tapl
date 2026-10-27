# Oymo

Oymo: oymomo, Alcor, Mizar and their toolchain.

This folder is self-contained: nothing in it refers to a path outside it. It is empty
for now. Until the bootstrap, the compiler and all its work live in `../oymo-py/`; when
the bootstrap starts, files move or are copied here.

```
oymo/
  LICENSE
  README.md
  lib/              the standard library
  tests/goldens/    `.oymo` programs and their expected output
```
