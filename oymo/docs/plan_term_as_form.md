# Plan: forms are Terms

Status: **implemented**.

## Goal

Replace `type Form = str | StructForm | FunctionForm` in [terms.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/terms.py) with plain `Term`s.
There is no separate form grammar: a form is written with the same syntax as any other term.

| Today (term) | After (term) | Today (source) | After (source) |
|---|---|---|---|
| `'i32'` | `ByteArray(b'i32', form=Empty)` | `: i32` | `: 'i32'` |
| `StructForm([('x', f)])` | `Struct([Field('x', f)])` | `: {x: i32}` | `: {x = 'i32'}` |
| `FunctionForm(p, r)` | tagged `Struct` (Decision 1) | `: {c: i8} => i32` | `: {c = 'i8'} => 'i32'` |
| `UNKNOWN_FORM` (`'unknown'`) | `syntax.Empty` | `: unknown` or omitted | omitted |

- `Lambda.param_form` and `ByteArray.form` hold a `Term`. `Empty` means unknown and is
  written by leaving out `: form`.
- `UNKNOWN_FORM` is removed everywhere. `unknown` is no longer special.
- `x: i32 -> x`: `i32` is a **variable reference**. `x: 'i32' -> x`: `'i32'` is a byte array.
- Struct syntax is only `{label = expr}`. Every field must have a value, so `{x, y: i32}` is gone.
- Byte array syntax is only `[hex]` / `'text'`. Quoted names (`"..."`) stay for variable names and labels only.

## Decision 1: how to tag a function form

A function form is an ordinary `Struct` whose first field is a `tag` field:

```python
Struct([
    Field('tag', ByteArray(b' => ', form=Empty)),
    Field('param', P),
    Field('result', R),
])
```

- `=>` (or `⇒`) is only syntax sugar. `{c = 'i8'} => 'i32'` parses to exactly
  `{tag = ' => ', param = {c = 'i8'}, result = 'i32'}`, and users may write that by hand.
- The spaces around `=>` make the tag deliberate. A matching tag means the user meant
  to write a function form, which is fine. `'=>'` without spaces is an ordinary byte array.
- `is_function_form(form)` checks: a `Struct` with exactly the fields `tag`, `param`, `result`,
  in that order, where `tag == FUNCTION_TAG`. A wrong shape is not a function form; it is
  treated as a plain struct.
- Constants in `terms.py`: `FUNCTION_TAG_LABEL = 'tag'` and `FUNCTION_TAG = ByteArray(b' => ', form=Empty)`.
- Printer: a struct that passes `is_function_form` prints as `P ⇒ R`. So writing the
  struct by hand round-trips to the sugar.

Considered and dropped: an empty `""` label (users could not write it by hand), a `tag: str`
member on `Struct` (nominal typing; deferred), `Lambda` as a Π type, and a dedicated `Arrow` term.

## Decision 2: locations and equality

**Chosen:** in every term dataclass in `terms.py` (`Variable`, `BruijnIndex`, `Lambda`,
`Apply`, `Field`, `Struct`, `Project`, `If`, `Fix`, `ByteArray`), declare
`location: Location | None = field(default=None, compare=False)`.
- `==` / `!=` on forms keep working. A parsed form equals the same form built in code.
- The `None` default lets code build forms without a location (`form_of`, prim signatures).
  `location` is already the last field everywhere, so positional construction still works.
- Cost: `==` no longer checks locations in tests. Only 4 asserts relied on that:
  `grammar_test.py:10, 14, 111` and `bruijn_test.py:30`. Add explicit
  `.location == Location(...)` asserts there, as `grammar_test.py:200-202` already do.

## Decision 3: what may follow `:`

Any expression can be a form. The form after `:` is read greedily. These forms are written as they are:
- a struct `{...}`
- a byte array `[..]` / `'..'` (which may carry its own `: form`)
- a function form `A => B`, where `A` and `B` are again one of these
- a parenthesised expression `( ... )`

**Any other expression needs parentheses.** That covers variables, applications, projections,
lambdas, `if`, `let` and `fix`. Examples:

