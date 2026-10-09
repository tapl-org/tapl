# Plan: a struct applied to a label selects the field

Status: **proposed**. Open questions below.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. The struct apply rule in `bruijn.reduce` (`oymomo: a struct applied to a label selects the field`)
- [ ] 2. `banf_reduce` reduces the label of a struct apply (`oymomo: banf_reduce reduces a struct apply's label`)

## Goal

**Pick a struct field by a label computed at run time.** This is the part of goal 2 of
[plan_annotation.md](plan_annotation.md) that it left out: labels are names, not terms,
so `s.a` can't take its label from a variable.

```
{a = '23'} 'a'                          ⇒   '23'
(l -> {a = '23', b = '45'} l) 'b'       ⇒   '45'
{a = '23'} 'c'                          stuck
```

## Decisions

1. **No new syntax and no new term.** Struct and project syntax keep static labels:
   no `s.(e)`, no `{(e) = v}`. `s l` is already an `Apply`; it only gets a reduction rule.
2. **Labels are compared as bytes.** Each field's label is encoded to UTF-8 and compared
   with the argument's bytes; the argument is never decoded. `{"a b" = x} 'a b'` gives
   `x`, and `{"λ" = x} [cebb]` gives `x`. A parsed name is never empty and never holds a
   surrogate (the parser rejects `\u{d800}`), so every label has an encoding.
3. **A missing label is stuck, not an error**, as for projection: the term is not a redex
   and is left as it is. The same goes for bytes that match no label's encoding (`[ff]`,
   `''`), and for an argument that is not (yet) a byte array.
4. **Duplicate labels: the first field wins**, as `bruijn.project` does.
5. **A form on the label is ignored**: `{a = x} ('a' : 'i8')` gives `x`. The label is its
   bytes. Same as an `if` condition, which sees through `Formed` (plan_annotation C2).
6. **`Project` stays its own term.** `s.a` and `s 'a'` reduce to the same field once `s` is
   a struct, but `s.a` is not sugar for `s 'a'`. BANF's shapes (`args.n`, `blocks.label`,
   `prim.op`, `decls.f`) and the printer match on `Project`, and a project label must
   be a name anyway.
7. **BANF shape rules decide what BANF accepts.** A struct apply that reduces away (the
   struct is known) leaves nothing behind. One that stays stuck, such as `args 'n'` or
   `blocks 'done' {...}`, is not a BANF shape, and `convert` rejects it with today's
   messages (as plan_annotation decided for nested forms).

---

## Design

### A. Reduction rule

One new case in `bruijn.reduce`, next to projection:

```python
case terms.Apply(
    function=terms.Struct() as struct,
    argument=terms.ByteArray(value=label) | terms.Formed(term=terms.ByteArray(value=label)),
):
    selected = select(struct, label)
    return term if selected is None else selected
```

```python
def select(struct: terms.Struct, label: bytes) -> syntax.Term | None:
    """`{a = e, ...} 'a'` becomes `e`. None if no field's name has `label` as its UTF-8 bytes."""
    return next((field.value for field in struct.fields if field.label.encode('utf-8') == label), None)
```

The comparison is on bytes: each field's label is encoded to UTF-8 and compared with the
argument's bytes. The argument is never decoded, so bytes that aren't UTF-8 (`[ff]`) need
no special case: they just match no field.

- It still holds that at most one rule applies to a term: beta needs a `Lambda` callee,
  this rule a `Struct` callee.
- Before this plan, an apply of a struct was never a redex, and nothing gave it a meaning
  (BANF has no such shape). So no existing program changes meaning.

### B. Heads in `banf_reduce`

`bruijn.reduce` only looks at the root, so `{a = x} ((y -> y) 'a')` is not a redex until
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

