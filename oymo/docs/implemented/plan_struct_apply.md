# Plan: a struct applied to an index selects the field

Status: **implemented**.

> [!NOTE]
> Since [plan_switch.md](../plan_switch.md) step 1, an index past the last field selects
> the last field instead of being stuck (`{a = '23'} [01]` is `'23'`); only `{} i` stays
> stuck. Decision 6 and the examples below describe the rule as first implemented.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [x] 1. A struct field's label is optional (`oymomo: a struct field's label is optional`)
- [x] 2. The struct apply rule in `bruijn.reduce` (`oymomo: a struct applied to an index selects the field`)
- [x] 3. `banf_reduce` reduces the index of a struct apply (`oymomo: banf_reduce reduces a struct apply's index`)
- [x] 4. `prim.extractvalue`: a field of a value struct by index, in BANF (`oymomo: add prim.extractvalue`)

## Goal

**Pick a struct field by a position computed at run time.** `s.a` picks a field by a
name written in the source (`Project`). `s i` picks a field by its position, and `i` is a
term, so it can come from a variable. A field needs no label, so a struct can be a tuple.

```
{a = '23'} [00]                          ⇒   '23'
(i -> {a = '23', b = '45'} i) [01]       ⇒   '45'
{'1', '2'} [01]                          ⇒   '2'
{a = '1', a = '2'} [01]                  ⇒   '2'
{a = '1', a = '2'}.a                     ⇒   '1'
{a = '23'} [01]                          stuck
```

In BANF, a value struct (a let, or a param such as `args.p`) has its fields read by
index with `prim.extractvalue {struct = s, index = [01]: 'i8'}`, as well as by label with `s.a`.

## Decisions

### Kernel

1. **A field's label is optional.** `{'1', b = '2'}` has an unlabeled field and a field
   `b`. An unlabeled field's label is the empty string (`Field.label == ''`). A written
   name is still never empty: `{"" = x}` stays a parse error, so `''` only ever means
   "no label".
2. **Labels can be duplicated, and `Project` picks the first.** This is today's
   behavior (`bruijn.project`), now written down: `{a = '1', a = '2'}.a` gives `'1'`.
   Unlabeled fields are many fields with the label `''`.
3. **Labels by name, positions by index.** `Project` is the only way to pick a field by
   its label. A struct apply never looks at labels. An unlabeled field can only be reached
   by its index, since `s.` can't be written.
4. **No new syntax for access and no new term.** Struct and project syntax keep static
   labels: no `s.(e)`, no `{(e) = v}`. `s i` is already an `Apply`; it only gets a
   reduction rule.
5. **An index is an unsigned little-endian integer of any length.** `[01]`, `[0100]` and
   `[01000000]` are all index 1; `[0001]` is index 256. Indexes start at 0. Any spelling
   of the same number is the same index.
6. **A missing field is stuck, not an error**, as for projection: the term is not a redex
   and is left as it is. The same goes for an index past the last field, for `''` (no
   bytes is not a number), and for an argument that is not (yet) a byte array.
7. **Every field is reachable by index**, duplicates and unlabeled fields included.
   `{a = '1', a = '2'} [01]` gives `'2'`, which `Project` can't reach.
8. **A form on the index is ignored**: `{a = x} ([00] : 'i8')` gives `x`. The index is its
   bytes. Same as an `if` condition, which sees through `Formed` (plan_annotation C2).
9. **`Project` stays its own term.** `s.a` and `s i` reduce to the same field only when `a`
   is the first field with that label and `i` is its position. BANF's shapes (`args.n`,
   `blocks.label`, `prim.op`, `decls.f`) and the printer match on `Project`.

### BANF

10. **`prim`, `module`, `blocks` and `args` are always accessed by a label.** They are
    binders, not structs. In the kernel a struct apply works on any struct, so a struct of
    functions can be called by index: `(blocks -> blocks [01] x) {a = f, b = g}` reduces
    to `g x`. In BANF, `args [00]`, `blocks [01] {...}`, `module [00] {...}` and
    `prim [00] {...}` stay stuck, and `convert` rejects them with today's messages. A
    struct apply that reduces away (the struct and the index are known) leaves nothing
    behind.
11. **Every other struct is read by index with `prim.extractvalue`**, or by label with `s.a` as
    today. `prim.extractvalue {struct = s, index = [01]: 'i8'}` is the field at position 1 of
    the value struct `s`. It is written like any prim call. Its index must be a byte array
    literal with an integer form (`i1` to `i64`), read as decision 5 says; LLVM's
    `extractvalue` needs a constant index. A let name as index, an index past the last
    field, or a `struct` that is not a struct is a `convert` error.
