# Plan: `$struct_to_fields` and `$fields_to_struct`, a struct to a list of fields and back

Status: **implemented**.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [x] 1. A built-in reduces its own call (`oymomo: a built-in reduces its own call`)
- [x] 2. `$struct_to_fields s`: a struct to a list of fields (`oymomo: add $struct_to_fields`)
- [x] 3. `$fields_to_struct l`: a list of fields to a struct (`oymomo: add $fields_to_struct`)

Built on [plan_builtin.md](plan_builtin.md). [plan_constant_folding.md](../plan_constant_folding.md)
builds on step 1.

## Goal

**Users can build a struct dynamically**: computed labels, a computed number of fields,
and fields mapped or filtered by oymomo code. Today a struct's labels and field count are
fixed by the syntax.

```
$fields_to_struct ($struct_to_fields {a = '1', b = '2'})            ⇒   {a = '1', b = '2'}
(l -> v -> $fields_to_struct {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'
                                                                    ⇒   {a = '23'}
```

Mapping a struct's fields:

```
let map = $fix (map -> f -> l ->
  if l.more then {more = [01], label = l.label, value = f l.value, rest = map f l.rest}
  else l)
in $fields_to_struct (map g ($struct_to_fields {a = x, b = y}))
⇒ {a = g x, b = g y}
```

## Overview

1. **Step 1** lets a built-in reduce parts of its argument. Today
   `$struct_to_fields ({p = s}.p)` is stuck: the rule sees a projection, not a struct,
   and nothing reduces it.
2. **Steps 2 and 3** add the two built-ins. Each is one entry in `bruijn.BUILTIN_RULES`:
   no new term, no grammar change, no reserved word.

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

### 1. A built-in reduces its own call

A built-in takes one argument, and only it knows which parts of the argument it reads.
So it reduces them itself:

```python
BuiltinRule.reduce(call, reduce_part) -> Term
```

- `reduce_part(part)` reduces `part` until its top constructor can't change.
- The built-in calls `reduce_part` on the parts it needs, then checks if it can fire.
- It returns:
  - **the result**, if it fires;
  - **`call` with the reduced parts put back**, if something changed but it can't fire yet;
  - **`call` itself**, if nothing changed.

The caller replaces the call with what comes back. There are two callers:

| Caller | Passes as `reduce_part` | Effect |
|---|---|---|
| `bruijn.reduce` | `keep` (returns the part unchanged) | Root-only, as today: fires only if the parts are already reduced |
| `banf_shape.unblock` | `reduce_until_top_stable` | Reduces the parts; one case for every built-in |

Example, `$fields_to_struct` on a list whose parts need reducing:

```
$fields_to_struct {more = (x -> x) [01], label = l, value = v, rest = (x -> x) {more = [00]}}
  reduce more  → [01], so this node has a field
  reduce label → l
  reduce rest  → {more = [00]}, the end
  fire         → {l = v}
```

**Rules every `reduce` follows** (step 1 tests them for every built-in):

1. Read a part only after giving it to `reduce_part`. Otherwise the result could depend
   on a part that still reduces to something else.
2. Build a new call only if some part changed (`new is not part`). So with `keep`,
   `reduce(t) is t` still means "not a redex".
3. Then "returns `call` itself" means stuck for good, and `banf_translate.convert` can
   report it (decision 8).

**Rejected:**

- *The built-in lists paths to the parts it reads, and `banf_shape` reduces them.* Needs
  path helpers, splits each built-in into two functions, and rewalks the paths every
  step (O(n²) on a list).
- *A fixed set of argument shapes in `banf_shape`.* Every new shape changes `banf_shape`.
- *Return None when nothing changed.* `reduce`, `step` and `unblock` already return the
  term itself for that.

### 2. Two built-ins, `$struct_to_fields s` and `$fields_to_struct l`

- Kernel-only: no opcode, so they must reduce away before BANF (plan_builtin decision 10).
- The names say both sides of the conversion and mirror each other.

