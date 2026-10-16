# Plans

- A plan is one design change, done in steps of one commit each.
- **Open** until every step is done; then **closed**: status **implemented**, moved to
  [implemented/](implemented/).
- Order of work (releases): [roadmap.md](roadmap.md).

## Open

| Plan | Status | What |
|---|---|---|
| [plan_tenon.md](plan_tenon.md) | proposed · 0/7 phases | Tenon: two-layer language on oymomo (layer 0 runs, layer 1 type-checks at compile time); uses plan_c_interop for C |
| [plan_bootstrap.md](plan_bootstrap.md) | proposed · 0/5 steps | 0.15 seed as two oymomo files (core + Tenon frontend) instead of one `.ll` |
| [plan_c_interop.md](plan_c_interop.md) | proposed · 0/6 phases | oymomo and C call each other as if both were C: same ABI, headers both ways, no glue |
| [plan_confluence.md](plan_confluence.md) | proposed · 0/4 steps | Reduction order doesn't change the result; full-β reference reducer as a test |
| [plan_metadata.md](plan_metadata.md) | proposed · 0/6 steps | LLVM metadata: a table after the code, `e !dbg !4` attachments |
| [plan_memory_advanced.md](plan_memory_advanced.md) | proposed · 0/7 steps | Pointer compare, null, int casts, `memcpy`, `align`, `noalias`, `bswap` |
| [plan_floats.md](plan_floats.md) | proposed · 0/5 steps | `'f32'`, `'f64'`: arithmetic, comparisons, conversions, as in LLVM |
| [plan_vm.md](plan_vm.md) | paused · 1/6 steps | Spindle: small embeddable VM that runs programs without LLVM |

## Closed

| Plan | What |
|---|---|
| [plan_memory.md](implemented/plan_memory.md) | `'ptr'`, `'alloca'`, `'getelementptr'`, `'load'`, `'store'` as in LLVM; effects ordered by `$seq`; globals |
| [plan_switch.md](implemented/plan_switch.md) | Struct of jumps applied to a run-time index → LLVM `switch` |
| [plan_constant_folding.md](implemented/plan_constant_folding.md) | Opcodes on literals fold to the bytes LLVM would compute |
| [plan_struct_pack.md](implemented/plan_struct_pack.md) | `$struct_to_fields` / `$fields_to_struct`: build structs dynamically |
| [plan_if_as_struct_apply.md](implemented/plan_if_as_struct_apply.md) | `if c then t else e` is sugar for `{e, t} c` |
| [plan_builtin.md](implemented/plan_builtin.md) | Every primitive is a global `$name`; `fix` is no longer a keyword |
| [plan_struct_apply.md](implemented/plan_struct_apply.md) | `s [01]` selects a field by index; labels optional |
| [plan_banf_explicit.md](implemented/plan_banf_explicit.md) | BANF translation only reduces; no defaults, no inference |
| [plan_annotation.md](implemented/plan_annotation.md) | No enforced parentheses; `e : F` is a `Formed` term |
| [plan_term_as_form.md](implemented/plan_term_as_form.md) | Forms are plain terms, same syntax as any term |
