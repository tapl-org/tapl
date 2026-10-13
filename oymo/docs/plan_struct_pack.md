# Plan: `$struct_to_fields` and `$fields_to_struct`, a struct to a list of fields and back

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. `$struct_to_fields s`: a struct to a list of fields (`oymomo: add $struct_to_fields`)
- [ ] 2. `$fields_to_struct l`: a list of fields to a struct (`oymomo: add $fields_to_struct`)

Step 2 uses step 1 in its round-trip tests. Built on [plan_builtin.md](plan_builtin.md):
both are built-ins, so each is an entry in `bruijn.BUILTIN_RULES`, with no new term, no
grammar rule and no reserved word.

## Goal

**Users can build a struct dynamically**: computed labels, a computed number of fields,
and fields mapped or filtered by oymomo code.

Every other term is already built from expressions, except for names and literal data:

| Term | Built dynamically today? |
|---|---|
| `Apply`, `If`, `Formed`, `FunctionForm` | yes: every part is a term |
| `Lambda` | yes: the form and the body are terms. The param name is only a binder name |
| `Project` | no: the label is a name. `s i` picks a field by a computed index, not label |
| `ByteArray` | no: its bytes are literal. Computing bytes needs opcodes ([plan_constant_folding.md](plan_constant_folding.md)) |
| **`Struct`** | **no**: the field list is fixed by the syntax, labels and count both |

```
$fields_to_struct ($struct_to_fields {a = '1', b = '2'})            ⇒   {a = '1', b = '2'}
(l -> v -> $fields_to_struct {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'
                                                                    ⇒   {a = '23'}
```

## Decisions

