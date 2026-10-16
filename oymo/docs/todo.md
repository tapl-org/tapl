# TODO

## Now

- [ ] Review reduction_rules.md.
- [ ] Form alias, e.g. `Point = {x='i32', y='i32'}`.
- [x] Use `f` instead of `blocks`.

## Someday / maybe

- [ ] `/* */` block comment syntax.
  - [ ] Show stuck-term error messages in the block comment.
- [ ] Move oymo to its own GitHub repo. Planned: the Tenon-written oymo, after 0.15
  ([roadmap.md › Repository layout](roadmap.md#repository-layout)).
- [ ] `$fields_to_struct` argument must be
  `A = {more=[01], label=utf8, value=term, rest=A} | {more=[00]}`; no other labels allowed.
- [ ] Go back to multiple layers instead of two (term, type), if someone finds real use cases.
- [ ] BANF goes away; oymomo translates directly to LLVM IR.