12. **`prim.extractvalue` is a dynamic prim.** Its result form depends on the struct's form
    and the index, so it can't be a `PrimSignature`, which stays as it is. A new class,
    `banf_prim.DynamicPrim`, has the param labels and a function that computes the result
    form from the arguments; dynamic prims live in their own table, `DYNAMIC_PRIMS`. In BANF
    it is still a `PrimCall`: no new op.
13. **Unlabeled fields are allowed in value structs and data forms**, and reached only
    with `prim.extractvalue`. They are rejected where a label names something: the top level of
    a block's param form (`args: {p = {'i32', 'i32'}}` is fine, `args: {'i32'}` is not),
    declarations, definitions, blocks, and a call's or a prim's argument struct. Duplicate
    labels stay an error in BANF; several unlabeled fields are not duplicates.

---

## Design

### A. Optional labels

**Grammar.** A field is `NAME = EXPRESSION` or just `EXPRESSION`. The labeled form is
tried first, so `{a = b}` is a labeled field and `{a}` is an unlabeled field whose value is
the variable `a`.

```python
rn.STRUCT: Seq(
    _punct('{'),
    Separated(
        First(
            Seq(NAME, _punct('='), Ref(rn.EXPRESSION), action=_field),
            Seq(Ref(rn.EXPRESSION), action=_unlabeled_field),
        ),
        _punct(','),
        trailing=True,
    ),
    _punct('}'),
    action=...,
),
```

```python
def _unlabeled_field(c):
    return terms.Field(label='', value=c.values[0], location=_location(c))
```

| Source | Fields |
|---|---|
| `{'1', '2'}` | `('', '1')`, `('', '2')` |
| `{a}` | `('', a)` |
| `{a = b}` | `('a', b)` |
| `{x -> x}` | `('', x -> x)`: `x` then `->` is not `x =` |
| `{'1', b = '2'}` | `('', '1')`, `('b', '2')` |

**Printer.** A field with label `''` prints only its value, in all three modes
(`_compact`, `_flat`, `_pretty`). Today `_name('')` would fail on `name[0]`, so the field
text goes through one helper that checks for `''` first.

**BANF (decision 13).**

- `banf_translate`:
  - `_check_data_form` and the struct case of `op` skip `''` when looking for duplicate
    labels.
  - An unlabeled field is an error in the module form (`_declarations`), the module body
    (`convert`), the blocks (`_blocks`), a block's param form, a signature's param form,
    and the argument struct of a call, a jump or a prim (`args`):
    `'This struct needs a label on every field.'`.
- `banf_terms`: `show_form` and `show_op` print an unlabeled field as its form or atom
  only.
- `llvm_translate`: `MakeStruct` names an unlabeled field's value `{let}.{index}`
  instead of `{let}.{label}`. Each `insertvalue` gets the name of the field it inserts:

  ```llvm
  ; let p = {x = a, y = b}            (today)
  %"p.x" = insertvalue {i32, i8} undef, i32 %"a", 0
  %"p.y" = insertvalue {i32, i8} %"p.x", i8 %"b", 1

  ; let q = {a, b}                    (with {let}.{label}: "q." and llvmlite's "q..1")
  %"q.0" = insertvalue {i32, i8} undef, i32 %"a", 0
  %"q.1" = insertvalue {i32, i8} %"q.0", i8 %"b", 1

  ; let r = {a, y = b}                (mixed)
  %"r.0" = insertvalue {i32, i8} undef, i32 %"a", 0
  %"r.y" = insertvalue {i32, i8} %"r.0", i8 %"b", 1
  ```

  The names only make the IR readable; LLVM doesn't use them.

### B. Reduction rule

One new case in `bruijn.reduce`, next to projection, and a helper that reads an index:

```python
case terms.Apply(function=terms.Struct(fields=fields), argument=argument) if (
    (position := index_value(argument)) is not None and position < len(fields)
):
    return fields[position].value
```

```python
def index_value(term: syntax.Term) -> int | None:
    """The index a byte array spells, unsigned little-endian. A form on it is ignored.

    None for `''` and for anything that is not a (formed) byte array.
    """
    match term:
        case terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)) if value:
            return int.from_bytes(value, 'little')
    return None
```

- It still holds that at most one rule applies to a term: beta needs a `Lambda` callee,
  this rule a `Struct` callee.
- Before this plan, an apply of a struct was never a redex, and nothing gave it a meaning
  (BANF has no such shape). So no existing program changes meaning.
