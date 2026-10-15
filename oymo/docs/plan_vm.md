# Plan: a virtual machine that runs BANF without LLVM

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. Bytecode, and a compiler from BANF to it (`oymomo: add VM bytecode`)
- [ ] 2. The interpreter: run bytecode, imports bound by the host (`oymomo: add the VM`)
- [ ] 3. Opcodes are VM symbols, polymorphic in `form`: `$add_i32 {a, b}` becomes `'add' {'i32', a, b}`, fields in LLVM's order (`oymomo: opcodes are VM symbols`) — **breaking**
- [ ] 4. VM symbols that are not LLVM instructions: `'ctpop'`, `'trace'` (`oymomo: add VM-only symbols`)
- [ ] 5. Memory in the VM (`oymomo: add memory to the VM`)

Steps 1 and 2 need nothing new in the kernel or BANF: the VM runs the BANF that
LLVM gets today. Step 3 is the one breaking step: it renames every opcode, moves
`opcodes.py`, constant folding and `llvm_opcodes.py` into one table, and makes the
form an operand. [plan_memory.md](plan_memory.md) steps 2 and 3 need step 3 (memory
ops are entries of its table), and step 5 needs them.

## Goal

**A verified BANF module runs in Python, with the same results as under LLVM.** Tests
and, later, a REPL run a program without building LLVM IR or starting a JIT:

```
convert(term) → BANF → verify → vm_compile → bytecode → vm.run
                              ↘ llvm_translate → LLVM IR → JIT / object file
```

Everything up to BANF is shared, so the VM and LLVM see the same program. Every
operation that isn't a call into the program is a **VM symbol**, written
`'name' {args}`, from one table that says, for each, its signature, how the VM runs
it, how LLVM lowers it, and whether the kernel may fold it. The kernel, the VM and
LLVM read the same table, and differential tests check that they agree.

```
module: {main = => 'i32', putchar = {c = 'i32'} => 'i32'} -> {
  main = f -> {
    entry = args: {n = 'i32'} ->
      let q = module.putchar {c = [68000000]: 'i32'} in
      let r = 'ctpop' {'i32', $after {args.n, q}} in
      'add' {'i32', r, [01000000]},
  },
}
```

```python
program = vm_compile.compile(banf_translate.convert(term))
output = []
vm.run(program, 'main', [7], host={'putchar': lambda c: output.append(c) or c})
# 4, and output == [0x68]
```

`'add'` is LLVM's `add`, and `'ctpop'` LLVM's `llvm.ctpop`: the VM runs both in
Python, LLVM lowers them, and with literal arguments the kernel folds them (decision
8). `module.putchar` is an import: the host binds it in the VM, the linker binds it
in LLVM. (`$after` is [plan_memory.md](plan_memory.md) step 1.)

## Decisions

### What the VM runs (steps 1, 2)

1. **The VM runs bytecode compiled from verified BANF.** Not the kernel terms (the
   kernel has no blocks, no calls, no effects order) and not BANF directly: compiling
   resolves every name to a register and every block label to an offset once, so the
   interpreter loop does no lookups. `vm_compile` takes only modules that
   `banf_terms.verify` accepts, so it never checks a form.
2. **Values are Python values, never bytes.** An integer of form `iN` is a Python
   `int`, unsigned, below `2^N`, which is what `opcodes.evaluate` takes and gives. A
   struct is a tuple of its fields' values, in field order; labels are gone after
   compiling. Bytes appear only at the edges: a `Const` is decoded once, at compile
   time, little-endian as every byte array
   ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)),
   and `vm.run` takes and gives Python values.
