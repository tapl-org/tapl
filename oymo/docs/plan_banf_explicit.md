# Plan: BANF translation has no defaults

Status: **in progress**.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [x] 1. `terms.Void` goes back to `terms.Empty` (`oymomo: an omitted form is Empty, not void`)
- [x] 2. A let's form replaces its op's form (`oymomo: a let's form replaces its op's form`)
- [x] 3. A formed atom has the written form (`oymomo: any atom can be formed`)
- [x] 4. `=> R`: a function form without params (`oymomo: a function form's param may be omitted`)
- [x] 5. One `module` binder declares every symbol (`oymomo: merge decls and defs into module`)
- [x] 6. Data defined in the module body (`oymomo: module data can be defined`)
- [ ] 7. Wrap up (`docs: plan_banf_explicit implemented`)

Step 1 comes first. Step 4 comes before step 5, and step 5 before step 6. Steps 2 and 3
don't depend on the others.

## Goal

**BANF translation only reduces terms.** `shape` runs term reductions (beta, fix, project,
`if`) until each position has BANF's shape, and then renames binders (`banf_rename`).
`convert` only reads the result:

- no default values: an omitted form is `Empty`, and `Empty` is never read as `void`,
  or as anything else;
- nothing inferred: every form BANF stores is written in the source, including return
  forms;
- unneeded forms are dropped: a form written where BANF has no slot for it is dropped,
  not rejected;
- **a form is not a type**: a written form is never checked against a computed one. It
  replaces it.

A term that doesn't have BANF's shape after reduction is rejected, with the usual
message. The source fixes it explicitly.

## Decisions

1. **An omitted form is `Empty`.** `terms.Void = syntax.Empty` goes back to
   `terms.Empty = syntax.Empty`. `Empty` means "not written". There is no void form;
   `'void'` is just a name.
