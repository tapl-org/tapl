# Plan: `$struct_to_fields` and `$fields_to_struct`, a struct to a list of fields and back

Status: **proposed**.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. A built-in reduces its own call (`oymomo: a built-in reduces its own call`)
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

| # | Decision | Step |
|---|---|---|
| 1 | A built-in reduces its own call, with a `reduce_part` it is given | 1 |
| 2 | Two built-ins, `$struct_to_fields s` and `$fields_to_struct l` | 2, 3 |
| 3 | A list of fields is a chain of `{more, label, value, rest}` structs | 2, 3 |
| 4 | A label is the UTF-8 bytes of the field's name | 2, 3 |
| 5 | Field values stay lazy | 2, 3 |
| 6 | Field order is kept | 2, 3 |
| 7 | A malformed input is stuck, not an error | 2, 3 |
| 8 | `banf_shape` reduces both away; a stuck one is rejected | 2, 3 |

### A built-in reduces its own call (step 1)

#### 1. A built-in reduces its own call, with a `reduce_part` it is given

**Problem.** `bruijn.reduce` only rewrites the root, and `banf_shape` never reduces a
built-in's argument (notes: "Blockers"). So `$struct_to_fields ({p = s}.p)` is stuck:
the rule sees a projection, not a struct.

**Fix.** A built-in takes one argument, and only it knows which parts of it it reads.
So each built-in steps its whole call itself:

```python
reduce(call: Apply, reduce_part: Callable[[Term], Term]) -> Term
```

- `reduce_part` reduces a part until its top constructor can't change. The built-in
  calls it on the parts it reads, in its own order, and picks what to read next by what
  comes back: `$fields_to_struct` reduces `rest` only once `more` is `[01]`.
- The caller puts what `reduce` returns in place of the call:

  | `reduce` returns | When |
  |---|---|
  | the result | the call fires |
  | `call` with the reduced parts put back | some part changed, but the call doesn't fire (yet) |
  | `call` itself | nothing changed |

- Two callers, one function per built-in:

  | Caller | `reduce_part` | So |
  |---|---|---|
  | `bruijn.reduce` | `keep`, which returns the part itself | still root-only: fires only if the parts are already reduced, else returns `call` itself |
  | `banf_shape.unblock` | `self.reduce_until_top_stable` | reduces the parts, with fuel; one generic case for every built-in |

```
$fields_to_struct {more = (x -> x) [01], label = l, value = v, rest = (x -> x) {more = [00]}}
                   ^ more → [01], so label, then rest → a node, so its more → [00]; fires: {l = v}
```

**Contract.**

| Rule | Means |
|---|---|
| Reads only what it reduced | `reduce` looks at a part as `reduce_part` returned it (its top constructor, and the term inside a `Formed`, which `step` reduces too), and deeper only at parts it also gave to `reduce_part`. This keeps reduction confluent: a rule never depends on a part that might still reduce differently. |
| Builds a new call only when a part changed | It checks `new is not part`, as `unblock` does. So with `keep` it returns the result or `call` itself, and `reduce(t) is t` still tells that the root is not a redex. |
| `call` itself is final | Follows from the two above: if `reduce` returns `call` itself with `reduce_until_top_stable`, every part it reads is top-stable, so no reduction elsewhere can make the call fire, and `banf_translate.convert` can report `needs` (decision 8). |

Step 1 tests these for every rule in `BUILTIN_RULES`.

**Rejected:**

| Alternative | Why not |
|---|---|
| The rule lists its *blockers* as paths into its argument (`blockers(argument) -> Iterable[Path]`), and `banf_shape` reduces them one at a time | Needs `Path`, `at` and `replace_at`, and two functions per built-in that must agree on the labels. `unblock` walks the paths from the root again at each step, O(n²) for an n-node list, and needs a "blockers only grow" contract for stuck to be final. |
| A fixed set of shapes in `banf_shape` (`NONE`, `ARGUMENT`, `FIELDS`, `SPINE`) | Each new shape would change `banf_shape`, and the node labels (`more`, `label`, `rest`) would be written in two modules. |
| `reduce` returns None when nothing changed, as `rule` does today | `call` itself is what `bruijn.reduce`, `step` and `unblock` return, and `is` tells it. |

**Cost:** a built-in that reads parts says both what it reduces and what it matches.
Helpers (`reduce_argument`, `reduce_argument_fields`) keep the common cases one line.

### The two built-ins (steps 2 and 3)

#### 2. Two built-ins, `$struct_to_fields s` and `$fields_to_struct l`

- Each is one entry in `bruijn.BUILTIN_RULES`: a `BuiltinRule` with no
  opcode, so both are kernel-only (plan_builtin decision 10).
