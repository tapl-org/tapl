# Plan: `unpack` and `pack`, a struct to a list of fields and back

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. `unpack s`: a struct to a list of fields (`oymomo: add unpack`)
- [ ] 2. `pack l`: a list of fields to a struct (`oymomo: add pack`)

Step 2 uses step 1 in its round-trip tests. Neither depends on
[plan_struct_apply.md](plan_struct_apply.md).

## Goal

**Users can build a struct dynamically**: computed labels, a computed number of fields,
and fields mapped or filtered by oymomo code.

Every other term is already built from expressions, except for names and literal data:

| Term | Built dynamically today? |
|---|---|
| `Apply`, `If`, `Fix`, `Formed`, `FunctionForm` | yes: every part is a term |
| `Lambda` | yes: the form and the body are terms. The param name is only a binder name |
| `Project` | yes, once struct apply lands: `s l` picks a computed label |
| `ByteArray` | no: its bytes are literal. Computing bytes needs prims (out of scope) |
| **`Struct`** | **no**: the field list is fixed by the syntax, labels and count both |

```
pack (unpack {a = '1', b = '2'})                                   ⇒   {a = '1', b = '2'}
(l -> v -> pack {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'
                                                                   ⇒   {a = '23'}
```

## Decisions

1. **Two built-ins written like `fix`: `unpack s` and `pack l`.** Each is a new term
   (`Unpack(struct)`, `Pack(list)`), named after its operation like `Apply`, `Project`
   and `Fix`. `pack` and `unpack` become reserved words; `"pack"` still works as a name.
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
3. **A label is the UTF-8 bytes of the field's name**, as in struct apply. `unpack`
   encodes each label; `pack` decodes it.
4. **Lazy values.** Neither built-in reduces a field value. `unpack {a = (x -> x) y}`
   keeps `(x -> x) y` in the `value` field.
5. **Order is kept.** Field order matters for layout (notes: "Struct, not record"), so
   `unpack` lists the fields in order and `pack` builds them in list order.
6. **A malformed input is stuck, not an error**, as for projection. `unpack` is stuck on
   anything but a struct literal. `pack` is stuck unless every node is a struct with
   `more = [00]`, or with `more = [01]` and `label`, `value` and `rest` fields, where the
   label's bytes are valid non-empty UTF-8. Extra fields in a node are ignored. Duplicate
   labels are kept, as a struct literal may have them.
7. **BANF shape rules decide what BANF accepts.** `pack` and `unpack` must reduce away
   in `banf_reduce.shape`. A stuck one is not a BANF shape, and `convert` rejects it.

---

## Design

### A. Syntax

`pack` and `unpack` sit at the `fix` level: `APPLY: APPLY FORMED | FIX | PACK | UNPACK | FORMED`.

```python
rn.PACK:   Seq('pack', FORMED),
rn.UNPACK: Seq('unpack', FORMED),
```