So `step` first reduces the callee to a struct, then the label to a byte array, then the
root fires. An argument is reduced only when the callee is already a struct, so ordinary
applications stay lazy (`f ((x -> x) a)` doesn't touch the argument). Each step still
costs fuel, and a label that never becomes a byte array leaves the apply stuck.

### C. What doesn't change

| Module | Why |
|---|---|
| `terms.py`, `grammar.py`, `rule_names.py`, `printer.py` | no new term and no new syntax |
| `banf_rename.py` | `Apply` is already walked |
| `banf_translate.py`, `banf_terms.py`, `llvm_translate.py` | a struct apply either reduces away in `shape` or is rejected by `convert` as today (decision 7) |
| golden files | they use no struct apply |

### Precedence

Nothing new: a struct apply is an application.

| Source | Means |
|---|---|
| `{a = '23'} 'a'` | `({a = '23'}) 'a'` |
| `s.t 'a'` | `(s.t) 'a'` |
| `s 'a' 'b'` | `(s 'a') 'b'`: a nested struct, then its field |
| `f s 'a'` | `(f s) 'a'`; write `f (s 'a')` to pass the field |
| `s 'a' : t` | `s ('a' : t)`, which decision 5 reads as `s 'a'`; write `(s 'a') : t` for a form on the field |

---

## Affected modules

| Module | Change |
|---|---|
| `bruijn.py` | `select` and the struct apply case in `reduce` |
| `banf_reduce.py` | `_head` / `_with_head`: the argument of a struct apply |
| `docs/notes.md` | "`reduce`: one step at the root" gets the rule; "Heads" in `banf_reduce` gets the new head; "Kernel syntax decisions" mentions `s 'a'` next to `s.x` |

---

## Open questions

> [!IMPORTANT]
> 1. **Decision 5**: should a form on the label really be ignored, or should
>    `{a = x} ('a' : 'i8')` be stuck? Ignoring it matches `if`.
> 2. **BANF and stuck struct applies.** Should `args 'n'` (with a literal label) ever be
>    accepted as `args.n`, and `blocks 'done' {...}` as a jump? Today's answer is no: it's
>    not a BANF shape (decision 7). Accepting it would be a BANF shape change, in its own plan.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: the struct apply rule in `bruijn.reduce`

- `bruijn.py`: `select` and the `reduce` case (A).
- Tests in `bruijn_test.py`, each on `reduce` of a resolved term:
  - `{a = '23'} 'a'` → `'23'`; `{a = '23', b = '45'} 'b'` → `'45'`.
  - Duplicate labels: `{a = '1', a = '2'} 'a'` → `'1'`.
  - Quoted and non-ASCII names: `{"a b" = x} 'a b'`, `{"λ" = x} [cebb]`.
  - A formed label: `{a = '23'} ('a' : 'i8')` → `'23'`.
  - Stuck (`reduce(t) is t`): `{a = '23'} 'c'`, `{a = '23'} [ff]`, `{a = '23'} ''`,
    `{a = '23'} $0` under a binder, and `{a = '23'} ((x -> x) 'a')` (the root only).
- `docs/notes.md`: the rule in the `reduce` list.

Commit: `oymomo: a struct applied to a label selects the field`

### Step 2: `banf_reduce` reduces a struct apply's label

- `banf_reduce.py`: `_head` and `_with_head` (B).
- Tests in `banf_reduce_test.py`, on `whnf`:
  - The goal: `(l -> {a = '23', b = '45'} l) 'b'` → `'45'`.
  - A computed callee and label: `{p = {a = '23'}}.p ((x -> x) 'a')` → `'23'`.
  - Nested: `{a = {b = '1'}} 'a' 'b'` → `'1'`.
  - Stuck and unchanged: `{a = '23'} 'c'`.
  - Still lazy: in `f ((x -> x) 'a')` under a binder `f`, the argument is not reduced.
- Tests in `banf_translate_test.py`:
  - A block returning `{r = args.n} 'r'` translates like one returning `args.n`.
  - `args 'n'` is rejected with today's message.
- `docs/notes.md`: the new head in "Heads", and a line in "Kernel syntax decisions".
- Status of this plan: **implemented**.

Commit: `oymomo: banf_reduce reduces a struct apply's label`

---

## Verification

After every step:

```
hatch run full-check
```

The final check is the goal, as a term comparison:

```python
def test_dynamic_label():
    term = bruijn.resolve(parse("(l -> {a = '23', b = '45'} l) 'b'"))
    assert banf_reduce.whnf(term) == parse("'45'")
```