3. **The bytecode is a register machine, one instruction per BANF let or terminator.**
   Each function is a flat list of instructions over numbered registers. A block's
   params are registers; a jump is a parallel move into the target's params, then a
   go-to. `GetField` is compiled to an index, since the forms are known after verify.

   | Instruction | BANF | Does |
   |---|---|---|
   | `op r, name, a...` | `OpcodeCall` (`VmCall` from step 3) | `r = run(a...)` |
   | `call r, f, a...` | `Call` to a function | push a frame for `f` |
   | `host r, f, a...` | `Call` to an import (`Signature`) | `r = host[f](a...)` |
   | `struct r, a...` | `MakeStruct` | `r = (a, ...)` |
   | `index r, s, i` | `GetField`, `GetIndex` | `r = s[i]` |
   | `data r, d` | `GetData` | `r = data[d]` |
   | `jump L, moves` | `Jump` | parallel move, go to `L` |
   | `branch c, L1, moves1, L2, moves2` | `Branch` | as `jump`, on `c != 0` |
   | `switch s, (L, moves)...` | `Switch` | the `s`-th target, or the last |
   | `return r` | `Return` | pop the frame, give `r` |

   An operand is a register or a constant, decoded at compile time.
4. **An operation whose result LLVM leaves undefined stops the VM.** Where
   `opcodes.evaluate` gives `None` (division by zero, a shift by the width or more),
   LLVM's result is undefined or poison; the VM raises
   `VmError: udiv i32: division by zero, in 'main' block 'entry'.` rather than pick a
   value. The kernel already doesn't fold these.
5. **Calls don't use the Python stack.** The interpreter is one loop over an explicit
   stack of frames, so a deep oymomo recursion costs memory, not Python recursion
   depth, as `bruijn`'s list loops cost fuel, not stack. `vm.run` takes `fuel`, the
   number of instructions it may run, and raises `VmError: out of fuel.` past it, so
   a test of an endless loop ends.

### Host functions and VM symbols (steps 2, 3, 4)

6. **Two kinds of host function: imports and VM symbols.**
   - An **import** (`module.putchar {...}`) is declared by the program, as today, and
     bound by whoever runs it: in the VM, by `vm.run(..., host={'putchar': f})`; in
     LLVM, by the linker. `vm.load` checks that every import the program calls is
     bound: `VmError: import 'putchar' is not bound.` Imported data is bound the same
     way.
   - A **VM symbol** (`'add' {...}`) is defined by the VM itself, the same in every
     program, in a fixed table in `vm_symbols.py`.

   That is "both": the program declares what it needs from outside, the VM defines
   what it always has.