| Source | Means |
|---|---|
| `pack l x` | `(pack l) x` |
| `unpack s.a` | `unpack (s.a)` |
| `pack l : t` | `pack (l : t)` (stuck: a formed list isn't a list); write `(pack l) : t` |
| `f pack l` | error, as `f fix g`; write `f (pack l)` |

The printer prints both like `fix`: at `_APPLY`, with the operand at `_FORMED`.

### B. Terms

```python
@dataclass
class Unpack(Term):
    struct: Term
    location: Location | None = field(default=None, compare=False)


@dataclass
class Pack(Term):
    list: Term
    location: Location | None = field(default=None, compare=False)
```

### C. Reduction rules in `bruijn.reduce`

Both are root-only, like the other rules.

- **unpack**: `unpack {l1 = e1, …, ln = en}` gives
  `{more = [01], label = 'l1', value = e1, rest = … {more = [00]}}`. The labels are bare
  byte arrays (no form).
- **pack**: `pack L` gives `{l1 = e1, …, ln = en}` when `L` is a *literal list*: each node
  is a `Struct` whose `more` is a byte array `[00]` or `[01]`, and for `[01]` whose `label`
  is a byte array of valid UTF-8 and whose `rest` is again a literal list. A `Formed`
  around `more` or `label` is seen through, as an `if` condition is. Otherwise not a redex.

`bruijn.reduce` still never looks *inside* to reduce: it only checks that the list is
already literal. The new helpers are `unpack_fields(struct)` and `pack_fields(list)`
(None when not literal).

### D. `banf_reduce`

- **`Unpack`'s head is its struct.** `unpack ({p = {a = x}}.p)` reduces the projection,
  then the root fires.
- **`Pack` needs its spine, not just its head.** `pack` fires only on a literal list, so
  `step` on a `Pack` reduces the list's spine: `whnf` of the list, then of its `more`, and
  for `[01]` of its `label` and `rest`, again and again. Values are left alone
  (decision 4). This is a new kind of position, next to the head:
  ```
  spine(L) = whnf(L), with more ↦ whnf(more), and if more is [01]:
             label ↦ whnf(label), rest ↦ spine(rest)
  ```
  A list that never ends (built with `fix`) runs out of fuel with today's error.

### E. Other modules

| Module | Change |
|---|---|
| `terms.py` | `Unpack`, `Pack` |
| `rule_names.py` | `PACK`, `UNPACK` |
| `grammar.py` | the two rules (A); `pack` and `unpack` in `RESERVED` |
| `printer.py` | both like `fix` |
| `bruijn.py` | `_map_children`, `unpack_fields`, `pack_fields`, the two `reduce` cases |
| `banf_reduce.py` | `Unpack` head, `Pack` spine (D) |
| `banf_rename.py` | `other` walks into both |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | none (decision 7) |
| `docs/notes.md` | kernel syntax table, the rules in "`reduce`", the spine in "`banf_reduce`", reserved words |

### Example: mapping a struct's fields

```
let map = fix (map -> f -> l ->
  if l.more then {more = [01], label = l.label, value = f l.value, rest = map f l.rest}
  else l)
in pack (map g (unpack {a = x, b = y}))
⇒ {a = g x, b = g y}
```

---

## Breaking changes

> [!WARNING]
> `pack` and `unpack` become reserved words. A variable or label with either name must be
> quoted (`"pack"`). No golden source uses them.

---

## Open questions

> [!IMPORTANT]
> 1. **Names.** `pack` / `unpack` are short verbs like `fix`. Alternatives: `fields` /
>    `struct`, `explode` / `implode`, `to_list` / `from_list`. `struct` would reserve a
>    very common word.
> 2. **Node labels.** `more`, `label`, `value`, `rest`. Alternatives: `head` / `tail`
>    with entries `{label, value}` (two levels per field), or a `tag` instead of `more`.
> 3. **Empty or invalid labels in `pack`** are stuck (decision 6). Should they be allowed,
>    since a struct built by `pack` never goes through the parser?

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: `unpack s`

- `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`: the `Unpack` term and syntax.
- `bruijn.py`: `_map_children`, `unpack_fields`, the `reduce` case.
- `banf_reduce.py`: `Unpack`'s head. `banf_rename.py`: walk into it.
- Tests:
  - Grammar: `unpack s` parses; `unpack s.a` is `unpack (s.a)`; `f unpack s` is an error;
    `"unpack"` is a name. Printer round trip.
  - `reduce`: `unpack {}` → `{more = [00]}`; `unpack {a = '1', "λ" = x}` → the list with
    labels `'a'` and `[cebb]`, in order; `unpack $0` is stuck.
  - `whnf`: `unpack ({p = {a = x}}.p)` reduces; a value stays unreduced.

Commit: `oymomo: add unpack`

### Step 2: `pack l`

- `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`: the `Pack` term and syntax.
- `bruijn.py`: `_map_children`, `pack_fields`, the `reduce` case.
- `banf_reduce.py`: the spine (D). `banf_rename.py`: walk into it.
- Tests:
  - Grammar and printer, as for `unpack`.
  - `reduce`: `pack {more = [00]}` → `{}`; a two-field list → the struct, in order;
    duplicates kept. Stuck: a missing `more`, `more = [02]`, a label `[ff]`, a label `''`,
    a `rest` that isn't reduced yet (root only).
  - `whnf`: the goal example with a computed label; a `rest` and a `label` that need
    reducing; the `map` example; `pack (fix (l -> {more = [01], label = 'a', value = x, rest = l}))`
    runs out of fuel.
  - Round trips: `pack (unpack s)` gives `s`; `unpack (pack l)` gives `l` for a list with
    bare labels.
- Status of this plan: **implemented**.

Commit: `oymomo: add pack`

---

## Verification

After every step:

```
hatch run full-check
```

The final check is the goal, as a term comparison:

```python
def test_dynamic_struct():
    source = "(l -> v -> pack {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'"
    assert banf_reduce.whnf(bruijn.resolve(parse(source))) == parse("{a = '23'}")
```