- Both read their argument, so each reduces it in its own `reduce` (decision 1).
- `needs` is `'a struct'` for `$struct_to_fields` and `'a list of fields'` for
  `$fields_to_struct`. A leftover call is reported as
  `$struct_to_fields has no opcode, so it must reduce away: its argument must reduce to a struct.`
- Nothing is reserved: `struct_to_fields` and `fields_to_struct` stay plain names.

**Why these names:** they say both sides of the conversion, so they read without knowing
a convention, and the two mirror each other.

**Rejected:**

| Names | Why not |
|---|---|
| `$pack` / `$unpack` | They don't say what they work on, and elsewhere (Python's `struct.pack`, Perl's `pack`, LLVM's packed structs) they mean bytes. That misleads in a language with byte arrays and memory opcodes. |
| `$construct_struct` / `$deconstruct_struct` | They don't name the other side (fields), and a struct literal also constructs a struct. |
| `$build_struct`, `$fields` / `$struct`, `$explode` / `$implode`, `$to_list` / `$from_list` | Less clear about direction or about what they work on. |

#### 3. A list of fields is a chain of `{more, label, value, rest}` structs

The kernel has no lists. With fixed labels, users build and read the nodes with today's
syntax:

```
nil  = {more = [00]}
cons = {more = [01], label = 'a', value = e, rest = <list>}
```

`more` is a one-byte boolean, so code walks a list with an ordinary
`if l.more then … else …`.

**Rejected:**

| Shape | Why not |
|---|---|
| Scott or Church lists (`c -> n -> …`) | A rule can't look inside a lambda to see the nodes, and an `if` can't branch on one. |
| `head` / `tail`, with entries `{label, value}` | Two levels per field: every walk reads `l.head.label` and `l.head.value`, and `_reduce_spine` has one more step. |
| `tag` instead of `more` | Same shape, but `if l.tag` reads worse, and nothing else in the kernel uses tags yet. |

#### 4. A label is the UTF-8 bytes of the field's name

`$struct_to_fields` encodes each label as a bare byte array, with no form;
`$fields_to_struct` decodes it. `''` is an unlabeled field (plan_struct_apply
decision 1).

#### 5. Field values stay lazy

Neither built-in reduces a value: `$struct_to_fields {a = (x -> x) y}` keeps
`(x -> x) y` in the `value` field.

#### 6. Field order is kept

Field order matters for layout (notes: "Struct, not record"). `$struct_to_fields` lists
the fields in order; `$fields_to_struct` builds them in list order.

#### 7. A malformed input is stuck, not an error

As for projection, the rule returns None.

- `$struct_to_fields` is stuck on anything but a struct literal.
- `$fields_to_struct` is stuck unless every node is either `{more = [00]}` or
  `{more = [01], label, value, rest}`, with a label that is valid UTF-8.
- A form on `more` or `label` is ignored, as `bruijn.index_value` ignores one, so
  `more = [01] : 'u8'` works. A form on a node or on the whole list is not: the
  argument must be a struct, as for `s.l`.
- Extra fields in a node are ignored. If a node has a label twice, the first one counts.
- Duplicate labels across nodes are kept, as a struct literal may have them.

**Why non-UTF-8 labels are stuck**, even though a struct built by `$fields_to_struct`
never goes through the parser: every struct stays one that a literal could write and
the printer can print, and `$struct_to_fields` gives back the same bytes.

#### 8. `banf_shape` reduces both away; a stuck one is rejected

Both are kernel-only, so BANF has no op for them: `banf_shape.shape` reduces every
`$fields_to_struct` and `$struct_to_fields` call with its own `reduce` (decision 1), until
the rule fires. A call that stays stuck reaches `banf_translate.convert`, which rejects
it with the message of decision 2, as for any kernel-only built-in.

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

### B. A built-in reduces its own call (step 1)

In `bruijn.py`:

```python
ReducePart = Callable[[syntax.Term], syntax.Term]
"""Reduces a part of a built-in's argument until its top constructor can't change.
Returns the part itself if it doesn't change."""


def keep(part: syntax.Term) -> syntax.Term:
    """The `ReducePart` that `reduce` passes: it reduces nothing, so `reduce` stays root-only."""
    return part


@dataclass(frozen=True)
class BuiltinRule:
    """How `$name arg` steps.

    `reduce(call, reduce_part)` gets the whole call. It passes each part of the argument
    that it reads to `reduce_part`, and returns the result if the call fires, else `call`
    with the changed parts put back, else `call` itself. `needs` says what the argument
    must reduce to, for the error when it doesn't (`'a struct'`).
    """

    name: str
    needs: str | None
    reduce: Callable[[terms.Apply, ReducePart], syntax.Term]


def reduce_argument(call: terms.Apply, reduce_part: ReducePart) -> terms.Apply:
    """`call` with its argument reduced; `call` itself if it doesn't change."""
    argument = reduce_part(call.argument)
    return call if argument is call.argument else replace(call, argument=argument)


def reduce_field(struct: terms.Struct, position: int, reduce_part: ReducePart) -> terms.Struct:
    """`struct` with the value at `position` reduced; `struct` itself if it doesn't change."""


def reduce_argument_fields(call: terms.Apply, reduce_part: ReducePart) -> terms.Apply:
    """`call` with its argument reduced, then, if it is a struct, each field in order."""
```

