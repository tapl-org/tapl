# Plan: `$unpack` and `$pack`, a struct to a list of fields and back

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. `$unpack s`: a struct to a list of fields (`oymomo: add $unpack`)
- [ ] 2. `$pack l`: a list of fields to a struct (`oymomo: add $pack`)

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
$pack ($unpack {a = '1', b = '2'})                                  ⇒   {a = '1', b = '2'}
(l -> v -> $pack {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'
                                                                    ⇒   {a = '23'}
```

## Decisions

1. **Two built-ins: `$unpack s` and `$pack l`.** Each is one entry in
   `bruijn.BUILTIN_RULES`: a `BuiltinRule` with a rule and no opcode, so both are
   kernel-only (plan_builtin decision 10). Both are strict: a rule reads its argument,
   which must be reduced first. `needs` is `'a struct'` for `$unpack` and `'a list of
   fields'` for `$pack`, so a leftover one is reported as
   `$unpack has no opcode, so it must reduce away: its argument must reduce to a struct.`
   Nothing is reserved: `pack` and `unpack` stay plain names.
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
3. **A label is the UTF-8 bytes of the field's name.** `$unpack`
   encodes each label; `$pack` decodes it.
4. **Lazy values.** Neither built-in reduces a field value. `$unpack {a = (x -> x) y}`
   keeps `(x -> x) y` in the `value` field.
5. **Order is kept.** Field order matters for layout (notes: "Struct, not record"), so
   `$unpack` lists the fields in order and `$pack` builds them in list order.
6. **A malformed input is stuck, not an error**, as for projection: the rule returns
   None. `$unpack` is stuck on anything but a struct literal. `$pack` is stuck unless every
   node is a struct with `more = [00]`, or with `more = [01]` and `label`, `value` and
   `rest` fields, where the label's bytes are valid UTF-8; `''` gives an unlabeled field.
   Extra fields in a node are ignored. Duplicate labels are kept, as a struct literal may
   have them.
7. **BANF shape rules decide what BANF accepts.** `$pack` and `$unpack` must reduce away
   in `banf_reduce.shape`. A stuck one reaches `convert`, which rejects it with the
   message of decision 1, as for any kernel-only built-in.

---

## Design

### A. Syntax

None: both are written as built-ins, `$pack l` and `$unpack s`, and apply like any
function (plan_builtin decision 13).

| Source | Means |
|---|---|
| `$pack l x` | `($pack l) x` |
| `$unpack s.a` | `$unpack (s.a)` |
| `$pack l : t` | `$pack (l : t)` (stuck: a formed list isn't a list); write `($pack l) : t` |
| `f $pack l` | `(f $pack) l`; write `f ($pack l)` |

### B. Rules in `bruijn.BUILTIN_RULES`

Both are root-only, like the other rules.

- **unpack**: `$unpack {l1 = e1, …, ln = en}` gives
  `{more = [01], label = 'l1', value = e1, rest = … {more = [00]}}`. The labels are bare
  byte arrays (no form).
- **pack**: `$pack L` gives `{l1 = e1, …, ln = en}` when `L` is a *literal list*: each node
  is a `Struct` whose `more` is a byte array `[00]` or `[01]`, and for `[01]` whose `label`
  is a byte array of valid UTF-8 and whose `rest` is again a literal list. A `Formed`
  around `more` or `label` is seen through, as an `if` condition is. Otherwise not a redex.

```python
BuiltinRule('unpack', strict=True, needs='a struct', rule=_unpack)
BuiltinRule('pack', strict=True, needs='a list of fields', rule=_pack)
```

The rules never reduce inside: `_pack` only checks that the list is already literal.
The helpers are `unpack_fields(struct)` and `pack_fields(list)` (None when not literal).

### C. `banf_reduce`

- **`$unpack`'s argument is its head**, since the rule is strict (plan_builtin step 4):
  `$unpack ({p = {a = x}}.p)` reduces the projection, then the rule fires. No change in
  `banf_reduce`.
- **`$pack` needs its spine, not just its argument.** `$pack` fires only on a literal list,
  but `strict` only takes the argument to whnf. So `step` on `$pack L` must also reduce the
  list's spine: `whnf` of the list, then of its `more`, and for `[01]` of its `label` and
  `rest`, again and again. Values are left alone (decision 4):
  ```
  spine(L) = whnf(L), with more ↦ whnf(more), and if more is [01]:
             label ↦ whnf(label), rest ↦ spine(rest)
  ```
  A list that never ends (built with `$fix`) runs out of fuel with today's error. How the
  rule tells `banf_reduce` that it needs the spine is open question 4.

### D. Other modules

| Module | Change |
|---|---|
| `bruijn.py` | `unpack_fields`, `pack_fields`, the two `BUILTIN_RULES` entries (B) |
| `banf_reduce.py` | `$pack`'s spine (C, open question 4) |
| `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`, `banf_rename.py` | none: a `Builtin` is a leaf, already parsed and printed |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | none (decision 7) |
| `docs/notes.md` | the built-ins table, the rules in "`reduce`", the spine in "`banf_reduce`" |

### Example: mapping a struct's fields

```
let map = $fix (map -> f -> l ->
  if l.more then {more = [01], label = l.label, value = f l.value, rest = map f l.rest}
  else l)
in $pack (map g ($unpack {a = x, b = y}))
⇒ {a = g x, b = g y}
```

---

## Breaking changes

None: no word becomes reserved, and no term changes.

---

## Open questions

> [!IMPORTANT]
> 1. **Names.** `$pack` / `$unpack` are short verbs like `$fix`. Alternatives: `$fields` /
>    `$struct`, `$explode` / `$implode`, `$to_list` / `$from_list`. As built-ins, none of
>    them reserves a word.
> 2. **Node labels.** `more`, `label`, `value`, `rest`. Alternatives: `head` / `tail`
>    with entries `{label, value}` (two levels per field), or a `tag` instead of `more`.
> 3. **Invalid labels in `$pack`** (bytes that aren't UTF-8) are stuck (decision 6). Should
>    they be allowed, since a struct built by `$pack` never goes through the parser? An empty
>    label is valid: it is an unlabeled field (plan_struct_apply decision 1).
> 4. **How `$pack` asks for its spine.** `BuiltinRule.strict` only reduces the argument.
>    [plan_constant_folding.md](plan_constant_folding.md) turns it into a `Strictness`
>    with a `FIELDS` value; `$pack` needs more (the spine). Options: a `SPINE` value that
>    `banf_reduce` knows; or a rule-supplied function giving the positions it reads, so
>    `banf_reduce` stays generic. Until then, adding `$pack` changes `banf_reduce`, so
>    plan_builtin's "two table entries, no other module" holds only for `$unpack`.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: `$unpack s`

- `bruijn.py`: `unpack_fields`, the `BUILTIN_RULES` entry.
- Tests:
  - `reduce`: `$unpack {}` → `{more = [00]}`; `$unpack {a = '1', "λ" = x}` → the list with
    labels `'a'` and `[cebb]`, in order; `$unpack $0` is stuck.
  - `whnf`: `$unpack ({p = {a = x}}.p)` reduces; a value stays unreduced.
  - `banf_translate`: `let t = $unpack args.p in t` gives
    `$unpack has no opcode, so it must reduce away: its argument must reduce to a struct.`

Commit: `oymomo: add $unpack`

### Step 2: `$pack l`

- `bruijn.py`: `pack_fields`, the `BUILTIN_RULES` entry.
- `banf_reduce.py`: the spine (C), as decided by open question 4.
- Tests:
  - `reduce`: `$pack {more = [00]}` → `{}`; a two-field list → the struct, in order;
    duplicates kept; a label `''` gives an unlabeled field. Stuck: a missing `more`,
    `more = [02]`, a label `[ff]`, a `rest` that isn't reduced yet (root only).
  - `whnf`: the goal example with a computed label; a `rest` and a `label` that need
    reducing; the `map` example; `$pack ($fix (l -> {more = [01], label = 'a', value = x, rest = l}))`
    runs out of fuel.
  - Round trips: `$pack ($unpack s)` gives `s`; `$unpack ($pack l)` gives `l` for a list
    with bare labels.
- Status of this plan: **implemented**.

Commit: `oymomo: add $pack`

---

## Verification

After every step:

```
hatch run full-check
```

The final check is the goal, as a term comparison:

```python
def test_dynamic_struct():
    source = "(l -> v -> $pack {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'"
    assert banf_reduce.whnf(bruijn.resolve(parse(source))) == parse("{a = '23'}")
```