7. **A VM symbol is called as a byte array applied to a struct.** `'name' {args}` is
   `Apply(ByteArray, Struct)`, a shape the kernel already leaves stuck (no rule
   matches a byte array in function position), so it needs no new term. Each table
   entry has:

   | Field | Meaning |
   |---|---|
   | `params` | in LLVM's operand order, each with a name for messages and docs; each a **form param** (decision 10) or a value param, whose form is fixed (`'ptr'`) or named by a form param (`form`) |
   | `result` | the result form, fixed or named by a form param |
   | `accepts` | which forms each form param may be: `'add' takes an integer form, got ptr.` |
   | `pure` | it reads and writes nothing but its arguments and result |
   | `run` | the Python function the VM calls, on Python values (decision 2) |
   | `llvm` | how LLVM lowers it, or `None` |

   `convert` turns `'name' {...}` into a BANF op `VmCall(name, forms, args)`: the
   form params, read as literal forms, and the value args as atoms. It is printed as
   LLVM writes the instruction: `add i32 a, b`, `zext i8 x to i32`.

   **Fields are positional, in LLVM's operand order, and labels are ignored**, as in
   `$after` and in a branch. `'sub' {'i32', x, y}` is `sub i32 x, y`, `x - y`,
   because LLVM writes `sub i32 %x, %y`; a form param sits where LLVM writes the
   type. Only the number of fields is checked: `'sub' takes 3 fields, got 2.`
   Optional params come last (`'alloca' {form, count}`), so leaving one out is
   leaving off the end. A label is free to write and means nothing:
   `'sub' {form = 'i32', subtrahend = x, minuend = y}` is still `x - y`. This drops
   [notes.md › Labels fit the op](notes.md#labels-fit-the-op): the order to
   remember is LLVM's, which the BANF and LLVM printouts show.

   A name not in the table is `Unknown VM symbol 'foo'.`; in LLVM, a symbol with no
   `llvm` is `'name' runs only in the VM.` This is also why decision 8 of
   [plan_memory.md](plan_memory.md) writes LLVM's aggregate types as tagged pairs
   (`{'array', {...}}`) and not as `'array' {...}`: that shape is a call.
8. **The kernel folds a pure VM symbol on literal arguments**, one rule for every
   symbol: when the name is a pure symbol, every form param is a literal form it
   folds on (integer forms, for now), and every value param a literal of its form,
   `run` gives the result, formed as `result`. This is today's constant folding
   ([plan_constant_folding.md](implemented/plan_constant_folding.md)) with the
   per-opcode rules of `BUILTIN_RULES` replaced by this one. An impure symbol never
   folds; it stays a call, ordered by `$after` like an import. The rule reads only
   literals, so it commutes with reduction, as [plan_confluence.md](plan_confluence.md)
   asks of every built-in rule. `vm_symbols.py` imports only `terms`, so `bruijn` can
   use it; LLVM lowerings are attached in `llvm_opcodes.py`, keyed by name, so the
   table stays free of llvmlite.
9. **`$` is kept only where the kernel or `convert` treats a term specially.** A VM
   symbol is a function on values, so it has no `$`. What keeps it:

   | Built-in | Why it isn't a VM symbol |
   |---|---|
   | `$fix` | a kernel rule on terms, not values |
   | `$struct_to_fields`, `$fields_to_struct` | they rewrite terms, and must reduce away before BANF |
   | `$after` | the kernel must not see through it, and `convert` drops it ([plan_memory.md](plan_memory.md)) |

### Opcodes polymorphic in `form` (step 3)

10. **The form is an operand, not part of the name.** One symbol per LLVM
    instruction, as LLVM writes `add i32 %a, %b`. A **form param** must reduce to a
    literal form; it is a form, not an operand, so it stays in place and is never
    let-bound (the other exception to
    [notes.md › Operands must be atoms](notes.md#operands-must-be-atoms), with
    `$after`).

    | Today | Step 3 | LLVM |
    |---|---|---|
    | `$add_i32 {a, b}` | `'add' {'i32', a, b}` | `add i32 a, b` |
    | `$sub_i32 {minuend, subtrahend}` | `'sub' {'i32', a, b}` | `sub i32 a, b` |
    | `$udiv_i32 {dividend, divisor}` | `'udiv' {'i32', a, b}` | `udiv i32 a, b` |
    | `$shl_i32 {value, amount}` | `'shl' {'i32', a, b}` | `shl i32 a, b` |
    | `$zext_i8_i32 {value}` | `'zext' {'i8', x, 'i32'}` | `zext i8 x to i32` |
    | `$slt_i32 {lhs, rhs}` | `'icmp_slt' {'i32', a, b}` | `icmp slt i32 a, b` |

    The same goes for `mul`, `sdiv`, `srem`, `urem`, `lshr`, `ashr`, `and`, `or`,
    `xor`, and `sext`, `trunc` (as `zext`).
    - **One symbol per comparison predicate, named `icmp_` and LLVM's predicate**,
      not LLVM's one `icmp` with a predicate field: `'icmp_eq'`, `'icmp_ne'`,
      `'icmp_ugt'`, `'icmp_uge'`, `'icmp_ult'`, `'icmp_ule'`, `'icmp_sgt'`,
      `'icmp_sge'`, `'icmp_slt'`, `'icmp_sle'`, each `{form, lhs, rhs}` and giving
      `'i1'`, as today. Float comparisons are `fcmp_` and LLVM's
      predicate ([plan_floats.md](plan_floats.md)), so every comparison names its
      LLVM instruction and predicate, and `icmp_ugt` (unsigned greater) can't be
      mistaken for `fcmp_ugt` (unordered or greater). BANF prints them as LLVM does
      (`icmp slt i32 a, b`).
    - **Still monomorphic where it matters**
      ([notes.md › Monomorphic](notes.md#monomorphic-one-op-per-signature)): the
      result form is read from the call, never inferred; widths are strict
      (`'add' expects a: i32, got i8.`); a conversion's target is the `to` field. The
      form moves from the name into a field; nothing else changes.
    - **A literal operand takes its form from `form`**, as a bare literal does today
      (`$add_i8 {a = [ff], b = [01]}`), and must have exactly its bytes:
      `'add' {'i32', [01], ...}` is
      `'add': a must be 4 bytes for i32, got 1.` A byte array is only its bytes, so it
      is never widened.
    - **`accepts`**: the arithmetic and bitwise symbols take an integer form; `and`,
      `or`, `xor`, `icmp_eq`, `icmp_ne` also `'i1'`, as today; `zext` and `sext` need `to`
      wider than `form`, `trunc` narrower: `'zext': to must be wider than i32, got i8.`
      Once [plan_memory.md](plan_memory.md) step 5 adds vectors, an integer vector is
      accepted wherever LLVM accepts one; the kernel folds only scalar integer forms.
    - **BANF ops carry their form params**, as LLVM's instructions carry their type.
      [notes.md › BANF](notes.md#banf)'s "ops carry no form, as in Cranelift" no
      longer holds for `VmCall`.
11. **The table replaces three files.** `opcodes.py`'s generated names become about
    25 entries; `opcodes.evaluate` becomes each entry's `run`; `llvm_opcodes.py`'s
    builders become each entry's `llvm`. `OpcodeCall` becomes `VmCall`.

### Memory (step 5)

12. **Memory is one `bytearray`, and a pointer is an offset into it.** Laid out as LLVM
    lays it out for the target: sizes, alignment and struct padding come from LLVM's
    data layout (llvmlite's `get_abi_size` and `get_element_offset` on the target
    data), and byte order is the target's, as [plan_memory.md](plan_memory.md)
    decision 12 says. So a program that reads memory reads the same bytes in the VM
    and under LLVM. `alloca` takes space from a stack area that a frame gives back
    when it returns; offset 0 is never handed out, so a stray zero pointer faults. An
    access outside what was allocated raises
    `VmError: load of 4 bytes at 0x10 is outside memory.` where LLVM would be
    undefined.

---

## Design

### A. Bytecode and compiler (step 1)

| Module | Change |
|---|---|
| `vm_bytecode.py` (new) | `Instruction` classes of decision 3, `Function(name, registers, params, code)`, `Program(functions, data, imports)`; `show(program)`, an assembly listing |
| `vm_compile.py` (new) | `compile(module) -> Program`: a register per block param and let, in order; block labels to offsets in a second pass; `GetField` to an index with `banf_terms.field_index`; constants decoded with their form |

### B. The interpreter (step 2)

| Module | Change |
|---|---|
| `vm.py` (new) | `load(program, host) -> Machine`, which checks imports; `Machine.run(function, args, fuel)`; `run(program, function, args, host, fuel)` for both; `op` runs `opcodes.evaluate`; `VmError` with the function and block |

### C. Opcodes are VM symbols (step 3)

| Module | Change |
|---|---|
| `vm_symbols.py` (new) | `VmSymbol(name, params, result, accepts, pure, run)`, `VM_SYMBOLS`; one entry per LLVM instruction of decision 10, `run` taken from `opcodes.evaluate`'s templates |
| `opcodes.py` | removed; `form_bits` and `byte_count` move to `vm_symbols.py` |
| `bruijn.py` | `_fold` rules replaced by one rule for `Apply(ByteArray, Struct)` (decision 8) |
| `banf_shape.py` | a VM symbol call: form params reduced to normal form in place, value params reduced as atoms |
| `banf_terms.py` | `OpcodeCall(opcode, args)` → `VmCall(symbol, forms, args)`; `form_of` from `result`; verifier from `params` and `accepts`; printed as LLVM writes it |
| `banf_translate.py` | `'name' {...}` read as `VmCall`; `$name` is only `$fix`, `$struct_to_fields`, `$fields_to_struct`, `$after`; any other `$name` is `Unknown built-in '$add_i32'; opcodes are VM symbols now: 'add' {'i32', a, b}.` |
| `llvm_opcodes.py` | builders keyed by symbol name, taking the form params |
| `printer.py` | prints `'add' {'i32', x, y}` |
| `vm_compile.py`, `vm.py` | `op` runs the entry's `run` |
| tests, goldens, `docs/notes.md` | every `$name_iN` rewritten |

### D. VM-only and intrinsic symbols (step 4)

| Module | Change |
|---|---|
| `vm_symbols.py` | `ctpop` (form param `form`, `value`, pure; LLVM `llvm.ctpop`) and `trace` (form param `form`, `value`, impure: appends to the machine's trace and gives `value`; no `llvm`) |
| `llvm_translate.py` | a `VmCall` with no lowering is `'trace' runs only in the VM.` |
| `vm.py` | `Machine.trace` |

### E. Memory (step 5)

| Module | Change |
|---|---|
| `vm_layout.py` (new) | size, alignment and field offsets of a form, from llvmlite's target data, so the VM and LLVM share one layout |
| `vm_symbols.py`, `vm.py` | `run` for `alloca`, `getelementptr`, `load`, `store` (their entries are [plan_memory.md](plan_memory.md)'s) on the machine's memory; a pointer is an `int` offset; loads and stores encode and decode values in the target's byte order |

---

## Breaking changes

Step 3: every opcode is renamed and takes its form as a field.

| Before | After |
|---|---|
| `$add_i32 {a = x, b = y}` | `'add' {'i32', x, y}` |
| `$sub_i32 {minuend = x, subtrahend = y}` | `'sub' {'i32', x, y}` |
| `$zext_i8_i32 {value = x}` | `'zext' {'i8', x, 'i32'}` |
| BANF `add_i32 x, y` | BANF `add i32 x, y` |

The old names give an error that names the new spelling (design C). Steps 1, 2, 4 and
5 break nothing: `'name' {args}` was stuck in the kernel and an error in `convert`.

---

## Open questions

> [!IMPORTANT]
> 1. **Trap or not** (decision 4). Stopping on an undefined operation makes the VM
>    stricter than LLVM, which is what tests want. A program that relies on what
>    LLVM happens to give would then run under LLVM and stop in the VM.
> 2. **Which VM-only symbols first** (step 4). `trace` is there for tests; Anvil's
>    layer-1 helpers (type values, errors) are the likely next users.
> 3. **Imports as VM symbols.** Could the VM define common imports (`putchar`,
>    `malloc`) itself, so a test needs no `host`? Then an import bound by neither is
>    still an error.
> 4. **Calling oymomo from a VM symbol.** A symbol that takes a function (a callback)
>    would need the VM to run a nested call: later, with function pointers
>    ([plan_c_interop.md](plan_c_interop.md) 1.6).
> 5. **A REPL and a CLI.** There is no driver yet. `oymo run --vm a.oymo` and a REPL
>    that converts and runs one expression are the obvious users; a plan of their
>    own.
> 6. **Speed.** A Python loop is slow next to a JIT. Fine for tests; if Anvil's layer
>    1 runs in the VM at compile time, a faster dispatch (instructions as closures)
>    may be needed.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: bytecode and compiler

- A.
- Tests:
  - `vm_compile`: every BANF op and terminator compiles to the instruction of
    decision 3; block params get registers; a jump to a block with two params is a
    two-register parallel move; a swap (`jump loop(b, a)` into `loop(a, b)`) is still
    correct; `GetField` becomes `index` with the field's position.
  - goldens: each `.banf` golden gets a `.vm` listing beside it.
- `docs/notes.md`: a VM section: the pipeline and the instruction table.

Commit: `oymomo: add VM bytecode`

### Step 2: the interpreter

- B.
- Tests:
  - `vm`: each opcode on edge operands (0, 1, the top bit, all ones) gives
    `opcodes.evaluate`'s result; a loop (sum 1 to n) gives the sum; a recursive
    function 10000 deep returns (no Python recursion); `udiv` by zero is `VmError`;
    an endless loop is `out of fuel`; a call to an unbound import is
    `import 'putchar' is not bound.`; an import reaches the host.
  - differential: every golden and every program in `llvm_translate_test` that runs
    under the JIT gives the same result in the VM.
- `docs/notes.md`: values, traps, fuel, host binding.

Commit: `oymomo: add the VM`

### Step 3: opcodes are VM symbols

- C.
- Tests:
  - `vm_symbols`: every entry's `run` gives what `opcodes.evaluate` gave for every
    old opcode, on edge operands (the old table is kept in the test as the oracle).
  - `bruijn`: `'add' {'i32', [01000000], [02000000]}` folds to
    `[03000000]: 'i32'`; with a variable it stays; with `form` computed by β
    (`(f -> 'add' {f, ...}) 'i32'`) it folds; with a non-literal form it stays.
  - `banf_translate`: `'add' {'i32', args.n, ...}` is `add i32 n, ...`;
    `'zext' {'i8', x, 'i32'}` is `zext i8 x to i32`; `'sub'` with labels written in
    the wrong order still subtracts by position; every message of decisions 7 and
    10 (field count, `accepts`, operand size, `to` width, unknown symbol);
    `$add_i32` names the new spelling.
  - `llvm_translate`: `test_fold_matches_llvm` over the new table; every lowering
    matches the old one.
  - every existing test and golden passes after the rewrite.
- `docs/notes.md`: Opcodes rewritten (polymorphic in `form`, and why still strict);
  Built-ins lists only the four `$` built-ins; BANF's `VmCall`; folding.

Commit: `oymomo: opcodes are VM symbols`

### Step 4: VM-only and intrinsic symbols

- D.
- Tests:
  - `vm`: `'ctpop' {'i32', 7}` is 3; `trace` records its argument and
    gives it back; two `trace`s chained with `$after` record in order.
  - `bruijn`: `ctpop` folds on a literal; `trace` never does.
  - `llvm_translate`: `ctpop` is `call i32 @llvm.ctpop.i32` and runs under the JIT
    with the VM's result; `trace` is `'trace' runs only in the VM.`
  - golden `vm_symbol.oymo`: the goal program.
- `docs/notes.md`: VM-only symbols.

Commit: `oymomo: add VM-only symbols`

### Step 5: memory

Needs [plan_memory.md](plan_memory.md) steps 2 and 3.

- E.
- Tests:
  - `vm_layout`: sizes and offsets of `{i8, i32}`, `<{i8, i32}>`, `[3 x i32]` match
    llvmlite's for the host target.
  - `vm`: the goal of [plan_memory.md](plan_memory.md) gives 42; a store of `'i32'`
    and a load of `'i8'` at the same pointer gives the target's low or high byte; an
    out-of-bounds load is `VmError`; memory from `alloca` is given back on return.
  - differential: every memory program in `llvm_translate_test` gives the same
    result in the VM.
- `docs/notes.md`: the VM's memory.
- Status of this plan: **implemented**.

Commit: `oymomo: add memory to the VM`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: every program that runs under LLVM's JIT in the test suite runs in
the VM with the same result, and the goal program gives 4 and calls `putchar` once.