`$fix` becomes `BuiltinRule('fix', None, _fix)` with `_fix(call, reduce_part)`, which
never calls `reduce_part`: `g` stays lazy. `bruijn.reduce` calls every built-in the same
way:

```python
case terms.Apply(function=terms.Builtin(name=name)) if (builtin := BUILTIN_RULES.get(name)) is not None:
    return builtin.reduce(term, keep)
```

In `banf_shape.py`, one case in `_Shaper.unblock`, before the generic apply:

```python
case terms.Apply(function=terms.Builtin(name=name)) if (
    builtin := bruijn.BUILTIN_RULES.get(name)
) is not None:
    # A built-in reduces the parts of its argument that it reads.
    return builtin.reduce(term, self.reduce_until_top_stable)
```

- The caller puts what `reduce` returns in place of the call, so `unblock` keeps no
  state, and one case serves every built-in.
- A part that is never given to `reduce_part` stays lazy, as `$fix`'s `g` does.
- One `unblock` may reduce several parts, and may fire. It fires only after some part
  changed (else `bruijn.reduce` would have fired first, with `keep`), and each reduction
  costs fuel, so fuel still runs down. A list that never ends (built with `$fix`) runs
  out of fuel with today's error.

| Built-in | Its `reduce` | `step` on it |
|---|---|---|
| `$fix g` | fires; never calls `reduce_part` | fires right away |
| `$struct_to_fields ({p = s}.p)` | `reduce_argument`, then `to_field_list` | the argument reduces to `s` and the rule fires, in one step |
| `$add_i32 {a = (x -> x) [01..]: 'i32', b = …}` | `reduce_argument_fields`, then the fold | the argument, then each field, then the fold |
| `$fields_to_struct L` | `_reduce_spine` (C), then `from_field_list` | each node, its `more`; if `[01]`: its `label`, then its `rest` as a node, … |

### C. Rules in `bruijn.BUILTIN_RULES` (steps 2 and 3)

- **struct_to_fields**: `$struct_to_fields {l1 = e1, …, ln = en}` gives
  `{more = [01], label = 'l1', value = e1, rest = … {more = [00]}}`. The labels are bare
  byte arrays (no form).
- **fields_to_struct**: `$fields_to_struct L` gives `{l1 = e1, …, ln = en}` when `L` is a
  *literal list*: each node is a `Struct` whose `more` is a byte array `[00]` or `[01]`,
  and for `[01]` whose `label` is a byte array of valid UTF-8 and whose `rest` is again a
  literal list. A `Formed` around `more` or `label` is seen through, as an `if` condition
  is. Otherwise not a redex (decision 7).

```python
BuiltinRule('struct_to_fields', 'a struct', _struct_to_fields)
BuiltinRule('fields_to_struct', 'a list of fields', _fields_to_struct)


def _struct_to_fields(call, reduce_part):
    call = reduce_argument(call, reduce_part)
    if isinstance(call.argument, terms.Struct):
        return to_field_list(call.argument)
    return call
```

The matching never reduces: `from_field_list(list)` (None when not literal) only checks
that the list is already literal, and `to_field_list(struct)` only reads the fields.

`$fields_to_struct` reads the list's spine, not just its argument: each node, its `more`,
and for `[01]` its `label` and `rest`, again and again. Values are left alone (decision 5).
`_reduce_spine` sits next to `from_field_list`, the only code that knows the node labels:

```python
def _reduce_spine(node, reduce_part):
    """`node` reduced, then its `more`; if `[01]`, its `label`, then its `rest` the same way.
    `node` itself if nothing changes."""
    node = reduce_part(node)
    if not isinstance(node, terms.Struct) or (more := _field_position(node, 'more')) is None:
        return node
    node = reduce_field(node, more, reduce_part)
    if index_value(node.fields[more].value) != 1:
        return node
    if (label := _field_position(node, 'label')) is not None:
        node = reduce_field(node, label, reduce_part)
    if (rest := _field_position(node, 'rest')) is not None:
        node = _replace_field(node, rest, _reduce_spine(node.fields[rest].value, reduce_part))
    return node


def _fields_to_struct(call, reduce_part):
    spine = _reduce_spine(call.argument, reduce_part)
    if (struct := from_field_list(spine)) is not None:
        return struct
    return call if spine is call.argument else replace(call, argument=spine)
```