1. **Two built-ins: `$struct_to_fields s` and `$fields_to_struct l`.** Each is one entry in
   `bruijn.BUILTIN_RULES`: a `BuiltinRule` with a rule and no opcode, so both are
   kernel-only (plan_builtin decision 10). Both are strict: a rule reads its argument,
   which must be reduced first. `needs` is `'a struct'` for `$struct_to_fields` and `'a list
   of fields'` for `$fields_to_struct`, so a leftover one is reported as
   `$struct_to_fields has no opcode, so it must reduce away: its argument must reduce to a struct.`
   Nothing is reserved: `struct_to_fields` and `fields_to_struct` stay plain names.

   The names say both sides of the conversion, so they read without knowing a
   convention, and the two mirror each other. Rejected:
   - `$pack` / `$unpack`: short, but they don't say what they work on, and elsewhere
     (Python's `struct.pack`, Perl's `pack`, LLVM's packed structs) they mean bytes, which
     misleads in a language with byte arrays and memory opcodes.
   - `$construct_struct` / `$deconstruct_struct`: exact opposites, but they don't name
     the other side (fields), and a struct literal also constructs a struct.
   - `$build_struct`, `$fields` / `$struct`, `$explode` / `$implode`, `$to_list` /
     `$from_list`: less clear about direction or about what they work on.
2. **A list of fields is made of structs with fixed labels.** The kernel has no lists,
   and the labels below are static, so users build and read these nodes with today's
   syntax:
   ```
   nil  = {more = [00]}
   cons = {more = [01], label = 'a', value = e, rest = <list>}
   ```
   `more` is a one-byte boolean, so code walks a list with an ordinary
   `if l.more then … else …`. Rejected: Scott or Church lists (`c -> n -> …`). A rule that
   needs to see a list's nodes can't look inside a lambda, and an `if` can't branch on
   one.
3. **A label is the UTF-8 bytes of the field's name.** `$struct_to_fields`
   encodes each label; `$fields_to_struct` decodes it.
4. **Lazy values.** Neither built-in reduces a field value. `$struct_to_fields {a = (x -> x) y}`
   keeps `(x -> x) y` in the `value` field.
5. **Order is kept.** Field order matters for layout (notes: "Struct, not record"), so
   `$struct_to_fields` lists the fields in order and `$fields_to_struct` builds them in
   list order.
6. **A malformed input is stuck, not an error**, as for projection: the rule returns
   None. `$struct_to_fields` is stuck on anything but a struct literal. `$fields_to_struct`
   is stuck unless every node is a struct with `more = [00]`, or with `more = [01]` and
   `label`, `value` and `rest` fields, where the label's bytes are valid UTF-8; `''` gives
   an unlabeled field. Extra fields in a node are ignored. Duplicate labels are kept, as a
   struct literal may have them.
7. **BANF shape rules decide what BANF accepts.** `$fields_to_struct` and
   `$struct_to_fields` must reduce away in `banf_reduce.shape`. A stuck one reaches
   `convert`, which rejects it with the message of decision 1, as for any kernel-only
   built-in.

---

## Design

### A. Syntax

None: both are written as built-ins, `$fields_to_struct l` and `$struct_to_fields s`, and
apply like any function (plan_builtin decision 13).

| Source | Means |
|---|---|
| `$fields_to_struct l x` | `($fields_to_struct l) x` |
| `$struct_to_fields s.a` | `$struct_to_fields (s.a)` |
| `$fields_to_struct l : t` | `$fields_to_struct (l : t)` (stuck: a formed list isn't a list); write `($fields_to_struct l) : t` |
| `f $fields_to_struct l` | `(f $fields_to_struct) l`; write `f ($fields_to_struct l)` |

### B. Rules in `bruijn.BUILTIN_RULES`

Both are root-only, like the other rules.

- **struct_to_fields**: `$struct_to_fields {l1 = e1, …, ln = en}` gives
  `{more = [01], label = 'l1', value = e1, rest = … {more = [00]}}`. The labels are bare
  byte arrays (no form).
- **fields_to_struct**: `$fields_to_struct L` gives `{l1 = e1, …, ln = en}` when `L` is a
  *literal list*: each node is a `Struct` whose `more` is a byte array `[00]` or `[01]`,
  and for `[01]` whose `label` is a byte array of valid UTF-8 and whose `rest` is again a
  literal list. A `Formed` around `more` or `label` is seen through, as an `if` condition
  is. Otherwise not a redex.

```python
BuiltinRule('struct_to_fields', strict=True, needs='a struct', rule=_struct_to_fields)
BuiltinRule('fields_to_struct', strict=True, needs='a list of fields', rule=_fields_to_struct)
```

The rules never reduce inside: `_fields_to_struct` only checks that the list is already
literal. The helpers are `to_field_list(struct)` and `from_field_list(list)` (None when
not literal).

### C. `banf_reduce`

- **`$struct_to_fields`'s argument is its head**, since the rule is strict (plan_builtin
  step 4): `$struct_to_fields ({p = {a = x}}.p)` reduces the projection, then the rule
  fires. No change in `banf_reduce`.
- **`$fields_to_struct` needs its spine, not just its argument.** `$fields_to_struct` fires
  only on a literal list, but `strict` only takes the argument to whnf. So `step` on
  `$fields_to_struct L` must also reduce the list's spine: `whnf` of the list, then of its
  `more`, and for `[01]` of its `label` and `rest`, again and again. Values are left alone
  (decision 4):
  ```
  spine(L) = whnf(L), with more ↦ whnf(more), and if more is [01]:
             label ↦ whnf(label), rest ↦ spine(rest)
  ```
  A list that never ends (built with `$fix`) runs out of fuel with today's error. How the
  rule tells `banf_reduce` that it needs the spine is open question 3.

### D. Other modules

| Module | Change |
|---|---|
| `bruijn.py` | `to_field_list`, `from_field_list`, the two `BUILTIN_RULES` entries (B) |
| `banf_reduce.py` | `$fields_to_struct`'s spine (C, open question 3) |
| `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`, `banf_rename.py` | none: a `Builtin` is a leaf, already parsed and printed |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | none (decision 7) |
| `docs/notes.md` | the built-ins table, the rules in "`reduce`", the spine in "`banf_reduce`" |

### Example: mapping a struct's fields

```
let map = $fix (map -> f -> l ->
  if l.more then {more = [01], label = l.label, value = f l.value, rest = map f l.rest}
  else l)
in $fields_to_struct (map g ($struct_to_fields {a = x, b = y}))
⇒ {a = g x, b = g y}
```

---

## Breaking changes

None: no word becomes reserved, and no term changes.

---

## Open questions

> [!IMPORTANT]
> 1. **Node labels.** `more`, `label`, `value`, `rest`. Alternatives: `head` / `tail`
>    with entries `{label, value}` (two levels per field), or a `tag` instead of `more`.
> 2. **Invalid labels in `$fields_to_struct`** (bytes that aren't UTF-8) are stuck
>    (decision 6). Should they be allowed, since a struct built by `$fields_to_struct`
>    never goes through the parser? An empty label is valid: it is an unlabeled field
>    (plan_struct_apply decision 1).
> 3. **How `$fields_to_struct` asks for its spine.** `bruijn.reduce` is root-only, so
>    `banf_reduce` must put in whnf every position a rule reads before it fires.
>    [plan_constant_folding.md](plan_constant_folding.md) (decision 8) makes `strict` a
>    `Strictness` of `NONE`, `ARGUMENT`, `FIELDS`, and leaves the general case to this
>    plan. `$fields_to_struct` needs an unbounded, data-dependent shape: whether `rest` is
>    read depends on the value of `more`:
>    ```
>    $fields_to_struct {more = (x -> x) [01], label = l, value = v, rest = f {}}
>                       ^ whnf first, then: [01], so label and rest too; then rest.more, ...
>    ```
>    *Option A: a fourth value, `SPINE`.* `banf_reduce` gets a case for it, which knows
>    the node labels (`more`, `label`, `rest`).
>    - Simple; each shape is visible in one table.
>    - Every new shape changes `banf_reduce`, so plan_builtin's "two table entries, no
>      other module" holds only for shapes that exist; the node labels are written in
>      two modules.
>
>    *Option B: the rule lists the positions it reads.* `Strictness` is replaced by
>    `reads(argument) -> Iterator[Path]`, a `Path` being field indices from the argument
>    (`()` is the argument, `(1, 0)` is field 0 of field 1). It is called on the argument
>    as reduced so far, so it can stop or go on by what it sees; `step` whnf's the first
>    yielded position that `whnf` changes.
>    ```python
>    def reads_nothing(argument):          # $fix
>        return iter(())
>
>    def reads_argument(argument):         # $struct_to_fields
>        yield ()
>
>    def reads_fields(argument):           # opcodes
>        yield ()
>        if isinstance(argument, terms.Struct):
>            yield from ((i,) for i in range(len(argument.fields)))
>
>    def reads_spine(argument, path=()):   # $fields_to_struct, next to _fields_to_struct
>        yield path
>        node = at(argument, path)
>        if isinstance(node, terms.Struct) and (more := index_of(node, 'more')) is not None:
>            yield path + (more,)
>            if index_value(node.fields[more].value) == 1:
>                yield path + (index_of(node, 'label'),)
>                yield from reads_spine(argument, path + (index_of(node, 'rest'),))
>    ```
>    - `banf_reduce` gets one generic case and never changes for a new built-in; a
>      rule's reading shape sits next to the rule.
>    - More machinery; re-walking from the root each step is O(n²) for an n-node list,
>      fine at today's sizes. Replaces constant folding's `Strictness`.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: `$struct_to_fields s`

- `bruijn.py`: `to_field_list`, the `BUILTIN_RULES` entry.
- Tests:
  - `reduce`: `$struct_to_fields {}` → `{more = [00]}`; `$struct_to_fields {a = '1', "λ" = x}`
    → the list with labels `'a'` and `[cebb]`, in order; `$struct_to_fields $0` is stuck.
  - `whnf`: `$struct_to_fields ({p = {a = x}}.p)` reduces; a value stays unreduced.
  - `banf_translate`: `let t = $struct_to_fields args.p in t` gives
    `$struct_to_fields has no opcode, so it must reduce away: its argument must reduce to a struct.`

Commit: `oymomo: add $struct_to_fields`

### Step 2: `$fields_to_struct l`

- `bruijn.py`: `from_field_list`, the `BUILTIN_RULES` entry.
- `banf_reduce.py`: the spine (C), as decided by open question 3.
- Tests:
  - `reduce`: `$fields_to_struct {more = [00]}` → `{}`; a two-field list → the struct, in
    order; duplicates kept; a label `''` gives an unlabeled field. Stuck: a missing
    `more`, `more = [02]`, a label `[ff]`, a `rest` that isn't reduced yet (root only).
  - `whnf`: the goal example with a computed label; a `rest` and a `label` that need
    reducing; the `map` example;
    `$fields_to_struct ($fix (l -> {more = [01], label = 'a', value = x, rest = l}))`
    runs out of fuel.
  - Round trips: `$fields_to_struct ($struct_to_fields s)` gives `s`;
    `$struct_to_fields ($fields_to_struct l)` gives `l` for a list with bare labels.
- Status of this plan: **implemented**.

Commit: `oymomo: add $fields_to_struct`

---

## Verification

After every step:

```
hatch run full-check
```

The final check is the goal, as a term comparison:

```python
def test_dynamic_struct():
    source = "(l -> v -> $fields_to_struct {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'"
    assert banf_reduce.whnf(bruijn.resolve(parse(source))) == parse("{a = '23'}")
```