2. **`Empty` is a shape like any other.** Each BANF position either needs a form, takes
   an optional one, or has no slot for one:
   - needs a form (`Const`, block params, the `module` binder and each symbol in it):
     `Empty` is rejected ("form must be written");
   - takes an optional form (a let, an atom, a function declaration's params): `Empty`
     has the meaning that position gives it, and a written form is used as written;
   - no slot for a form (`prim` and `blocks` binders, a data definition): a written form
     is dropped, as today. It isn't rejected.
3. **`banf_rename` only changes its fixed names.** Structural binders can have any name
   and are renamed to `prim`, `module`, `blocks` and `args`, so `main = f -> {...}`
   shapes to `main = blocks -> {...}`. A clashing let is still renamed (`t`, `t_6`, ...).
4. **A let's form replaces its op's form.** `let t: 'i32' = prim.eq_i32 {...} in t`
   gives `t` the form `i32`, with no check against `i1`. `banf.Let` gets a `form`
   field: `Empty` means `form_of(op)`.
5. **A formed atom has the written form.** `args.n : 'i32'` and `t : 'i32'` are atoms
   with the form `i32`, whatever the form of `args.n` or `t`. So
   `let m: 'i32' = args.n in m` reduces to `args.n : 'i32'` (new beta) and translates.
   Same for a formed byte array: `([01]:'i8'):'i16'` has the form `i16`.
6. **`=> R` is a function form without params.** `FunctionForm.param` may be `Empty`,
   written by leaving it out: `=> 'i1'`. It differs from `{} => 'i1'`, which declares
   zero params.
7. **One `module` binder for declarations and definitions.** `decls` and `defs` merge.
   The binder's form declares every symbol, and each declaration's shape says whether
   the body defines it. See [The module binder](#the-module-binder).
8. **Return forms are declared, not computed.** Every function's result form, imported or
   defined, is written in the `module` binder's form. `_infer_return_forms` goes away,
   and recursion needs nothing special.
9. **Every parameter list and form is written once.** A defined function's params come
   only from its entry block; an imported function's only from its declaration. A
   defined data's form comes only from its declaration.
10. **`banf_reduce` only changes its positions.** Its reductions are allowed, and it
    already leaves a term it can't shape for `convert` to report.

---

## What is implicit today

| Where | Today | After |
|---|---|---|
| `terms.Void` | an omitted form is called void; `show_form` prints `void` | `terms.Empty`; `show_form` prints nothing for it |
| structural binders | renamed to `prim`, `decls`, `defs`, `blocks`, `args` | renamed to `prim`, `module`, `blocks`, `args` |
| clashing lets | renamed to `t_6`, `t__6`, ... | same |
| written let form | must equal the op's form | replaces the op's form |
| formed atom other than a byte array | rejected | the written form |
| formed formed byte array | rejected | the outer form |
| return forms | inferred, iterated to a fixed point over the module | declared in the `module` binder's form |
| imports vs definitions | two binders, `decls` and `defs` | one `module` binder; the declaration's shape says which |
| module data | imports only | imported or defined with a byte array |
| `defs` binder form | any form, dropped | gone |
| `prim`, `blocks` binder forms | any form, dropped | same |
| `args` binder form | must be a struct | same |

Unchanged: `banf.verify` still checks call and jump arguments against params, the
condition of a branch against `i1`, and each return against the declared return form.
These compare a form with a *required* form, not a written form with a computed one. The
source meets them explicitly with a let form or a formed atom.

---

## The module binder

```
prim -> module: {
  putchar = {c = 'i8'} => 'i32',
  errno = 'i32',
  answer = 'i32',
  main = => 'i32',
} -> {
  answer = [2a 00 00 00],
  main = blocks -> {
    entry = args: {a = 'i32'} -> let t = module.putchar {c = [41]:'i8'} in t,
  },
}
```

The `module` binder's form is a struct with one field per symbol. The shape of each
declaration says what the body must do with it:

| Declaration | Defined in the body | Result |
|---|---|---|
| `=> R` | as a function | `banf.Function`: params from its entry block, return form `R` |
| `=> R` | no | rejected: "'main' declares no params, so it must be defined" |
| `{...} => R` | no | import, `banf.Signature` |
| `{...} => R` | yes | rejected: "'putchar' declares its params; a definition takes them from its entry block" |
| data form `F` | no | import, `banf.Data` |
| data form `F` | as a byte array | defined data, `banf.Data` with a value |

More rules:
- **A body label must be declared**: "'f' is defined but not declared".
- **A definition must fit its declaration**: a function declaration (`=> R`) needs a
  function definition (`blocks -> {...}`); a data declaration needs a byte array
  ("'answer' is declared as data, so its definition must be a byte array").
- **Checks on declarations**, as for `decls` today: a function form's param is a struct
  or `Empty`, and no function forms are nested inside other forms. `Empty` alone
  (`main = `) can't be written, since a struct field needs a value.
- **One way to use a symbol**: `module.f {...}` is a `Call` and `module.errno` is a
  `GetData`, whether the symbol is imported or defined. A call reads the callee's params
  from its declaration (import) or its entry block (definition), and its return form from
  its declaration.
- **Recursion** needs nothing special, since the return form is declared:

```
prim -> module: {loop = => 'i8'} -> {
  loop = blocks -> {
    entry = args: {c = 'i1'} -> if args.c then blocks.a {} else blocks.b {},
    a = args: {} -> let t = module.loop {c = [00]:'i1'} in t,
    b = args: {} -> [07]:'i8',
  },
}
```

- **A forgotten definition is caught.** A function meant to be defined is declared as
  `=> R`, so leaving its definition out is an error in translation, not at link time.
- **Shape**: `prim -> module -> {...}`, one structural binder fewer. In a block body with
  `k` lets, `args` is `$k`, `blocks` `$k+1`, `module` `$k+2` and `prim` `$k+3`.
- **Order of BANF bindings**: in declaration order.

### `=> R` syntax

`ARROW: PROJECT '=>' ARROW | '=>' ARROW | PROJECT`. So `=> 'i1'` is
`FunctionForm(Empty, 'i1')`, `=> => 'i1'` is `FunctionForm(Empty, FunctionForm(Empty, 'i1'))`,
and `f => b` is still `FunctionForm(f, b)`. As an apply argument it needs parentheses:
`f (=> b)`. The printer prints `Empty` as nothing, so `=> 'i1'` and `{} => 'i1'` print as
written.

### Defined data

`answer = [2a 00 00 00]` with `answer = 'i32'` declared is a `banf.Data` with
`value=b'\x2a\x00\x00\x00'` and form `i32`.

- The definition reduces to a byte array: `banf_reduce` takes it to whnf.
- Its form is the declared one. A form written on the definition (`[2a 00 00 00] : 'i8'`)
  is dropped (decision 2).
- `banf.Data` gets `value: bytes | None`; `None` is an import.
- `llvm_translate` emits a writable LLVM `global` (not `constant`) with an initializer,
  like imported data. Details such as constness will come later with the data's form.
  The initializer uses the rules that
  constants use today: integer forms only, and the byte count must fit the form
  ("A i32 constant needs 4 bytes."). Struct data forms are rejected there until struct
  constants are supported.
- `module.answer` is a `GetData` (a load), the same as for imported data.

---

## LLVM for a replaced form

Decisions 4 and 5 let a value have a form whose LLVM type differs from the op's or the
atom's: `let t: 'i32' = prim.eq_i32 {...}` makes an `i1` value with the form `i32`.
BANF accepts it, since a form isn't a type. `llvm_translate` rejects it when the LLVM
types differ ("let 't' is formed as i32, but its op gives i1"). Nothing is converted
or reinterpreted: no `bitcast`, no widening, no narrowing. When the LLVM types are equal
(for example, two struct forms with the same layout), the value is used as it is.

---

## Implementation steps

Each step leaves `hatch run full-check` green and updates `docs/notes.md` for its part.

### Step 1: `Void` → `Empty`

- `terms.py`: `Empty = syntax.Empty`, comment "An omitted form: not written."
- `grammar.py`, `printer.py`, `bruijn.py`, `banf_terms.py`, `banf_translate.py`: rename
  every use. `show_form(Empty)` prints nothing, as the oymomo printer does.
- `_check_data_form`: "form must be written" instead of "form must be known".
- Tests: `grammar_test.py`, `bruijn_test.py`, `banf_reduce_test.py`, `printer_test.py`,
  `banf_terms_test.py` (`show_form(Empty) == ''`, `{f: => i32}`).
- `notes.md`: "Forms are optional; omitted means void" becomes "omitted means `Empty`",
  without "each later stage decides what it can infer".

### Step 2: a let's form replaces its op's form

- `banf_terms.py`: `Let(name, value, form=Empty)`. A helper `let_form(let, forms, module)`
  returns `let.form` unless it is `Empty`, else `form_of(let.value, ...)`. The verifier,
  printer and `llvm_translate` use it. The printer shows `t: i32 = prim.eq_i32 ...` when
  the form is written.
- `banf_translate.py`: `body` stores the written form in the `Let`, after
  `_check_data_form`. Delete `written_forms` and `_check_written_forms`.
- `llvm_translate.py`: reject a replaced form whose LLVM type differs (see
  [LLVM for a replaced form](#llvm-for-a-replaced-form)), with a test.
- Tests: `test_let_with_wrong_written_form` becomes a let whose form replaces the op's;
  printer and LLVM tests for a let with a form.
- `notes.md`: "What the shape is", **Let**; "Forms are stored only where they can't be
  worked out" gets the optional let form.

### Step 3: a formed atom has the written form

- `banf_terms.py`: `Var(name, form=Empty)`; `atom_form` returns the written form unless
  it's `Empty`. A `Const` already has its form.
- `banf_translate.atom`: `Formed(inner, form)` → the atom of `inner` with `form` (after
  `_check_data_form`); a `Const` takes the outer form.
- `llvm_translate.py`: reject a replaced form whose LLVM type differs (see
  [LLVM for a replaced form](#llvm-for-a-replaced-form)), with a test.
- Tests: `args.n : 'i32'`, `t : 'i32'`, `([01]:'i8'):'i16'`, and
  `let m: 'i32' = args.n in m`. Remove the "Only a byte array without a form can be given
  a form." test.
- `notes.md`: "Atoms", and the `Formed` section ("It rejects any other `Formed`" goes).

### Step 4: `=> R`

- `grammar.py`: the `'=>' ARROW` alternative of `ARROW`, building
  `FunctionForm(Empty, R)`.
- `printer.py`: `FunctionForm(Empty, R)` prints `=> R` (compact and pretty); as an apply
  argument it gets parentheses.
- `banf_terms.show_form`: `(=> R)`.
- `banf_translate`: until step 5, a `decls` function form with an `Empty` param is
  rejected ("definition is not found").
- Tests: parse and print `=> 'i1'`, `=> => 'i1'`, `{} => 'i1'`, `f => b`, `f (=> b)`.
- `notes.md`: "Function forms".

### Step 5: one `module` binder (breaking)

- `banf_rename.py`: fixed names `PRIM`, `MODULE`, `BLOCKS`, `ARGS`; `DECLS` and `DEFS` go.
- `banf_reduce.py`: positions `prim -> <module> -> <body>`; one `lambda_then` fewer.
- `banf_translate.py`:
  - `_unwrap`: `prim -> module: {...} -> {...}`; the module form must be a struct.
  - `_imports` becomes `_declarations`: one entry per declared symbol, with the same
    checks as `_imports` today, and an `Empty` param allowed.
  - `_function_header`: the label must be declared as `=> R`; the return form is `R`; the
    params come from the entry block.
  - The table in [The module binder](#the-module-binder): undefined `{...} => R` and data
    declarations become `banf.Signature` and `banf.Data`; the error rows are rejected.
  - `_Block.binder`: `(ARGS, BLOCKS, MODULE, PRIM)`.
  - `op`: one `MODULE` case for calls (`Call`) and data (`GetData`); the `DECLS` and
    `DEFS` cases merge.
  - Delete `_known_return_form` and `_infer_return_forms`.
- Tests: every program in `banf_translate_test.py`, `banf_reduce_test.py`,
  `banf_rename_test.py`, `llvm_translate_test.py` and the golden `simplest.oymo` moves to
  `prim -> module: {...} -> {...}`. New tests: one per row of the table; defined but not
  declared; recursion without a let form. The return-form inference tests go.
- `notes.md`: "Program shape", "`decls`" and "`defs`" become one "`module`" section;
  "Binders get fixed names"; "`convert` finds binders by index"; replace "Return forms
  are inferred, to a fixed point" with "Return forms are declared".

### Step 6: defined data

- `banf_terms.py`: `Data(name, form, value=None)`. The printer shows
  `answer: i32 = [2a000000]`.
- `banf_reduce.py`: a module body field that isn't a lambda is taken to whnf.
- `banf_translate.py`: a data declaration defined in the body by a byte array (or a
  formed one, whose form is dropped) becomes `banf.Data` with that value. Anything else
  is rejected.
- `llvm_translate.py`: a `Data` with a value is a writable `global` with an initializer, using
  `_const`'s rules.
- Tests: translate, print and emit LLVM for defined data; a wrong byte count; a struct
  data form rejected in LLVM; a function definition for a data declaration, and the
  reverse.
- `notes.md`: the "`module`" section.

### Step 7: wrap up

- `notes.md`: the goal of this plan in "oymomo to BANF".
- Status: **implemented**.

## Verification

```
hatch run full-check
```
