# Plan: `$struct_to_fields` and `$fields_to_struct`, a struct to a list of fields and back

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. A built-in rule lists its blockers (`oymomo: a built-in rule lists its blockers`)
- [ ] 2. `$struct_to_fields s`: a struct to a list of fields (`oymomo: add $struct_to_fields`)
- [ ] 3. `$fields_to_struct l`: a list of fields to a struct (`oymomo: add $fields_to_struct`)

Step 1 lets a rule read reduced parts of its argument. Step 3 uses step 2 in its round-trip
tests. Built on [plan_builtin.md](implemented/plan_builtin.md): both are built-ins, so each is an entry
in `bruijn.BUILTIN_RULES`, with no new term, no grammar rule and no reserved word.
[plan_constant_folding.md](plan_constant_folding.md) builds on step 1.

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
   kernel-only (plan_builtin decision 10). Both read their argument, so each lists what
   it reads as blockers (decision 8). `needs` is `'a struct'` for `$struct_to_fields` and
   `'a list of fields'` for `$fields_to_struct`, so a leftover one is reported as
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
   `$struct_to_fields` must reduce away in `banf_shape.shape`. A stuck one reaches
   `convert`, which rejects it with the message of decision 1, as for any kernel-only
   built-in.
8. **A rule lists its blockers as paths into its argument.** `bruijn.reduce` is
   root-only, and today `banf_shape` never reduces a built-in's argument (notes:
   "Blockers"). A rule that reads a reduced part of its argument says so with
   `blockers(argument) -> Iterable[Path]`, next to the rule. A `Path` is field positions
   from the argument: `()` is the argument, `(1, 0)` is field 0 of field 1.
   `banf_shape.unblock` reduces the first yielded blocker that
   `reduce_until_top_stable` changes, with one generic case for every built-in.

   `blockers` is called again on the argument as reduced so far, so a rule can choose
   what comes next by what it sees. `$fields_to_struct` needs this: whether `rest` is a
   blocker depends on the value of `more`:
   ```
   $fields_to_struct {more = (x -> x) [01], label = l, value = v, rest = f {}}
                      ^ reduced first, then: [01], so label and rest too; then rest.more, ...
   ```
   The contract, checked per rule by a test:
   1. **`rule` reads only blockers.** It looks at the top constructor of a yielded path,
      and under it only at paths that are yielded too.
   2. **None with every blocker reduced is final.** If `reduce_until_top_stable` changes
      no yielded blocker and `rule` returns None, no reduction elsewhere can make the
      call fire. So `banf_translate` can report `needs`.
   3. **Blockers only grow.** Reducing a blocker never takes back a path yielded before
      it; it can only add paths after it.

   Contract 1 also keeps reduction confluent: a rule never depends on a part that is
   still unreduced and might reduce differently later.

   Rejected: a fixed set of shapes in `banf_shape` (`NONE`, `ARGUMENT`, `FIELDS`, and a
   fourth, `SPINE`, for this plan). Each new shape would change `banf_shape`, and the node
   labels (`more`, `label`, `rest`) would be written in two modules. The cost of paths:
   `unblock` walks `blockers` from the root again at each step, O(n²) for an n-node
   list, which is fine at today's sizes.

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

### B. Blockers (step 1)

In `bruijn.py`:

```python
Path = tuple[int, ...]
"""Field positions from a built-in's argument: `()` is the argument, `(1, 0)` is field 0 of field 1."""


@dataclass(frozen=True)
class BuiltinRule:
    """How `reduce` steps `$name arg`.

    `blockers(arg)` yields the paths of `arg` that `rule` reads, outermost first.
    `banf_shape` reduces them, one at a time, before `rule` fires; it calls `blockers`
    again on the argument as reduced so far.

    `rule(call, arg)` gets the whole call and its argument, and returns the result, or
    None if the call doesn't reduce (yet). `needs` says what the argument must reduce to,
    for the error when it doesn't (`'a struct'`).
    """

    name: str
    blockers: Callable[[syntax.Term], Iterable[Path]]
    needs: str | None
    rule: Callable[[syntax.Term, syntax.Term], syntax.Term | None]


def at(term: syntax.Term, path: Path) -> syntax.Term | None:
    """The part of `term` at `path`, or None if a step isn't a struct or has no such field."""


def replace_at(term: syntax.Term, path: Path, part: syntax.Term) -> syntax.Term:
    """`term` with the part at `path` (which `at` found) replaced by `part`."""


def no_blockers(argument):          # $fix: g stays lazy
    return ()


def argument_blocker(argument):     # $struct_to_fields
    yield ()


def field_blockers(argument):       # opcodes (plan_constant_folding)
    yield ()
    if isinstance(argument, terms.Struct):
        yield from ((i,) for i in range(len(argument.fields)))
```