| Source | Meaning |
|---|---|
| `x: 'i32' -> x` | lambda, param form `'i32'` |
| `x: {c = 'i8'} => 'i32' -> x` | lambda, param form is a function form |
| `x: (i32) -> x` | lambda, param form is the variable `i32` |
| `x: (a -> b) -> c` | lambda, param form is the lambda `a -> b` |
| `x: i32 -> x` | syntax error (the form would be a bare variable) |
| `f [00]: 'i32' y` | `f` applied to `[00]: 'i32'`, then to `y` (the form stops after the byte array `'i32'`) |

Grammar sketch:

```
FORM       := FORM_ATOM ('=>' FORM)?             // right-associative
FORM_ATOM  := STRUCT | BYTE_ARRAY | GROUP
FORM_OPT   := (':' FORM)?                        // omitted → Empty
```

`=>` is also an expression operator, so a function form can be a struct field value
(`{f = {a = 'i8'} => 'i32'}`) or a let value. It binds looser than application and
tighter than `->`, `if` and `let`:

```
EXPRESSION := LAMBDA | IF | LET | ARROW
ARROW      := APPLY ('=>' ARROW)?
```

So `decls: {} => 'i32' -> defs -> body` still reads as the lambda `decls` (form `{} => 'i32'`),
then the lambda `defs`.

## Decision 4: hashability

`PrimSignature` is `frozen=True` and holds forms. Term dataclasses are not hashable
(`Struct.fields` is a list). No code hashes signatures today, as far as I found. Leave it alone,
and fix it only if something breaks.

## Changes, file by file

### [terms.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/terms.py)
- Delete `Form`, `StructForm`, `FunctionForm`. Export `Empty = syntax.Empty`.
- Type `Lambda.param_form: Term` and `ByteArray.form: Term`. Declare every `location` as
  `field(default=None, compare=False)` (Decision 2).
- `Lambda.children()` yields `param_form` then `body`. `ByteArray.children()` yields `form`.
- Add helpers, so callers never build the encoding by hand:
  - `name_form(name: str) -> ByteArray`. ASCII bytes, `form=Empty`.
  - `form_name(form) -> str | None`. Returns the text of a `ByteArray` with an `Empty` form.
  - `struct_form(fields: list[tuple[str, Term]]) -> Struct`
  - `function_form(param, result) -> Struct` and `is_function_form(form) -> bool`
- Order matters: check `is_function_form` **before** treating a `Struct` as a struct form, in every `match`.

### [grammar.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/grammar.py)
- Remove `UNKNOWN_FORM`, `rn.FORM` and `rn.ARROW_FORM`. Add `FORM` / `FORM_ATOM` (Decision 3)
  and the expression-level `ARROW`.
- `_form_opt` returns `Empty` when `: form` is omitted.
- Lambda, let and byte array use the new `FORM_OPT`.
- Update `rule_names.py` to match.

### [bruijn.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/bruijn.py)
- Forms can contain variables now. `_resolve` resolves a lambda's `param_form` in the
  **outer** scope (before the param is pushed), and resolves a byte array's `form`.
- `_map_children` / `_map_indices` also map `Lambda.param_form` (at the outer depth) and `ByteArray.form`.
  So `shift`, `substitute` and `beta` keep forms correct.

### [printer.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/printer.py)
- Remove the form printers (`_compact_form`, `_pretty_form`, `_compact_field_suffix`).
  A form is printed as a term.
- `: form` suffix: nothing for `Empty`. A struct, byte array or function form is printed
  as is; any other term is printed in parentheses (Decision 3).
- Function form: printed as `P ⇒ R`. `P` is parenthesised if it is itself a function form
  (or not a form atom). Check `is_function_form` before the generic `Struct` case.
- `_bytes_text`: the `'text'` rule checks `form is Empty`. So a name form prints as `'i32'`.

### [banf_terms.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/banf_terms.py)
- Change `terms.Form` annotations to `terms.Term`.
- `form_of` (MakeStruct) uses `struct_form`. The project lookup and `field_index` iterate `Struct.fields`.
- `!= 'i1'` becomes `!= name_form('i1')`.
- `show_form` keeps BANF's own text syntax (`i32`, `{a: i32}`, `A => B`), so the BANF golden is unchanged.
  It reads the new terms through `form_name`, `is_function_form` and `Struct.fields`.

