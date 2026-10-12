# Plans

Each plan is one design change, carried out in steps of one commit each. A plan is
**open** until every step is done, and then **closed**, with its status set to
**implemented**.

## Open

| Plan | Status | Description |
|---|---|---|
| [plan_confluence.md](plan_confluence.md) | proposed, with open questions; 0 of 4 steps | Reduction order doesn't change the result: any two full-β reductions can be joined. Beta stops stripping the argument's form and a new rule `(t : G) : F → t : F` replaces it. Built-in rules must commute with reduction of their argument. A test-only full-β reducer checks that every strategy, `whnf` and `shape` included, gives the same normal form. |
| [plan_struct_pack.md](plan_struct_pack.md) | proposed, with open questions; 0 of 2 steps | `$unpack s` turns a struct into a list of fields and `$pack l` turns one back, so a struct can be built dynamically: labels and number of fields computed by oymomo code. Two entries in `bruijn.BUILTIN_RULES`, with no new term or reserved word. |
| [plan_switch.md](plan_switch.md) | proposed, with open questions; 0 of 3 steps | `{a0, a1, ..., an} i` in tail position, with three or more jumps, is a BANF `Switch`, lowered to LLVM `switch`. Two fields stay a `Branch`. A switch may repeat a target with the same args. Open: what an index past the last target does. |
| [plan_constant_folding.md](plan_constant_folding.md) | proposed, with open questions; 0 of 4 steps | An opcode whose operands are all literals reduces to its result (`$add_i32` on `[01000000]` and `[02000000]` is `[03000000]: 'i32'`), with the bytes LLVM would compute and nothing folded where LLVM has no defined result. Each opcode gets a rule in `bruijn.BUILTIN_RULES`. |
| [plan_memory.md](plan_memory.md) | proposed, with open questions; 0 of 4 steps | Mutable memory: a `'ptr'` form (an opaque address) and the opcodes `$load_T`, `$store_T` (gives `{}`) and `$alloca_T` (entry block only). Effects happen in let order, as calls do today; no memory opcode reduces. A data symbol becomes its address (breaking). Open: let order or a memory token. |

## Closed

| Plan | Description |
|---|---|
| [plan_if_as_struct_apply.md](plan_if_as_struct_apply.md) | `if c then t else e` is sugar for `{e, t} c`: a struct applied to the condition, which the kernel already reduces. The printer prints a two-field unlabeled struct apply as `if`. In BANF, a struct literal applied to an atom in tail position is a `Branch`. The `If` term goes; the syntax stays. |
| [plan_builtin.md](plan_builtin.md) | Every primitive is a global constant written `$name` (`$add_i32`, `$fix`), so the program has no `prim ->` binder and `fix` is no longer a term or keyword. A built-in has a reduction rule in `bruijn.BUILTIN_RULES`, an opcode, or both; a strict rule's argument is reduced first. `s [01]` on a value struct is the BANF op `GetIndex`. |
| [plan_struct_apply.md](plan_struct_apply.md) | A struct applied to an index selects the field (`s [01]`), so a field can be picked by a position computed at run time. Field labels are optional, so a struct can be a tuple. In BANF, `prim.extractvalue` reads a field of a value struct by its index; step 1 of `plan_builtin.md` replaces it with the op `GetIndex` (`s [01]`). |
| [plan_banf_explicit.md](plan_banf_explicit.md) | BANF translation has no defaults: it only reduces terms, infers nothing, and drops unneeded forms. A written form replaces a computed one, since a form is not a type. |
| [plan_annotation.md](plan_annotation.md) | No enforced parentheses: any syntax has a meaning based on precedence. `e : F` is a `Formed` term, so any term, a form included, can come from an expression. |
| [plan_term_as_form.md](plan_term_as_form.md) | Forms are plain terms (`'i32'`, `{x = 'i32'}`, `{c = 'i8'} => 'i32'`), written with the same syntax as any other term instead of a separate form grammar. |