`at` doesn't look through `Formed`: no rule reads a struct under a form. `$fix` becomes
`BuiltinRule('fix', no_blockers, None, _fix)`.

In `banf_shape.py`, one case in `_Shaper.unblock`, before the generic apply:

```python
case terms.Apply(function=terms.Builtin(name=name), argument=argument) if (
    builtin := bruijn.BUILTIN_RULES.get(name)
) is not None:
    # A built-in's blockers are parts of its argument, as its rule lists them.
    for path in builtin.blockers(argument):
        part = bruijn.at(argument, path)
        if part is None:
            return term  # Not the shape the rule reads: stuck.
        new = self.reduce_until_top_stable(part)
        if new is not part:
            return replace(term, argument=bruijn.replace_at(argument, path, new))
    return term
```

- `unblock` returns after one change, and the next `step` calls `blockers` again, so a
  rule's choices need no state.
- A part that isn't yielded stays lazy, as `$fix`'s `g` does.
- Each reduction costs fuel, so a list that never ends (built with `$fix`) runs out of
  fuel with today's error.

| Built-in | `blockers` | `step` on it |
|---|---|---|
| `$fix g` | `no_blockers` | the rule fires right away |
| `$struct_to_fields ({p = s}.p)` | `argument_blocker` | `()` reduces to `s`, then the rule fires |
| `$add_i32 {a = (x -> x) [01..]: 'i32', b = …}` | `field_blockers` | `()`, then `(0,)`, then `(1,)`, then the fold |
| `$fields_to_struct L` | `spine_blockers` (C) | `()`, `(more,)`; if `[01]`: `(label,)`, then the spine of `rest`, … |

### C. Rules in `bruijn.BUILTIN_RULES` (steps 2 and 3)

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
BuiltinRule('struct_to_fields', argument_blocker, 'a struct', _struct_to_fields)
BuiltinRule('fields_to_struct', spine_blockers, 'a list of fields', _fields_to_struct)
```

The rules never reduce inside: `_fields_to_struct` only checks that the list is already
literal. The helpers are `to_field_list(struct)` and `from_field_list(list)` (None when
not literal).

`$fields_to_struct` reads the list's spine, not just its argument: each node, its `more`,
and for `[01]` its `label` and `rest`, again and again. Values are left alone (decision 4).
`spine_blockers` sits next to `_fields_to_struct`, the only code that knows the node labels:

```python
def spine_blockers(argument, path=()):
    yield path
    node = at(argument, path)
    if isinstance(node, terms.Struct) and (more := _field_position(node, 'more')) is not None:
        yield path + (more,)
        if index_value(node.fields[more].value) == 1:
            if (label := _field_position(node, 'label')) is not None:
                yield path + (label,)
            if (rest := _field_position(node, 'rest')) is not None:
                yield from spine_blockers(argument, path + (rest,))
