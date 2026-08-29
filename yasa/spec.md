# Yasa

A formally verifiable programming language based on lambda calculus. Source programs are reduced with lambda-calculus techniques, then whatever remains is compiled to machine code from its shape.

The name *yasa* comes from the idea that a programming language is a forming a sentence (gap yasamoq).

## Goals

- Formally verifiable
- Compilable to machine code from the residual term's structure
- Strong reduction (full support)

## Compilation pipeline

1. Write a program in lambda calculus.
2. Partially evaluate it with reductions (`β`, `η`, `θ`, …).
3. Translate the residual term to SSA, driven by the term's shape/structure.
4. Lower SSA to machine code through one of several backends:
   - MLIR
   - Cranelift
   - QBE
   - C
   - others

## Design notes

### Concise residuals after β-reduction

Partial beta-reduction feature: After β-reduction, keep applications rather than fully substituting everywhere. Apply a value only at the occurrences that need it; other occurrences of the same variable stay as a variable under application.

### Memory / store types

Lambda parameters may be annotated with a store type. When generating machine code, introduce memory as needed and drop the memory parameter from the residual.

## Syntax

| Form | Notes |
| --- | --- |
| Variable | |
| Function / abstraction | Parameter may have a store-type annotation |
| Call / application | `let` is syntax sugar |
| Record | |
| Variant | |
| Data / bits | With a store type |
| `!` (fix) | Fixes a record: `!A.label = (A !A).label` |

S-expression syntax is planned and should be configurable (e.g. show de Bruijn indices, show store types).

## Examples

### Factorial

```
F = \E. {fact=\n. if n = 1 then 1 else n * E.fact(n-1)}

!F.fact 2
= (\n. if n = 1 then 1 else n * !F.fact(n-1)) 2
= 2 * !F.fact(1)
= 2 * (\n. if n = 1 then 1 else n * !F.fact(n-1))(1)
= 2 * 1
= 2
```

### Mutual recursion (even / odd)

```
P = \E. {
    even = \n. if n = 0 then false else E.odd(n-1),
    odd  = \n. if n = 0 then true  else E.even(n-1)
}

!P.even 2
= (\n. if n = 0 then false else !P.odd(n-1)) 2
= if 2 = 0 then false else !P.odd(2-1)
= !P.odd(1)
= (\n. if n = 0 then true else !P.even(n-1)) 1
= !P.even(0)
= (\n. if n = 0 then false else !P.odd(n-1)) 0
= !P.odd(0)
= (\n. if n = 0 then true else !P.even(n-1)) 0
= true
```

## Open work

- [ ] Design terms
- [ ] Design S-expression syntax (configurable: show de Bruijn, show store type)
- [ ] Design evaluation
- [ ] Implement how to store-type the lambda
- [ ] Design how to introduce memory, and remove the memory parameter when generating machine code
