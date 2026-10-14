# Plan: a virtual machine that runs BANF without LLVM

Status: **proposed**, with open questions; 0 of 5 steps.

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. Bytecode, and a compiler from BANF to it (`oymomo: add VM bytecode`)
- [ ] 2. The interpreter: run bytecode, imports bound by the host (`oymomo: add the VM`)
- [ ] 3. VM symbols: `'name' {args}` calls a symbol the VM defines (`oymomo: add VM symbols`)
- [ ] 4. The kernel folds a pure VM symbol on literals (`oymomo: fold pure VM symbols`)
- [ ] 5. Memory in the VM (`oymomo: add memory to the VM`)

Steps 1 and 2 need nothing new in the kernel or BANF: the VM runs the BANF that
LLVM gets today. Step 3 adds the one new term shape, step 4 lets the kernel run it,
and step 5 needs [plan_memory.md](plan_memory.md) steps 2 and 3. No step is breaking.

## Goal

**A verified BANF module runs in Python, with the same results as under LLVM.** Tests
and, later, a REPL run a program without building LLVM IR or starting a JIT:

```
convert(term) → BANF → verify → vm_compile → bytecode → vm.run
                              ↘ llvm_translate → LLVM IR → JIT / object file
```

Everything up to BANF is shared, so the VM and LLVM see the same program. The VM's
opcodes are computed by `opcodes.evaluate`, the function the kernel already folds with
([plan_constant_folding.md](implemented/plan_constant_folding.md)), so the kernel, the
VM and LLVM agree by construction, and differential tests check it.

```
module: {main = => 'i32', putchar = {c = 'i32'} => 'i32'} -> {
  main = f -> {
    entry = args: {n = 'i32'} ->
      let q = module.putchar {c = [68000000]: 'i32'} in
      let r = 'popcount_i32' {value = $after {args.n, q}} in
      r,
  },
}
```

```python
program = vm_compile.compile(banf_translate.convert(term))
output = []
vm.run(program, 'main', [7], host={'putchar': lambda c: output.append(c) or c})
# 3, and output == [0x68]
```