- A long index such as `[ffffffffffffffffff]` is just a large number past the last field:
  stuck, with no overflow.
- `bruijn.project` doesn't change: it already picks the first field with the label, and
  no `Project` label is `''`.

### C. Heads in `banf_reduce`

`bruijn.reduce` only looks at the root, so `{a = x} ((y -> y) [00])` is not a redex until
the argument is reduced. The argument becomes the head of an apply **once its callee is a
struct**:

| Term | Head |
|---|---|
| `Apply(f, a)`, `f` not a `Struct` | `f` (as today) |
| `Apply(Struct, a)` | `a` |
| `Project(s, l)` | `s` (as today) |
| `If(c, t, e)` | `c` (as today) |
| `Formed(t, F)` | `t` (as today) |

```python
def _head(term):
    match term:
        case terms.Apply(function=terms.Struct(), argument=head):
            return head
        case terms.Apply(function=head) | terms.Project(struct=head) | ...:
            return head
    return None
```

`_with_head` mirrors it: for an apply with a struct callee, the new head replaces the
argument.

So `step` first reduces the callee to a struct, then the index to a byte array, then the
root fires. An argument is reduced only when the callee is already a struct, so ordinary
applications stay lazy (`f ((x -> x) a)` doesn't touch the argument). Each step still
costs fuel, and an index that never becomes a byte array leaves the apply stuck.

### D. `prim.extractvalue`

**Source.** An ordinary prim call, so `banf_reduce` already shapes it: `op_arg` reduces
the argument struct to atoms.

```
prim -> module: {first => 'i32'} -> {
  first = blocks -> {entry = args: {p = {'i32', 'i32'}} ->
    let x = prim.extractvalue {struct = args.p, index = [00]: 'i8'} in x}}
```

**`banf_prim`: a second kind of prim.** `PrimSignature` doesn't change. Prims whose
result form depends on their arguments get their own class and their own table:

```python
class PrimFormError(Exception):
    """A dynamic prim's arguments don't fit it. `banf_terms` turns it into a FormError."""


@dataclass(frozen=True)
class DynamicPrim:
    """A prim with no fixed signature: its result form depends on its arguments.

    `result_form` gets each argument's form and, for a constant, its bytes (None for a
    name). It returns the result form, or raises PrimFormError.
    """

    name: str
    labels: tuple[str, ...]
    result_form: Callable[[list[terms.Term], list[bytes | None]], terms.Term]


def _extractvalue_form(forms, values):
    struct_form, index_form = forms
    _, index = values
    if not isinstance(struct_form, terms.Struct):
        raise PrimFormError('prim.extractvalue: struct must have a struct form.')
    if index is None or not index:
        raise PrimFormError("prim.extractvalue needs a literal index, such as [00]: 'i8'.")
    if not (isinstance(index_form, terms.ByteArray) and index_form.as_str in INT_FORMS):
        raise PrimFormError('prim.extractvalue: the index form must be one of i1, ..., i64.')
    position = int.from_bytes(index, 'little')
    if position >= len(struct_form.fields):
        raise PrimFormError(f'prim.extractvalue: the struct has no field at index {position}.')
    return struct_form.fields[position].value


DYNAMIC_PRIMS: dict[str, DynamicPrim] = {
    prim.name: prim for prim in (DynamicPrim('extractvalue', ('struct', 'index'), _extractvalue_form),)
}
```

`banf_prim` only imports `terms`, so it reads the index with `int.from_bytes` itself, the
same rule as `bruijn.index_value` (decision 5). A name in `PRIMS` is never in
`DYNAMIC_PRIMS`.

**BANF term.** None: it stays a `PrimCall('extractvalue', [struct, index])`. It prints with
today's `show_op` as `prim.extractvalue(p, [00]:i8)`.

**`banf_translate.op`.** The prim case looks in both tables. For a dynamic prim only
the labels are checked here, by today's `args`:

```python
if base == PRIM:
    if name in banf_prim.PRIMS:
        params = banf_prim.PRIMS[name].params
    elif name in banf_prim.DYNAMIC_PRIMS:
        params = [(label, terms.Empty) for label in banf_prim.DYNAMIC_PRIMS[name].labels]
    else:
        raise TranslationError(f'Unknown prim op {name!r}.', location)
    return banf.PrimCall(name, self.args(arg, params, f'prim.{name}', block), location)
```

The rest (`struct` is a struct, `index` is a literal of an int form, in range) is checked
by `result_form` when `convert` calls `banf.verify`, and reported as a `TranslationError`
as every `FormError` is.

**`banf_terms`.**

- `form_of(PrimCall)`: for a dynamic prim, call `result_form` with the arguments' forms
  and the bytes of each `Const` (None for a `Var`); a `PrimFormError` becomes a
  `FormError` at the op's location.
- `_check_op(PrimCall)`: for a dynamic prim, check the argument count against `labels`,
  then call `form_of`.

**`llvm_prims`.** One more entry in `DEFAULT_PRIMS`. The index arrives as the
`ir.Constant` that `_const` built, so its Python int is `.constant`:

```python
DEFAULT_PRIMS['extractvalue'] = lambda builder, args: builder.extract_value(args[0], args[1].constant)
```

`llvm_translate` doesn't change: it already calls `target.prims[name]` for every
`PrimCall`. As for any constant, the index's bytes must fit its form exactly in LLVM:
`[00]: 'i8'`, or `[00000000]: 'i32'`.

### E. What doesn't change

| Module | Why |
|---|---|
| `terms.py`, `rule_names.py` | `Field.label` is already a `str`; no new term or rule |
| `banf_rename.py` | `Apply` is already walked |
| `PrimSignature`, `PRIMS` | `extractvalue` is a `DynamicPrim`, in its own table |
| `banf_terms.Op` | `prim.extractvalue` is a `PrimCall` |
| golden files | they use no struct apply, no unlabeled field and no `prim.extractvalue` |

### Precedence

Nothing new: a struct apply is an application.

| Source | Means |
|---|---|
| `{a = '23'} [00]` | `({a = '23'}) [00]` |
| `s.t [00]` | `(s.t) [00]` |
| `s [00] [01]` | `(s [00]) [01]`: a nested struct, then its field |
| `f s [00]` | `(f s) [00]`; write `f (s [00])` to pass the field |
| `s [00] : t` | `s ([00] : t)`, which decision 8 reads as `s [00]`; write `(s [00]) : t` for a form on the field |

---

## Affected modules

| Module | Change |
|---|---|
| `grammar.py` | an unlabeled field (A) |
| `printer.py` | an unlabeled field prints only its value (A) |
| `bruijn.py` | `index_value` and the struct apply case in `reduce` (B) |
| `banf_reduce.py` | `_head` / `_with_head`: the argument of a struct apply (C) |
| `banf_prim.py` | `PrimFormError`, `DynamicPrim`, `DYNAMIC_PRIMS` with `extractvalue` (D) |
| `banf_translate.py` | unlabeled fields (A); the prim case looks in `DYNAMIC_PRIMS` too (D) |
| `banf_terms.py` | unlabeled fields in the printer (A); `form_of` and `_check_op` for a dynamic prim (D) |
| `llvm_prims.py` | `extractvalue` in `DEFAULT_PRIMS` (D) |
| `llvm_translate.py` | unlabeled field names (A) |
| `docs/notes.md` | "Kernel syntax decisions": optional labels, duplicates and `Project` picking the first, `s [00]` next to `s.x`; "`reduce`" gets the rule; "Heads" gets the new head; the BANF prims get dynamic prims and `prim.extractvalue`; the LLVM section gets `extractvalue` |

---

## Open questions

None.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: a struct field's label is optional

- `grammar.py`: `_unlabeled_field` and the `STRUCT` rule (A).
- `printer.py`: the field helper, used by all three modes (A).
- `banf_translate.py`, `banf_terms.py`, `llvm_translate.py`: unlabeled fields (A).
- Tests:
  - Grammar: each row of the table in A; `{}` is still an empty struct; `{"" = x}` is an
    error; a trailing comma after an unlabeled field.
  - Printer: round trips of `{'1', '2'}`, `{'1', b = '2'}`, `{a}`, and a broken pretty
    struct with unlabeled fields.
  - `reduce`: `{a = '1', a = '2'}.a` → `'1'` (decision 2, today's behavior, now tested);
    `{'1'}.a` is stuck.
  - BANF: a let-bound `{[01]: 'i32', [02]: 'i32'}` translates, and its form prints as
    `{i32, i32}`. An unlabeled field in a block's param form, a declaration, a call's
    argument and a prim's argument is rejected with the new message.
- `docs/notes.md`: optional labels and duplicates in "Kernel syntax decisions"; unlabeled
  fields in the BANF section.

Commit: `oymomo: a struct field's label is optional`

### Step 2: the struct apply rule in `bruijn.reduce`

- `bruijn.py`: `index_value` and the `reduce` case (B).
- Tests in `bruijn_test.py`, each on `reduce` of a resolved term:
  - `{a = '23'} [00]` → `'23'`; `{a = '23', b = '45'} [01]` → `'45'`.
  - Unlabeled fields: `{'1', '2'} [01]` → `'2'`; `{'1', b = '2'} [00]` → `'1'`.
  - Duplicate labels: `{a = '1', a = '2'} [01]` → `'2'`.
  - Longer spellings: `{a = '23', b = '45'} [0100]` → `'45'`; `{a = '23'} [0000]` → `'23'`.
  - A formed index: `{a = '23'} ([00] : 'i8')` → `'23'`.
  - Stuck (`reduce(t) is t`): `{a = '23'} [01]`, `{a = '23'} [0001]`, `{a = '23'} ''`,
    `{} [00]`, `{a = '23'} $0` under a binder, and `{a = '23'} ((x -> x) [00])` (the root only).
  - `index_value`: `[01]` → 1, `[0001]` → 256, `''` → None, `$0` → None.
- `docs/notes.md`: the rule in the `reduce` list, and `s [00]` in "Kernel syntax decisions".

Commit: `oymomo: a struct applied to an index selects the field`

### Step 3: `banf_reduce` reduces a struct apply's index

- `banf_reduce.py`: `_head` and `_with_head` (C).
- Tests in `banf_reduce_test.py`, on `whnf`:
  - The goal: `(i -> {a = '23', b = '45'} i) [01]` → `'45'`.
  - A computed callee and index: `{p = {a = '23'}}.p ((x -> x) [00])` → `'23'`.
  - Nested: `{{'1'}} [00] [00]` → `'1'`.
  - A struct of functions called by index: `(s -> s [01] '7') {x -> '1', x -> x}` → `'7'`.
  - Stuck and unchanged: `{a = '23'} [01]`.
  - Still lazy: in `f ((x -> x) [00])` under a binder `f`, the argument is not reduced.
- Tests in `banf_translate_test.py`:
  - A block returning `{args.n} [00]` translates like one returning `args.n`.
  - Rejected with today's messages (decision 10): `args [00]`, `blocks [01] {...}`,
    `module [00] {...}`, `prim [00] {...}`.
- `docs/notes.md`: the new head in "Heads".

Commit: `oymomo: banf_reduce reduces a struct apply's index`

### Step 4: `prim.extractvalue`

- `banf_prim.py`: `PrimFormError`, `DynamicPrim`, `_extractvalue_form`, `DYNAMIC_PRIMS` (D).
- `banf_terms.py`: `form_of` and `_check_op` for a dynamic prim (D).
- `banf_translate.py`: the prim case looks in `DYNAMIC_PRIMS` too (D).
- `llvm_prims.py`: `extractvalue` in `DEFAULT_PRIMS` (D).
- Tests:
  - `banf_prim_test.py`: `PRIMS` and `DYNAMIC_PRIMS` share no name; `_extractvalue_form`
    on `{x: i32, y: i8}` with index `[01]` is `i8`; each `PrimFormError` (not a struct, a
    name as index, `''`, a non-int index form, index 2).
  - `banf_terms_test.py`: `form_of(PrimCall('extractvalue', [Var('p'), Const(b'\x01', 'i8')]))`
    is `i8`; a `PrimFormError` becomes a `FormError` with the op's location; a wrong
    argument count; `show_op` prints `prim.extractvalue(p, [01]:i8)`.
  - `banf_translate_test.py`: the example in D, on a labeled and on an unlabeled param
    struct; `prim.extractvalue` on a let-bound struct; wrong labels
    (`prim.extractvalue takes {struct, index}, got {...}.`); each `result_form` error, as
    a `TranslationError`.
  - `llvm_translate_test.py`: `prim.extractvalue` with index `[00]: 'i8'` gives the same
    `extractvalue` as `args.p.x`; index `[00]: 'i32'` is rejected (`A i32 constant needs 4 bytes.`).
- `docs/notes.md`: dynamic prims and `prim.extractvalue` in the BANF and LLVM sections.
- Status of this plan: **implemented**.

Commit: `oymomo: add prim.extractvalue`

---

## Verification

After every step:

```
hatch run full-check
```

The final checks are the goals:

```python
def test_dynamic_index():
    term = bruijn.resolve(parse("(i -> {a = '23', b = '45'} i) [01]"))
    assert banf_reduce.whnf(term) == parse("'45'")


def test_prim_extractvalue():
    # A block reading `prim.extractvalue {struct = args.p, index = [01]: 'i8'}` on
    # `p = {'i32', 'i8'}` translates to a PrimCall of form i8, and to an extractvalue.
    ...
```
