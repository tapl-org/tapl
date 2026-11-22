<!--
Part of the TAPL project, under the Apache License v2.0 with LLVM
Exceptions. See /LICENSE for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

# arXiv submissions

Two preprints, posted to establish authorship. They are not peer reviewed.

| Paper | Source | Upload |
|---|---|---|
| The θ-Calculus | [`../theta-calculus.tex`](../theta-calculus.tex) | `build/theta-calculus.tar.gz` |
| The Oymomo Calculus | [`oymomo-calculus.tex`](oymomo-calculus.tex) (arXiv edition) | `build/oymomo-calculus.tar.gz` |

The oymomo paper's arXiv edition is a copy of `doc/oymomo-calculus.tex`, kept here
so the original stays as it is. The copy adds an abstract, a subtitle, citations,
a Related Work section and a bibliography, and renames one duplicate label. The
calculus itself is unchanged. If `doc/oymomo-calculus.tex` changes before you
submit, carry the change into the copy.

## Build

```bash
make -C doc/arxiv
```

This compiles each paper twice with `pdflatex`, fails if a reference or citation
is undefined, and packs the `.tex` into `build/<paper>.tar.gz`. The PDFs in
`build/<paper>/` are for checking only: arXiv compiles the source itself.

## Before you submit

- [ ] Read the oymomo **abstract** and **Related Work** (Section 11). Claude drafted
      them, and you are the one who knows the claims are right.
- [ ] Check each new citation in the oymomo bibliography against the original
      (authors, venue, year).
- [ ] **Proofs link.** `\bibitem{oymoproofs}` points to
      `tapl-org/tapl/tree/main/oymo-py/proofs`. Make sure that link is public
      and that `lake build` passes at that commit. Better still, archive the proofs
      on Zenodo or Software Heritage and cite the DOI or SWHID, which never breaks.
- [ ] **Theta date and subtitle.** The theta paper still reads "Draft — Work in
      Progress, February 2026". That is fine for a preprint; change it if you want.
- [ ] Once the θ paper has an arXiv ID, add it to `\bibitem{bazar2026theta}` in
      the oymomo paper (`arXiv:YYMM.NNNNN`) and submit oymomo after it.

## arXiv form

For both papers:

- **Primary category:** cs.PL (Programming Languages)
- **Cross-list:** cs.LO (Logic in Computer Science)
- **License:** CC BY 4.0. Anyone may reuse the paper, but they must credit you.
- **ACM class:** F.3.2; D.3.1 (semantics; formal definitions and theory)
- **Endorsement:** a first-time cs.PL submitter may be asked for one. arXiv then
  gives you a code to send to someone who has posted in cs.PL.

### θ-calculus

- **Title:** The θ-Calculus: Unifying Type Systems through Layered Computation
- **Comments:** 12 pages. Preprint, not peer reviewed.
- **Abstract:**

  > We present the θ-calculus, an extension of the λ-calculus with two
  > operations, layering (t:t) and unlayering (θ.t), that provides a unified
  > mechanism for expressing the full spectrum of type system features. We
  > define the syntax, term classification, evaluation semantics, and separation
  > operation, then show that Simply Typed Lambda Calculus, System F
  > polymorphism, and dependent types all arise as configurations of the same
  > mechanism, differing only in the choice of guard combinator.

### Oymomo calculus

- **Title:** The Oymomo Calculus: A Layered, Confluent λ-Calculus that Translates to SSA
- **Comments:** 19 pages. Preprint, not peer reviewed. Lean 4 proofs at
  https://github.com/tapl-org/tapl/tree/main/oymo-py/proofs
- **Abstract:**

  > Oymomo is a small untyped λ-calculus meant as a compiler's intermediate
  > language that translates directly to SSA form. To variables, abstraction
  > and application it adds ordered structs with projection and indexing, byte
  > arrays that name opcodes, and a fixed point; its β rule is call-by-value. A
  > program may have two layers, low and high, written with a layering t1 : t2
  > and separated before any reduction, so one source gives two programs that
  > reduce independently. Reduction may fire anywhere, under a λ and in every
  > arm of a branch. It is confluent for every opcode table, and a deterministic
  > strategy is sound, complete, and reaches the normal form whenever one
  > exists. A-normal form needs no lifting rule: every term in ANF is already a
  > normal form. A function body is a region of labeled blocks that end in
  > returns, jumps, branches or nested regions. Modules, called ingots, are
  > structs of typed entries with explicit linkage, and each ingot translates to
  > one LLVM module. Confluence, the strategy's soundness, completeness and
  > guarantee, and the normality of ANF are proved in Lean 4.

## θ-calculus: related work to consider

Section 8 already covers the lambda cube and PTS, the Calculus of Constructions,
staging, two-level type theory and Layered Modal Type Theory. Readers may also
expect these, since they also make types and terms one language:

- **Type:Type.** L. Cardelli, *A polymorphic λ-calculus with Type:Type*, DEC SRC
  Research Report 10, 1986. Compare it with how layers avoid (or don't avoid)
  Girard's paradox.
- **Pure Subtype Systems.** D. Hutchins, POPL 2010. Types are terms, and
  subtyping replaces typing.
- **Levels in one language.** T. Sheard, *Languages of the future* (Ωmega),
  OOPSLA Companion 2004. Values, types and kinds as levels of one language.

## After arXiv

- Upload the same PDFs to **Zenodo** for a DOI, and link your **ORCID iD**.
- When oymo-py moves to its own repository, connect it to Zenodo so that each
  release, proofs included, gets a DOI.
