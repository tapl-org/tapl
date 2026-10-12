# Plans

Each plan is one design change, carried out in steps of one commit each. A plan is
**open** until every step is done, and then **closed**, with its status set to
**implemented**.

## Open

| Plan | Status | Description |
|---|---|---|
| [plan_builtin.md](plan_builtin.md) | in progress; 4 of 5 steps | Every primitive is a global constant written `$name` (`$add_i32`, `$fix`), so the program drops its `prim ->` binder and `fix` is no longer a term or keyword. A new built-in is one table entry. Also, `s [01]` on a value struct becomes the BANF op `GetIndex`, replacing `prim.extractvalue`. |
| [plan_struct_pack.md](plan_struct_pack.md) | proposed, with open questions; 0 of 2 steps | `unpack s` turns a struct into a list of fields and `pack l` turns one back, so a struct can be built dynamically: labels and number of fields computed by oymomo code. To be built on `plan_builtin.md`. |

## Closed

| Plan | Description |
|---|---|
| [plan_struct_apply.md](plan_struct_apply.md) | A struct applied to an index selects the field (`s [01]`), so a field can be picked by a position computed at run time. Field labels are optional, so a struct can be a tuple. In BANF, `prim.extractvalue` reads a field of a value struct by its index; step 1 of `plan_builtin.md` replaces it with the op `GetIndex` (`s [01]`). |
| [plan_banf_explicit.md](plan_banf_explicit.md) | BANF translation has no defaults: it only reduces terms, infers nothing, and drops unneeded forms. A written form replaces a computed one, since a form is not a type. |
| [plan_annotation.md](plan_annotation.md) | No enforced parentheses: any syntax has a meaning based on precedence. `e : F` is a `Formed` term, so any term, a form included, can come from an expression. |
| [plan_term_as_form.md](plan_term_as_form.md) | Forms are plain terms (`'i32'`, `{x = 'i32'}`, `{c = 'i8'} => 'i32'`), written with the same syntax as any other term instead of a separate form grammar. |