### [banf_translate.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/banf_translate.py)
- `_check_data_form`: reject a function form first, then recurse into struct fields.
  Reject `Empty` ("form must be known"). Reject anything that is not a name form or a struct
  ("form must be a literal"). This covers variables and other expressions in form position.
- Replace `UNKNOWN_FORM` with `Empty` (lines 141, 268, 312, 326, 335), using `is Empty` checks.
- Update the `StructForm` / `FunctionForm` `isinstance` checks and the `Lambda(... param_form=StructForm(...))` pattern.

### [banf_rename.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/banf_rename.py), [banf_reduce.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/banf_reduce.py), [llvm_translate.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/llvm_translate.py)
- Get labels from `Struct.fields`. `llvm_type` matches an int name through `form_name`.
- Check any pass that rebuilds `Lambda` / `ByteArray` keeps or maps the form.

### [banf_prim.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/banf_prim.py), [llvm_prims.py](file:///usr/local/google/home/orti/github/tapl/oymo/src/oymo/oymomo/llvm_prims.py)
- Keep `INT_FORMS` as strings for naming prims (`add_i32`). Wrap them with `name_form`
  in `PrimSignature.params` / `result`. `int_bits` keeps taking a string.

### Tests (about 240 lines use the old form syntax)
- All oymomo sources in tests: `: i32` becomes `: 'i32'` and `{a: i32}` becomes `{a = 'i32'}`.
  `=> i32` becomes `=> 'i32'`.
- `grammar_test.py`: `UNKNOWN_FORM` becomes `Empty`. Build expected forms with the helpers.
  Add explicit location asserts at lines 10, 14, 111 (Decision 2). Remove `{x, y: i32}` (no omitted field values).
  Add tests for Decision 3: `x: (i32) -> x`, `x: (a -> b) -> c`, `x: i32 -> x` is an error,
  and `=>` as a field value.
- `bruijn_test.py`: add an explicit location assert at line 30. Add tests that variables in forms resolve
  in the outer scope, and that `shift` / `substitute` reach forms.
- `printer_test.py`: `test_pretty_omits_unknown_forms` becomes `x -> x` → `x → x`.
  Add a case where `x: (unknown) -> x` keeps its form. Line 197 builds forms with the helpers.
  Add a round-trip case for the hand-written `{tag = ' => ', ...}` printing as `⇒`.
- `banf_translate_test.py:408`: `{g: unknown}` becomes a test where `g` has no form.
  Add a "form must be a literal" test (for example `x: (i32) -> ...`).
- `banf_terms_test.py`, `llvm_translate_test.py`: `POINT` and the others use `struct_form` / `name_form`.
- Goldens: update `simplest.oymo` and `simplest.shaped.oymo` to the new syntax
  (`args: {a = 'i32'} → [00000000]: 'i32'`). `simplest.banf` and `simplest.ll` should not change.

### [notes.md](file:///usr/local/google/home/orti/github/tapl/oymo/docs/notes.md)
- Rewrite "Forms are optional; omitted means unknown" (unknown is `Empty`; `: unknown` is gone).
- Replace "a struct term and a struct form share `{}` and are told apart by `=` vs `:`".
  Now there is one struct syntax.
- Rewrite "Function forms" for the tagged struct and the expression-level `=>`.
- Add a decision "forms are terms" covering Decisions 1–3.

## Verification
- Run `pytest` (unit + golden), plus the repo's lint and type check.
- `grep -rn "UNKNOWN_FORM\|StructForm\|FunctionForm\|terms.Form\|ARROW_FORM"` should return nothing.

## Decided
1. Tag: the first field is `tag = ' => '`, with a space on each side.
2. Equality: `location` is `field(default=None, compare=False)`.
3. `unknown` is no longer special.
4. Any expression can be a form. Struct, byte array, function form or parenthesised forms are written as they are;
   anything else needs parentheses.
5. Every struct field must have a value.
6. Bare names after `:` are variables; `'i32'` is a byte array.