`'popcount_i32' {...}` calls a VM symbol (decision 6): the VM runs it in Python,
LLVM lowers it to `llvm.ctpop.i32`, and with a literal argument the kernel folds it
(decision 8). `module.putchar` is an import: the host binds it in the VM, the linker
binds it in LLVM.

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
   | `const r, v` | a `Const` operand | `r = v` (decoded at compile time) |
   | `op r, name, a...` | `OpcodeCall` | `r = opcodes.evaluate(name, a...)` |
   | `call r, f, a...` | `Call` to a function | push a frame for `f` |
   | `host r, f, a...` | `Call` to an import (`Signature`) | `r = host[f](a...)` |
   | `vm r, s, a...` | `VmCall` (step 3) | `r = vm_symbols[s](a...)` |
   | `struct r, a...` | `MakeStruct` | `r = (a, ...)` |
   | `index r, s, i` | `GetField`, `GetIndex` | `r = s[i]` |
   | `data r, d` | `GetData` | `r = data[d]` |
   | `jump L, moves` | `Jump` | parallel move, go to `L` |
   | `branch c, L1, moves1, L2, moves2` | `Branch` | as `jump`, on `c != 0` |
   | `switch s, (L, moves)...` | `Switch` | the `s`-th target, or the last |
   | `return r` | `Return` | pop the frame, give `r` |

   A constant operand is folded into the instruction that uses it, not given its own
   `const` (an instruction's operand is a register or a constant).
4. **An opcode whose result LLVM leaves undefined stops the VM.** Where
   `opcodes.evaluate` gives `None` (division by zero, a shift by the width or more),
   LLVM's result is undefined or poison; the VM raises
   `VmError: $udiv_i32: division by zero, in 'main' block 'entry'.` rather than pick a
   value. The kernel already doesn't fold these.
5. **Calls don't use the Python stack.** The interpreter is one loop over an explicit
   stack of frames, so a deep oymomo recursion costs memory, not Python recursion
   depth, as `bruijn`'s list loops cost fuel, not stack. `vm.run` takes `fuel`, the
   number of instructions it may run, and raises `VmError: out of fuel.` past it, so
   a test of an endless loop ends.

### Host functions and VM symbols (steps 2, 3)

6. **Two kinds of host function: imports and VM symbols.**
   - An **import** (`module.putchar {...}`) is declared by the program, as today, and
     bound by whoever runs it: in the VM, by `vm.run(..., host={'putchar': f})`; in
     LLVM, by the linker. `vm.load` checks that every import the program calls is
     bound: `VmError: import 'putchar' is not bound.` Imported data is bound the same
     way.
   - A **VM symbol** (`'popcount_i32' {...}`) is defined by the VM itself, the same in
     every program, in a fixed table in `vm_symbols.py`, as opcodes are in
     `opcodes.py`.

   That is "both": the program declares what it needs from outside, the VM defines
   what it always has.
7. **A VM symbol is called as a byte array applied to a struct.** `'name' {args}` is
   `Apply(ByteArray, Struct)`, a shape the kernel already leaves stuck (no rule
   matches a byte array in function position), so it needs no new term and no `$`.
   Each table entry has:

   | Field | Meaning |
   |---|---|
   | `params`, `result` | labels and forms, as an `OpcodeSignature` |
   | `pure` | it reads and writes nothing but its arguments and result |
   | `run` | the Python function the VM calls, on Python values (decision 2) |
   | `llvm` | how LLVM lowers it, as `llvm_opcodes` does, or `None` |

   `convert` turns `'name' {...}` into a BANF op `VmCall(name, args)`, printed
   `vm popcount_i32 n`, checked by label as an opcode call; a name not in the table
   is `Unknown VM symbol 'foo'.` In LLVM, a symbol with no `llvm` is
   `'name' runs only in the VM.` This is also why decision 8 of
   [plan_memory.md](plan_memory.md) writes LLVM's aggregate types as tagged pairs
   (`{'array', {...}}`) and not as `'array' {...}`: that shape is a call.
8. **The kernel folds a pure VM symbol on literal arguments** (step 4), as it folds an
   opcode: one `BuiltinRule`-like rule for `Apply(ByteArray, Struct)` that, when the
   name is a pure symbol and every field is a literal of its param's form, calls
   `run` and gives the result formed as `result`. An impure symbol never folds; it
   stays a call, and is ordered by `$after` like an import. The rule reads only
   literals, so it commutes with reduction, as
   [plan_confluence.md](plan_confluence.md) asks of every built-in rule.
   `vm_symbols.py` imports only `terms` and `opcodes`, so `bruijn` can use it.

### Memory (step 5)

9. **Memory is one `bytearray`, and a pointer is an offset into it.** Laid out as LLVM
   lays it out for the target: sizes, alignment and struct padding come from LLVM's
   data layout (llvmlite's `get_abi_size` and `get_element_offset` on the target
   data), and byte order is the target's, as
   [plan_memory.md](plan_memory.md) decision 12 says. So a program that reads memory
   reads the same bytes in the VM and under LLVM. `alloca` takes space from a
   stack area that a frame gives back when it returns; offset 0 is never handed out,
   so a stray zero pointer faults. An access outside what was allocated raises
   `VmError: load of 4 bytes at 0x10 is outside memory.` where LLVM would be
   undefined.

---

## Design

### A. Bytecode and compiler (step 1)

| Module | Change |
|---|---|
| `vm_bytecode.py` (new) | `Instruction` classes of decision 3, `Function(name, registers, params, code)`, `Program(functions, data, imports)`; `show(program)`, an assembly listing |
| `vm_compile.py` (new) | `compile(module) -> Program`: a register per block param and let, in order; block labels to offsets in a second pass; `GetField` to an index with `banf_terms.field_index`; constants decoded with their form (`opcodes.form_bits`) |

### B. The interpreter (step 2)

| Module | Change |
|---|---|
| `vm.py` (new) | `load(program, host) -> Machine`, which checks imports; `Machine.run(function, args, fuel)`; `run(program, function, args, host, fuel)` for both; `VmError` with the function and block |

### C. VM symbols (step 3)

| Module | Change |
|---|---|
| `vm_symbols.py` (new) | `VmSymbol(name, params, result, pure, run, llvm)` and `VM_SYMBOLS`; first entries `popcount_i8` to `popcount_i64` (pure, `llvm.ctpop`) and `trace_i32` (impure, appends to the machine's trace, gives its argument; no `llvm`) |
| `banf_terms.py` | op `VmCall(symbol, args)`; `form_of` and the verifier from the table; printed `vm name a, b` |
| `banf_translate.py` | `'name' {...}` (a byte array applied to a struct) read as `VmCall`, fields checked by label |
| `banf_shape.py` | a VM symbol call's fields reduced as atoms, as an opcode call's |
| `vm_compile.py`, `vm.py` | `vm` instruction; `trace_i32` writes to `Machine.trace` |
| `llvm_translate.py` | `VmCall` → the entry's `llvm`, or `'name' runs only in the VM.` |

### D. Folding (step 4)

| Module | Change |
|---|---|
| `bruijn.py` | in `reduce`, `Apply(ByteArray, Struct)` with a pure symbol: reduce the fields, and if all are literals of their params' forms, `run` and give the result formed as `result` |

### E. Memory (step 5)

| Module | Change |
|---|---|
| `vm_layout.py` (new) | size, alignment and field offsets of a form, from llvmlite's target data, so the VM and LLVM share one layout |
| `vm_bytecode.py`, `vm_compile.py`, `vm.py` | `alloca`, `gep`, `load`, `store`; a pointer is an `int` offset; loads and stores encode and decode values in the target's byte order |

---

## Breaking changes

None. The VM is new. `'name' {args}` was stuck in the kernel and an error in
`convert` (a byte array is not a function), so no program that worked changes meaning.

---

## Open questions

> [!IMPORTANT]
> 1. **Trap or not** (decision 4). Stopping on an undefined opcode makes the VM
>    stricter than LLVM, which is what tests want. A program that relies on what
>    LLVM happens to give would then run under LLVM and stop in the VM.
> 2. **The first VM symbols** (decision 7). `popcount` is there to show the three
>    paths (VM, LLVM, folding) with one example; it could be an opcode instead. Which
>    symbols does the VM really need first: output for tests (`trace`), Anvil's
>    layer-1 helpers (type values, errors), or form helpers?
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
    function 10000 deep returns (no Python recursion); `$udiv_i32` by zero is
    `VmError`; an endless loop is `out of fuel`; a call to an unbound import is
    `import 'putchar' is not bound.`; the goal's `putchar` reaches the host.
  - differential: every golden and every program in `llvm_translate_test` that runs
    under the JIT gives the same result in the VM.
- `docs/notes.md`: values, traps, fuel, host binding.

Commit: `oymomo: add the VM`

### Step 3: VM symbols

- C.
- Tests:
  - `banf_translate`: `'popcount_i32' {value = args.n}` is `vm popcount_i32 n`;
    fields out of order are an error; `'nope' {}` is `Unknown VM symbol 'nope'.`
  - `vm`: `popcount_i32` of `7` is `3`; `trace_i32` records its argument and gives it
    back; two `trace_i32` chained with `$after` record in order.
  - `llvm_translate`: `popcount_i32` is `call i32 @llvm.ctpop.i32` and runs under the
    JIT with the VM's result; `trace_i32` is `'trace_i32' runs only in the VM.`
  - golden `vm_symbol.oymo`.
- `docs/notes.md`: VM symbols in Built-ins (not `$`: a call), `VmCall` in BANF, the
  table.

Commit: `oymomo: add VM symbols`

### Step 4: folding

- D.
- Tests:
  - `bruijn`: `'popcount_i32' {value = [07000000]: 'i32'}` normalizes to
    `[03000000]: 'i32'`; with a variable argument it stays; `'trace_i32'` with a
    literal stays (impure); a field formed as the wrong form stays.
  - confluence: a program with a pure VM symbol gives the same BANF from `t` and from
    `normalize(t)`.
- `docs/notes.md`: the rule in the kernel's reduction rules
  ([reduction_rules.md](reduction_rules.md)).

Commit: `oymomo: fold pure VM symbols`

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
the VM with the same result, and the goal program gives 3 and calls `putchar` once.