`_field_position(struct, label)` is the position of the first field with that label, or
None. `_replace_field(struct, position, value)` returns `struct` itself when `value` is
the value already there.

### D. Other modules

| Module | Step | Change |
|---|---|---|
| `bruijn.py` | 1, 2, 3 | `ReducePart`, `keep`, `reduce_argument`, `reduce_field`, `reduce_argument_fields`, `BuiltinRule.reduce`, `reduce` passes `keep` (B); `to_field_list`, `from_field_list`, `_reduce_spine`, the two `BUILTIN_RULES` entries (C) |
| `banf_shape.py` | 1 | the built-in case in `unblock` (B) |
| `banf_shape_test.py`, `banf_translate_test.py` | 1 | the monkeypatched rules become `reduce(call, reduce_part)` |
| `terms.py`, `rule_names.py`, `grammar.py`, `printer.py`, `banf_rename.py` | — | none: a `Builtin` is a leaf, already parsed and printed |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | — | none (decision 8) |
| `docs/notes.md` | 1, 2, 3 | "Blockers" and "How to add a built-in" (1); the built-ins table, the rules in "`reduce`" (2, 3) |
| `docs/reduction_rules.md` | 1 | an `E-Builtin` congruence rule: a built-in's `reduce` reduces the parts it reads |

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

None: no word becomes reserved, and no term changes. `BuiltinRule.rule(call, arg)`
becomes `reduce(call, reduce_part)`, which only code that builds rules sees.

---

## Out of scope

- **`needs` as a function.** `needs` stays a string. With `reduce` in place it could
  become `(call) -> str` and say which part was wrong, for example
  "field `b` must reduce to a byte array". That can be a separate change.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: a built-in reduces its own call

- `bruijn.py`: B; `rule` becomes `reduce`, `_fix` takes `reduce_part` and ignores it,
  `bruijn.reduce` passes `keep`. `banf_shape.py`: the case in `unblock`.
- Tests in `banf_shape_test.py`, with test-only rules (monkeypatched
  `bruijn.BUILTIN_RULES`):
  - `reduce_argument`: `$first ({p = {a = x}}.p)` reduces the projection and fires in
    one `step`.
  - `reduce_argument_fields`: `$both {a = (i -> i) [01], b = {c = [02]}.c}` reduces
    both fields, then fires; `$both {a = e, b = (i -> i) [02]}` reduces `b` and stays
    (`e` is free): the call comes back with `b = [02]`.
  - A rule that picks what to reduce by what it sees: field 1 is reduced only when
    field 0 reduces to `[01]`.
  - `$fix g` still doesn't reduce `g`; `reduce_argument` doesn't reduce fields.
  - `bruijn.reduce` on `$first ({p = {a = x}}.p)` returns the term itself (`keep`).
- Contract tests (decision 1), for each rule in `BUILTIN_RULES` on sample arguments,
  with a `reduce_part` that records what it was given:
  - Replacing every part that wasn't given to `reduce_part` by a fresh free variable
    gives the same result.
  - With `keep`, `reduce` returns the result or `call` itself, never a new call.
  - Called again on its own unchanged return, `reduce` returns it itself (stuck is
    final).
- `docs/notes.md`: a row in "Blockers" (`$name a` with a rule: the parts its `reduce`
  reads); "How to add a built-in" describes `reduce(call, reduce_part)` instead of a
  new `unblock` case. `docs/reduction_rules.md`: `E-Builtin`.

Commit: `oymomo: a built-in reduces its own call`

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

- `bruijn.py`: `from_field_list`, `_reduce_spine`, the `BUILTIN_RULES` entry.
- Tests:
  - `reduce`: `$fields_to_struct {more = [00]}` → `{}`; a two-field list → the struct, in
    order; duplicates kept; a label `''` gives an unlabeled field; `more = [01] : 'u8'`
    works. Stuck: a missing `more`, `more = [02]`, a label `[ff]`, a node under a form,
    a `rest` that isn't reduced yet (root only).
  - `_reduce_spine`, with a recording `reduce_part`: the parts given for a two-node
    list; no `label` or `rest` after `more = [00]`; never a `value`.
  - `reduce_until_top_stable`: the goal example with a computed label; a `rest` and a
    `label` that need reducing; a `value` stays unreduced; the `map` example;
    `$fields_to_struct ($fix (l -> {more = [01], label = 'a', value = x, rest = l}))`
    runs out of fuel.
  - Round trips: `$fields_to_struct ($struct_to_fields s)` gives `s`;
    `$struct_to_fields ($fields_to_struct l)` gives `l` for a list with bare labels.
- Status of this plan: **implemented**; move it to `docs/implemented/` and update
  `docs/plans.md`.

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