```

`_field_position(struct, label)` is the position of the first field with that label, or
None.

### D. Other modules

| Module | Step | Change |
|---|---|---|
| `bruijn.py` | 1, 2, 3 | `Path`, `at`, `replace_at`, the blocker helpers, `BuiltinRule.blockers` (B); `to_field_list`, `from_field_list`, `spine_blockers`, the two `BUILTIN_RULES` entries (C) |
| `banf_shape.py` | 1 | the built-in case in `unblock` (B) |
| `banf_shape_test.py`, `banf_translate_test.py` | 1 | the monkeypatched rules get a `blockers` argument |
| `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`, `banf_rename.py` | — | none: a `Builtin` is a leaf, already parsed and printed |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | — | none (decision 7) |
| `docs/notes.md` | 1, 2, 3 | "Blockers" and "How to add a built-in" (1); the built-ins table, the rules in "`reduce`" (2, 3) |
| `docs/reduction_rules.md` | 1 | an `E-Builtin` congruence rule over a rule's blockers |

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

None: no word becomes reserved, and no term changes. `BuiltinRule` gets a field, which
only code that builds rules sees.

---

## Open questions

> [!IMPORTANT]
> 1. **Node labels.** `more`, `label`, `value`, `rest`. Alternatives: `head` / `tail`
>    with entries `{label, value}` (two levels per field), or a `tag` instead of `more`.
> 2. **Invalid labels in `$fields_to_struct`** (bytes that aren't UTF-8) are stuck
>    (decision 6). Should they be allowed, since a struct built by `$fields_to_struct`
>    never goes through the parser? An empty label is valid: it is an unlabeled field
>    (plan_struct_apply decision 1).

---

## Out of scope

- **`needs` as a function.** `needs` stays a string. With blockers in place it could
  become `(argument) -> str` and say which blocker was wrong, for example
  "field `b` must reduce to a byte array". That can be a separate change.
- **A cursor into `blockers`**, to avoid the O(n²) walk of decision 8. It can be added
  later without changing the contract.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: a built-in rule lists its blockers

- `bruijn.py`: B; `$fix` gets `no_blockers`. `banf_shape.py`: the case in `unblock`.
- Tests in `banf_shape_test.py`, with test-only rules (monkeypatched
  `bruijn.BUILTIN_RULES`):
  - `argument_blocker`: `$first ({p = {a = x}}.p)` reduces the projection, then fires.
  - `field_blockers`: `$both {a = (i -> i) [01], b = {c = [02]}.c}` reduces both fields,
    then fires; `$both {a = e, b = (i -> i) [02]}` reduces `b` and stays (`e` is free).
  - A rule whose blockers depend on what it sees: a field is yielded only when field 0
    reduces to `[01]`.
  - A path that isn't there (`(3,)` of a two-field struct) leaves the call as it is.
  - `$fix g` still doesn't reduce `g`; `argument_blocker` doesn't reduce fields.
- Contract test: for each rule in `BUILTIN_RULES`, on sample arguments, `rule` gives the
  same result when every part that isn't a blocker is replaced by a fresh free variable.
- `docs/notes.md`: a row in "Blockers" (`$name a` with a rule: the rule's blockers, in
  order); "How to add a built-in" lists `blockers` instead of a new `unblock` case.
  `docs/reduction_rules.md`: `E-Builtin`.

Commit: `oymomo: a built-in rule lists its blockers`

### Step 2: `$struct_to_fields s`

- `bruijn.py`: `to_field_list`, the `BUILTIN_RULES` entry.
- Tests:
  - `reduce`: `$struct_to_fields {}` → `{more = [00]}`; `$struct_to_fields {a = '1', "λ" = x}`
    → the list with labels `'a'` and `[cebb]`, in order; `$struct_to_fields $0` is stuck.
  - `reduce_until_top_stable`: `$struct_to_fields ({p = {a = x}}.p)` reduces; a value
    stays unreduced.
  - `banf_translate`: `let t = $struct_to_fields args.p in t` gives
    `$struct_to_fields has no opcode, so it must reduce away: its argument must reduce to a struct.`

Commit: `oymomo: add $struct_to_fields`

### Step 3: `$fields_to_struct l`

- `bruijn.py`: `from_field_list`, `spine_blockers`, the `BUILTIN_RULES` entry.
- Tests:
  - `reduce`: `$fields_to_struct {more = [00]}` → `{}`; a two-field list → the struct, in
    order; duplicates kept; a label `''` gives an unlabeled field. Stuck: a missing
    `more`, `more = [02]`, a label `[ff]`, a `rest` that isn't reduced yet (root only).
  - `spine_blockers`: the paths for a two-node list; no `label` or `rest` path after
    `more = [00]`.
  - `reduce_until_top_stable`: the goal example with a computed label; a `rest` and a
    `label` that need reducing; a `value` stays unreduced; the `map` example;
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
    assert banf_shape.reduce_until_top_stable(bruijn.resolve(parse(source))) == parse("{a = '23'}")
```