Rejected names: `$pack` / `$unpack` (elsewhere they mean bytes), `$construct_struct` /
`$deconstruct_struct` (don't name the fields side), `$to_list` / `$from_list` and similar
(unclear about direction).

### 3. A list of fields is a chain of `{more, label, value, rest}` structs

The kernel has no lists, so a list is plain structs that today's syntax can build and read:

```
empty    = {more = [00]}
nonempty = {more = [01], label = 'a', value = e, rest = <list>}
```

Code walks a list with `if l.more then … else …`.

Rejected: Scott/Church lists (a rule can't look inside a lambda), `head` / `tail` with
`{label, value}` entries (two levels per field), `tag` instead of `more` (reads worse in
an `if`).

### 4. A label is the UTF-8 bytes of the field's name

A bare byte array, no form. `''` is an unlabeled field (plan_struct_apply decision 1).

### 5. Field values stay lazy

Neither built-in reduces a value: `$struct_to_fields {a = (x -> x) y}` keeps
`(x -> x) y` as the `value`.

### 6. Field order is kept

Order matters for layout (notes: "Struct, not record").

### 7. A malformed input is stuck, not an error

As for projection, the call just doesn't reduce.

- `$struct_to_fields`: stuck unless the argument reduces to a struct literal.
- `$fields_to_struct`: stuck unless every node is `{more = [00]}` or
  `{more = [01], label, value, rest}` with a valid UTF-8 label.
- A form on `more` or `label` is ignored (`more = [01] : 'u8'` works); a form on a node
  is not.
- Extra fields in a node are ignored; in a node, the first of two equal labels counts.
- Duplicate labels across nodes are kept, as a struct literal may have them.

Non-UTF-8 labels are stuck so that every struct stays one a literal could write.

### 8. `banf_shape` reduces both away; a stuck one is rejected

`banf_shape` reduces each call with its `reduce` (decision 1). A call still stuck reaches
`banf_translate.convert`, which rejects it like any kernel-only built-in:

```
$struct_to_fields has no opcode, so it must reduce away: its argument must reduce to a struct.
```

The "must reduce to …" text is hard-coded in `banf_translate`, the only code that
reports it, in a dict by built-in name (`'a struct'`, `'a list of fields'`). So
`BuiltinRule` drops its `needs` field: a rule only says how to reduce.

---

## Design

### Syntax

None. They are built-ins and apply like any function: `$struct_to_fields s.a` is
`$struct_to_fields (s.a)`; write `f ($fields_to_struct l)`, not `f $fields_to_struct l`.

### Step 1: `bruijn.py` and `banf_shape.py`

```python
ReducePart = Callable[[syntax.Term], syntax.Term]


def keep(part):
    """Reduces nothing: `bruijn.reduce` passes it, so it stays root-only."""
    return part


@dataclass(frozen=True)
class BuiltinRule:
    name: str
    reduce: Callable[[terms.Apply, ReducePart], syntax.Term]
```

The two call sites:

```python
# bruijn.reduce
case terms.Apply(function=terms.Builtin(name=name)) if (builtin := BUILTIN_RULES.get(name)) is not None:
    return builtin.reduce(term, keep)

# banf_shape._Shaper.unblock, before the generic apply
case terms.Apply(function=terms.Builtin(name=name)) if (builtin := bruijn.BUILTIN_RULES.get(name)) is not None:
    return builtin.reduce(term, self.reduce_until_top_stable)
```

- `$fix` never calls `reduce_part`, so `g` stays lazy.
- Each reduction costs fuel, so an endless list (built with `$fix`) runs out of fuel.

### Steps 2 and 3: the two rules

```python
BuiltinRule('struct_to_fields', _struct_to_fields)
BuiltinRule('fields_to_struct', _fields_to_struct)


def _struct_to_fields(call, reduce_part):
    argument = reduce_part(call.argument)
    if isinstance(argument, terms.Struct):
        return to_field_list(argument)
    return call if argument is call.argument else replace(call, argument=argument)


def _fields_to_struct(call, reduce_part):
    field_list = _reduce_field_list(call.argument, reduce_part)
    if (struct := from_field_list(field_list)) is not None:  # None unless the list is literal
        return struct
    return call if field_list is call.argument else replace(call, argument=field_list)


def _reduce_field_list(field_list, reduce_part):
    """Reduces each node, its `more`, and if `more` is [01], its `label` and its `rest`.
    Never a `value`. A loop, not recursion, so a long list costs fuel, not Python stack."""
    parents = []  # (node, position of its rest), outermost first
    node = reduce_part(field_list)
    while isinstance(node, terms.Struct) and (more := _field_position(node, 'more')) is not None:
        node = _with_value(node, more, reduce_part(node.fields[more].value))
        if _bytes(node.fields[more].value) != b'\x01':
            break
        if (label := _field_position(node, 'label')) is not None:
            node = _with_value(node, label, reduce_part(node.fields[label].value))
        if (rest := _field_position(node, 'rest')) is None:
            break
        parents.append((node, rest))
        node = reduce_part(node.fields[rest].value)
    for parent, rest in reversed(parents):
        node = _with_value(parent, rest, node)
    return node
```

`_field_position(struct, label)` is the position of the first field with that label, or None.
`_bytes(term)` is a byte array's bytes, form ignored. `_with_value(struct, i, v)` returns
`struct` itself when `v` is already the value at `i`.

### Modules

| Module | Step | Change |
|---|---|---|
| `bruijn.py` | 1 | `ReducePart`, `keep`, `BuiltinRule.reduce`, no `needs`, `reduce` passes `keep` |
| `banf_translate.py` | 1, 2, 3 | the "must reduce to" texts, by built-in name, replace `builtin.needs` (1); one entry per built-in (2, 3) |
| `bruijn.py` | 2, 3 | `to_field_list`, `from_field_list`, `_reduce_field_list`, the two rules |
| `banf_shape.py` | 1 | the built-in case in `unblock` |
| `banf_shape_test.py`, `banf_translate_test.py` | 1 | test rules use `reduce(call, reduce_part)` |
| `docs/notes.md` | 1, 2, 3 | "Blockers", "How to add a built-in" (1); built-ins table (2, 3) |
| `docs/reduction_rules.md` | 1 | an `E-Builtin` congruence rule |

No change to the grammar, printer, terms, `banf_terms` or LLVM modules.

## Breaking changes

None for users. `BuiltinRule(name, needs, rule)` becomes `BuiltinRule(name, reduce)`.

## Out of scope

- **A finer error**, saying which part was wrong ("field `b` must reduce to a byte
  array"). A separate change in `banf_translate`.

---

## Implementation steps

Each step is one commit, leaves `hatch run full-check` green, and updates
`docs/notes.md` for its part.

### Step 1: a built-in reduces its own call

- Code: "Step 1" in Design. `_fix` takes `reduce_part` and ignores it. `needs` moves
  from `BuiltinRule` to a dict in `banf_translate` (decision 8).
- Tests in `banf_shape_test.py`, with test-only rules:
  - `$first ({p = {a = x}}.p)` reduces the projection and fires in one `step`.
  - `$both {a = (i -> i) [01], b = {c = [02]}.c}` reduces both fields, then fires.
  - `$both {a = e, b = (i -> i) [02]}` (`e` free) comes back with `b = [02]`, unfired.
  - A rule that reduces field 1 only when field 0 is `[01]`.
  - `$fix g` doesn't reduce `g`; `bruijn.reduce` alone doesn't reduce parts.
- Tests of the three rules of decision 1, for every built-in.
- Docs: notes "Blockers" and "How to add a built-in"; `reduction_rules.md` `E-Builtin`.

Commit: `oymomo: a built-in reduces its own call`

### Step 2: `$struct_to_fields s`

- Code: `to_field_list`, the rule.
- Tests:
  - `$struct_to_fields {}` → `{more = [00]}`.
  - `$struct_to_fields {a = '1', "λ" = x}` → labels `'a'` and `[cebb]`, in order.
  - `$struct_to_fields $0` is stuck; `$struct_to_fields ({p = {a = x}}.p)` reduces.
  - Values stay unreduced.
  - `banf_translate`: `let t = $struct_to_fields args.p in t` gives the decision 8 error.

Commit: `oymomo: add $struct_to_fields`

### Step 3: `$fields_to_struct l`

- Code: `from_field_list`, `_reduce_field_list`, the rule.
- Tests:
  - `{more = [00]}` → `{}`; a two-node list → the struct, in order.
  - Duplicate labels kept; label `''` → unlabeled field; `more = [01] : 'u8'` works.
  - Stuck: no `more`, `more = [02]`, label `[ff]`, a node under a form.
  - `_reduce_field_list` never reduces a `value`, and stops after `more = [00]`.
  - The goal and `map` examples.
  - An endless list built with `$fix` runs out of fuel.
  - Round trips both ways.
- Mark this plan **implemented**, move it to `docs/implemented/`, update `docs/plans.md`.

Commit: `oymomo: add $fields_to_struct`

## Verification

`hatch run full-check` after every step. The final check is the goal:

```python
def test_dynamic_struct():
    source = "(l -> v -> $fields_to_struct {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'"
    assert banf_shape.reduce_until_top_stable(bruijn.resolve(parse(source))) == parse("{a = '23'}")
```
