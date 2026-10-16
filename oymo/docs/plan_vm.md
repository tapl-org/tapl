# Plan: Spindle, a virtual machine that runs BANF without LLVM

**Status:** paused · 1 of 6 steps · side project, no release waits for it; rewritten in
Tenon after 1.0 · [roadmap › Spindle in Tenon](roadmap.md#after-10--spindle-in-tenon)

> [!NOTE]
> Step 3 is done, without VM code, under the name **opcode**. Read *VM symbol*,
> `vm_symbols.py`, `VmSymbol`, `VmCall`, `run` as *opcode*, `opcodes.py`, `Opcode`,
> `OpcodeCall(opcode, forms, args)`, `evaluate`; folding is `reduction.fold_opcode`.

## Goal

- Run a verified BANF module in Python with **the same results as under LLVM**.
- A **tiny VM embedded like Lua**: it knows integers, control flow and calls; structs,
  memory, imports and coroutine scheduling are host functions.
- State is two host objects, `Spindle` and `Fiber`: the host creates, runs, resumes
  them, and calls into them from its own functions.
- Written so a C (later Tenon) port is a straight translation.

## Steps

One commit each; each leaves `hatch run full-check` green and updates `docs/notes.md`.

- [ ] 1. Stack bytecode, and a compiler from BANF to it (`oymomo: add VM bytecode`)
- [ ] 2. The VM: `Spindle` and `Fiber` objects, host functions, host calls back into the VM (`oymomo: add the VM`)
- [x] 3. Opcodes are VM symbols, polymorphic in `form`: `$add_i32 {a, b}` becomes `'add' {'i32', a, b}`, fields in LLVM's order (`oymomo: opcodes are VM symbols`) — **breaking**
- [ ] 4. Coroutines: a host function yields the fiber, the host resumes it, yields cross host calls by continuations (`oymomo: VM coroutines`)
- [ ] 5. VM symbols that are not LLVM instructions: `'ctpop'`, `'trace'`, as host functions (`oymomo: add VM-only symbols`)
- [ ] 6. Memory as a host library (`oymomo: add memory to the VM`)

Pipeline (option A; option B in [Open questions](#open-questions) 8):

```
convert(term) → BANF → verify → spindle_compile → bytecode → Spindle(program, host) → fiber.resume
                              ↘ llvm_translate → LLVM IR → JIT / object file
```

## Decisions

### What the VM runs (steps 1, 2)

1. **Bytecode compiled from verified BANF.** Names → slots, labels → offsets once;
   the loop does no lookups. `spindle_compile` accepts only modules
   `banf_terms.verify` accepts, so it never checks a form.
2. **The VM knows integers; every other value is the host's.** `iN` is an unsigned
   Python `int` below `2^N`. Structs, pointers, fibers are opaque host values.
   Constants decoded once at compile time, little-endian.
3. **A stack machine, as Wren's.** Ten instructions (table below). A frame is a
   window of the fiber's one value stack: params, then block params and lets, then
   operands. A jump pushes args, then stores them last to first (no temporaries
   for parallel moves). `Branch`/`Switch` edges with moves get a stub.

   | Instruction | Stack | BANF |
   |---|---|---|
   | `const k` | → v | constant atom, defined data |
   | `get s` | → v | variable |
   | `set s` | v → | let, block param |
   | `op o` | a... → r | `OpcodeCall` (a core `VmCall` from step 3) |
   | `call f` | a... → r | `Call` to a function |
   | `host h, n` | a... → r | `Call` to an import; `MakeStruct`, `GetField`, `GetIndex`; non-core `VmCall` |
   | `jump L` | | `Jump`, after its moves |
   | `jump_if L` | c → | `Branch`: to `L` on `c != 0`, else next |
   | `switch n, L0 ... Ln` | s → | `Switch`: the `s`-th target, or the last |
   | `return` | r → | `Return`: pop frame, push `r` in the caller's |

4. **An operation LLVM leaves undefined stops the VM.** Where `opcodes.evaluate`
   gives `None`: `SpindleError: udiv i32: division by zero, in 'main' block 'entry'.`
5. **No Python stack for VM calls; fuel suspends.** One loop over frames. `resume`
   takes `fuel` (instructions); past it, returns `OutOfFuel()` and the next `resume`
   goes on. Only host callbacks nest a loop (decision 14).

### Host functions and VM symbols (steps 2, 3, 5)

6. **Two kinds of host function, both bound by the host:**
   - **import** (`module.putchar {...}`): declared by the program; bound by
     `Spindle(..., imports=...)` in the VM, by the linker in LLVM. Data too.
   - **VM symbol** (`'add' {...}`): fixed table in `vm_symbols.py`; core runs integer
     ones; the rest come from `Spindle(..., symbols=...)`, defaulting to `run` via
     `spindle_lib.default()`.
   - The compiler's own symbols: `'struct'` (`MakeStruct`), `'field'` (`GetField`,
     `GetIndex`); default struct is a Python tuple.
   - Unbound: `SpindleError: import 'putchar' is not bound.` / `symbol 'ctpop' is not bound.`
7. **A VM symbol is a byte array applied to a struct**, `'name' {args}`, already stuck
   in reduction, so no new term. Table entry fields: `params`, `result`, `accepts`,
   `pure`, `core`, `run`, `llvm`. `convert` makes `VmCall(name, forms, args)`, printed
   as LLVM (`add i32 a, b`). **Fields are positional in LLVM's order; labels are
   ignored**; only the count is checked (`'sub' takes 3 fields, got 2.`); optional
   params last. Unknown: `Unknown VM symbol 'foo'.`; no `llvm`: `'name' runs only in
   the VM.`
8. **Reduction folds a pure VM symbol on literal arguments**, one rule for all:
   literal form params (integer forms for now) and literal values → `run`, formed as
   `result`. Impure symbols never fold. Folding uses the table's `run`, never the
   host's binding.
9. **`$` only where reduction or `convert` treats a term specially:** `$fix`,
   `$struct_to_fields`, `$fields_to_struct`, `$seq`.

### Opcodes polymorphic in `form` (step 3)

10. **The form is an operand, not part of the name.** One symbol per LLVM
    instruction. A form param must reduce to a literal form, stays in place, never
    let-bound.

    | Before | Step 3 | LLVM |
    |---|---|---|
    | `$add_i32 {a, b}` | `'add' {'i32', a, b}` | `add i32 a, b` |
    | `$sub_i32 {minuend, subtrahend}` | `'sub' {'i32', a, b}` | `sub i32 a, b` |
    | `$udiv_i32 {dividend, divisor}` | `'udiv' {'i32', a, b}` | `udiv i32 a, b` |
    | `$shl_i32 {value, amount}` | `'shl' {'i32', a, b}` | `shl i32 a, b` |
    | `$zext_i8_i32 {value}` | `'zext' {'i8', x, 'i32'}` | `zext i8 x to i32` |
    | `$slt_i32 {lhs, rhs}` | `'icmp_slt' {'i32', a, b}` | `icmp slt i32 a, b` |

    - Same for `mul`, `sdiv`, `srem`, `urem`, `lshr`, `ashr`, `and`, `or`, `xor`;
      `sext`, `trunc` as `zext`.
    - Comparisons: one symbol per predicate, `icmp_eq|ne|ugt|uge|ult|ule|sgt|sge|slt|sle`,
      `{form, lhs, rhs}` → `'i1'`; floats use `fcmp_`.
    - Still monomorphic: result read from the call, strict widths
      (`'add' expects a: i32, got i8.`), conversion target in `to`.
    - A literal operand must have exactly `form`'s bytes:
      `'add': a must be 4 bytes for i32, got 1.`
    - `accepts`: integer forms; `and`, `or`, `xor`, `icmp_eq`, `icmp_ne` also `'i1'`;
      `zext`/`sext` need `to` wider, `trunc` narrower
      (`'zext': to must be wider than i32, got i8.`); integer vectors once
      plan_memory step 5 adds them (folded only for scalars).
    - BANF ops carry their form params, as LLVM instructions carry types.
11. **One table replaces three files and draws the core's line.** `opcodes.py`
    names → ~25 entries; `evaluate` → `run`; `llvm_opcodes.py` builders → `llvm`;
    `OpcodeCall` → `VmCall`. Today's opcodes are `core`; every later symbol is a host
    function unless moved into the core on purpose.

### The VM as a host object (steps 2, 4)

12. **State is two host objects, nothing global** (Lua's `global_State`/`lua_State`):
    - `Spindle(program, symbols, imports)`: program and bindings, shared by fibers.
    - `Fiber` from `machine.fiber(function, args)`: value stack, frame stack, status
      `'suspended' | 'running' | 'normal' | 'dead'`.
      `fiber.resume(value=None, fuel=None)` → `Returned(v)`, `Yielded(v)`, `OutOfFuel()`;
      an error raises `SpindleError` and kills it.
    - `fiber.frames()` for messages; `fiber.host` slot for host per-fiber state.
    - `machine.call(function, args, fuel=None)`: new fiber run to the end; may not yield.
13. **A host function is `f(fiber, *args)`** returning a value, `Yield(value, k=None)`
    or `Call(function, args, k=None)`; `k(fiber, v)` returns any of the three again
    (Lua 5.2 continuations without `longjmp`). Python exceptions become
    `SpindleError: host function 'putchar' failed: ...`.
14. **A host function may call back into the VM, recursively:** `fiber.call(...)`
    nests a loop (no yield or fuel-out inside; depth ≤ `max_host_depth=200`);
    `Call(...)` nests nothing and may yield. Errors in `fiber.call` are catchable.
    Resuming another fiber nests a loop; the resumer is `'normal'`.
15. **Coroutines are host functions, not instructions.** `spindle_lib.coroutines()`
    gives `'yield' {form, value}`. Fibers from oymomo code wait for function values.
16. **A pure interpreter, C-port-ready.** No JIT; bytecode checked once at load
    (jump targets, stack depths, arity, bindings); then the loop checks only fuel and
    traps. Plain data: integer code array, constant pool, function table, host slots.

### Memory (step 6)

17. **Memory is a host library.** `spindle_lib.memory(layout)` binds `'alloca'`,
    `'getelementptr'`, `'load'`, `'store'` on one `bytearray` per `Spindle`; a pointer
    is an `int` offset. Laid out as LLVM's data layout for the target, in its byte
    order. `alloca` uses a per-fiber stack, freed by `'stacksave'`/`'stackrestore'`.
    Offset 0 never handed out; out of range: `SpindleError: load of 4 bytes at 0x10 is outside memory.`

## Design

Modules per step (tests in [Background](#tests-per-step)).

| Step | Module | Change |
|---|---|---|
| 1 | `spindle_bytecode.py` (new) | opcodes and sizes; `Function(name, arity, slots, max_stack, entry)`, `HostSlot(kind, name, arity)`, `Program(code, constants, functions, host_slots, data)`; `show(program)` listing |
| 1 | `spindle_compile.py` (new) | `compile(module) -> Program`: slots, pushes and `set`s, jump moves last to first, edge stubs, labels in a second pass, `max_stack`; `MakeStruct` = `host 'struct', n`; `GetField` = `const i; host 'field', 2` (`banf_terms.field_index`); constants decoded with their form |
| 2 | `spindle.py` (new) | `Spindle(program, symbols, imports, max_host_depth)` checks bytecode and bindings; `Fiber` (`resume`, `call`, `status`, `frames`, `host`); `Returned`, `OutOfFuel`, `Call`; `SpindleError` with function and block; `op` runs `opcodes.evaluate` |
| 2 | `spindle_lib.py` (new) | `default()`: `'struct'` (tuple), `'field'` (index) |
| 3 | `vm_symbols.py` (new) | `VmSymbol(name, params, result, accepts, pure, core, run)`, `VM_SYMBOLS`; all `core`; `run` from `evaluate`'s templates |
| 3 | `opcodes.py` | removed; `bit_width`, `byte_width` move to `vm_symbols.py` |
| 3 | `reduction.py` | `_fold` rules → one rule for `Apply(ByteArray, Struct)` |
| 3 | `banf_shape.py` | form params reduced in place; value params as atoms |
| 3 | `banf_terms.py` | `OpcodeCall` → `VmCall(symbol, forms, args)`; `form_of` from `result`; verifier from `params`/`accepts`; LLVM-style print |
| 3 | `banf_translate.py` | `'name' {...}` → `VmCall`; other `$name` → `Unknown built-in '$add_i32'; opcodes are VM symbols now: 'add' {'i32', a, b}.` |
| 3 | `llvm_opcodes.py`, `printer.py` | builders keyed by name, taking form params; prints `'add' {'i32', x, y}` |
| 3 | `spindle_compile.py`, `spindle.py`, `spindle_lib.py` | `core` → `op` (form params as immediates), else `host`; `op` runs `run`; `default()` binds non-`core` entries |
| 3 | tests, goldens, `docs/notes.md` | every `$name_iN` rewritten |
| 4 | `spindle.py` | `Yield`; `resume(value)`; `k` in `Yield`/`Call`; `'normal'`; decision 14 errors |
| 4 | `vm_symbols.py`, `spindle_lib.py` | `yield` (form, value; impure; not core; no `llvm`); `coroutines()` |
| 5 | `vm_symbols.py` | `ctpop` (pure; LLVM `llvm.ctpop`), `trace` (impure; no `llvm`); both not core |
| 5 | `spindle_lib.py` | `default()` binds `ctpop`; `tracer(out)` binds `'trace'` (appends, returns value) |
| 5 | `llvm_translate.py` | no lowering → `'trace' runs only in the VM.` |
| 6 | `spindle_layout.py` (new) | size, alignment, offsets from llvmlite target data |
| 6 | `spindle_lib.py`, `spindle_compile.py` | `memory(layout)` incl. `stacksave`/`stackrestore`, target byte order; save/restore around functions calling `'alloca'` |

## Open questions

> [!IMPORTANT]
> 1. **Trap or not** (decision 4)? Stricter than LLVM suits tests, but a program relying
>    on LLVM's actual result would run under LLVM and stop in the VM.
> 2. **Which VM-only symbols first** (step 5)? `trace` for tests; next likely Tenon
>    layer-1 helpers (type values, errors).
> 3. **Common imports in `spindle_lib`** (`putchar`, `malloc`)? Unbound is still an error.
> 4. **Function values:** passing functions to the host and creating fibers from oymomo
>    wait for function pointers ([plan_c_interop.md](plan_c_interop.md) 1.6).
> 5. **REPL and CLI** (`oymo run --spindle a.oymo`)? A plan of their own.
> 6. **Speed:** if Tenon layer 1 runs in the VM, make `struct`/`field` core
>    instructions (against "no data structures")?
> 7. **Values in a C port** (decision 16): `iN` ≤ 64 fits a word; wider ints and host
>    values need handles, released by the host when a fiber dies (no GC).
> 8. **What Spindle runs, now that BANF goes in oymo 0.3?** Decide before the Tenon rewrite.
>    - a. The shaped oymomo program
>    - b. LLVM IR, after LLVM's optimizer (`llvm_translate → LLVM IR → spindle_compile`)

## Dependencies

- Step 6 needs [plan_memory.md](implemented/plan_memory.md) steps 2 and 3, which needed step 3.
- Steps 1, 2: nothing new in reduction or BANF.
- Fibers from oymomo, host function values: [plan_c_interop.md](plan_c_interop.md) 1.6.

## Background (for agents)

Context kept for reference; not needed to follow the plan.

### Name

A drop spindle is a stick until a hand spins it; the VM is inert bytecode until the
host resumes it, on the host's data. And a spindle spins fibers. Modules:
`spindle.py`, `spindle_bytecode.py`, `spindle_compile.py`, `spindle_lib.py`,
`spindle_layout.py`. The symbol table keeps a non-Spindle name (`vm_symbols.py`,
`VmCall`): reduction and LLVM read it too.

### Prior art

| Like | What we take |
|---|---|
| Lua | VM is a host value, no globals; a fiber (`lua_State`) is created, resumed, yields; host functions call back in; yields cross them by continuation (5.2 `lua_callk`) |
| Wren | stack machine: params and lets are slots in a window of one value stack per fiber |
| wasm3 | pure interpreter, no JIT; bytecode checked once at load, loop checks only fuel and traps |

### Example

```
module~{main = => 'i32', putchar = {c = 'i32'} => 'i32', ask = {c = 'i32'} => 'i32'} -> {
  main = f -> {
    entry = args~{n = 'i32'} ->
      let q = module.putchar {c = [68000000]~'i32'} in
      let a = module.ask {c = $seq {q, args.n}} in
      let r = 'ctpop' {'i32', a} in
      'add' {'i32', r, [01000000]},
  },
}
```

```python
program = spindle_compile.compile(banf_translate.convert(term))
output = []
machine = spindle.Spindle(program, symbols=spindle_lib.default(), imports={
    'putchar': lambda fiber, c: output.append(c) or c,
    'ask': lambda fiber, c: spindle.Yield(c),   # suspend; the resumed value is the result
})
fiber = machine.fiber('main', [7])
fiber.resume()     # Yielded(7), and output == [0x68]
fiber.resume(15)   # Returned(5): ctpop(15) + 1
```

`'add'` runs in the core, `'ctpop'` (LLVM `llvm.ctpop`) in `spindle_lib`; reduction
folds both on literals. Imports are bound by the host (VM) or linker (LLVM). `ask`
yields; the next `resume` gives its result. `$seq` is plan_memory step 1.

### Pipeline option B

```
convert(term) → BANF → verify → llvm_translate → LLVM IR → spindle_compile → bytecode → Spindle(program, host) → fiber.resume
                                                         ↘ JIT / object file
```

Leverages LLVM's optimizer.

### Notes on the decisions

- 1: not oymomo terms (no blocks, calls, effect order) and not BANF directly.
- 2: `iN` is what `opcodes.evaluate` takes and gives; the VM moves host values and
  passes them to host functions, never looks inside. Little-endian as every byte
  array ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)).
- 3: jump-then-store-last-to-first makes `jump loop(b, a)` into `loop(a, b)` correct.
  The core is the ten instructions and nothing else.
- 4: division by zero, shift by width or more: LLVM undefined/poison; reduction
  doesn't fold these either.
- 5: deep recursion costs memory, not Python depth. Fuel is both a test's guard
  against endless loops and the host's time-slicing.
- 6: struct-as-host-call is how the VM has no data structures; an embedder may make a
  struct anything. A host may replace any default symbol.
- 7: entry fields:

  | Field | Meaning |
  |---|---|
  | `params` | LLVM operand order, each named; a form param (decision 10) or a value param with fixed form (`'ptr'`) or named by a form param |
  | `result` | fixed or named by a form param |
  | `accepts` | allowed forms per form param: `'add' takes an integer form, got ptr.` |
  | `pure` | reads and writes only its arguments and result |
  | `core` | run by the core as `op`; else a host function |
  | `run` | Python function on Python values: core `op`, `spindle_lib` default, and fold |
  | `llvm` | LLVM lowering, or `None` |

  `'sub' {'i32', x, y}` is `x - y` as LLVM's `sub i32 %x, %y`; a form param sits where
  LLVM writes the type. `'sub' {form = 'i32', subtrahend = x, minuend = y}` is still
  `x - y`. Optional params are left off the end (`'alloca' {form, count}`). Drops
  [notes.md › Labels fit the op](notes.md#fields-are-positional-in-llvms-order): the order to remember is
  LLVM's, shown by BANF and LLVM printouts. Also why plan_memory decision 8 writes
  aggregate types as tagged structs (`{'array', count, element}`), not `'array' {...}`
  (that shape is a call).
- 8: replaces per-opcode rules of [plan_constant_folding.md](implemented/plan_constant_folding.md).
  Impure symbols stay calls, ordered by `$seq` like imports. Reads only literals, so
  commutes with reduction ([plan_confluence.md](plan_confluence.md)). `vm_symbols.py`
  imports only `terms` so `reduction` can use it; LLVM lowerings live in
  `llvm_opcodes.py`, keyed by name, keeping llvmlite out. A host that replaces a
  symbol can't change what reduction computes.
- 9: a VM symbol is a function on values, so no `$`. `$fix`: rule on terms;
  `$struct_to_fields`/`$fields_to_struct`: rewrite terms, gone before BANF; `$seq`:
  gives its last field only once the others are literals, `convert` drops a stuck one.
- 10: form params are the other exception (with `$seq`) to
  [notes.md › Operands must be atoms](notes.md#operands-must-be-atoms). Per-predicate
  names (vs LLVM's one `icmp` with a predicate field) keep `icmp_ugt` (unsigned
  greater) distinct from `fcmp_ugt` (unordered or greater)
  ([plan_floats.md](plan_floats.md)); BANF prints `icmp slt i32 a, b`. Monomorphic
  per [notes.md › Monomorphic](notes.md#polymorphic-in-form): the form
  just moves into a field. A literal takes its form from `form`, as bare literals did
  (`$add_i8 {a = [ff], b = [01]}`); a byte array is never widened.
  [notes.md › BANF](notes.md#banf)'s "ops carry no form, as in Cranelift" no longer
  holds for `VmCall`.
- 11: integer arithmetic, bitwise, comparisons, `zext`, `sext`, `trunc` are core; the
  core doesn't grow with the table (`ctpop`, floats, memory are host functions).
- 12: two `Spindle`s share nothing. `'suspended'` = new, yielded or out of fuel;
  `'normal'` = resumed another fiber; `'dead'` = returned or failed. Errors:
  `SpindleError: cannot resume a running fiber.`,
  `SpindleError: 'main' yielded, but machine.call can't resume it.` `fiber.frames()`
  lists `(function, block)` from the top; `fiber.host` is Lua's extra space, used by
  host libraries (decision 17).
- 13: args come as VM values in field order. `Yield`: `resume` returns `Yielded(value)`;
  next `resume(v)` calls `k(fiber, v)`, or with no `k`, `v` is the result. `Call`: runs
  a program function on the same fiber and loop; result to `k`, or is the result. The
  host function returns before the VM runs anything, so nothing on the Python stack
  unwinds. Exceptions are chained and carry `fiber.frames()`.
- 14:

  ```python
  def twice(fiber, x):        # nested: simple, but nothing inside may yield
      return fiber.call('double', [fiber.call('double', [x])])

  def twice_k(fiber, x):      # through the loop: anything inside may yield
      return spindle.Call('double', [x], lambda fiber, y: spindle.Call('double', [y]))
  ```

  `fiber.call` is `lua_call`, runs above the host function's frame; depth limit is
  Lua's `LUAI_MAXCCALLS`: `SpindleError: host calls nested deeper than 200.` A yield
  (or fuel out) inside:
  `SpindleError: 'ask' yielded inside fiber.call from host function 'twice'; return spindle.Call(...) to let it yield.`
  An error raises in the host function with nested frames popped; caught, the fiber
  goes on (Lua's `pcall` for free); uncaught, it dies.
- 15: no `yield` instruction; a program yields via an import or symbol returning
  `Yield`. `'yield'` gives back what `resume` was given, so the host drives a fiber as
  a generator. Function values: [plan_c_interop.md](plan_c_interop.md) 1.6.
- 16: load checks, as wasm3 validates: jump targets in range, equal stack depth at
  every label along every path and within `max_stack`, arity of every `call`/`host`,
  every binding present. `Program`: opcodes of fixed size with immediates; function
  table (entry, arity, slots, `max_stack`); host slots (name, arity). A fiber is one
  value list and one frame list of `(function, pc, base)`. Loop is `while` over
  `match`; no closures, generators or exceptions in the core except host
  continuations (in C: function pointer and context). C loop may be `switch`,
  computed `goto`, or wasm3 tail-call threading.
- 17: plan_memory's entries. Sizes, alignment, padding from llvmlite's
  `get_abi_size`/`get_element_offset`; target byte order per plan_memory decision 12;
  so the VM and LLVM read the same bytes. `stacksave`/`stackrestore` are LLVM's
  `llvm.stacksave`/`llvm.stackrestore`, inserted on entry and before each return. Zero
  pointer faults; out of range is an error where LLVM is undefined.

### Step 3 as implemented

Old `$add_i32` names give a plain `Unknown built-in '$add_i32'.` with no hint of the new
spelling; an unaccepted form reads `'add': form must be one of i8, i16, i32, i64, got ptr.`

### Breaking changes

Only step 3: every opcode renamed, form as a field. Steps 1, 2, 4, 5, 6 break nothing
(`'name' {args}` was stuck in reduction and an error in `convert`).

| Before | After |
|---|---|
| `$add_i32 {a = x, b = y}` | `'add' {'i32', x, y}` |
| `$sub_i32 {minuend = x, subtrahend = y}` | `'sub' {'i32', x, y}` |
| `$zext_i8_i32 {value = x}` | `'zext' {'i8', x, 'i32'}` |
| BANF `add_i32 x, y` | BANF `add i32 x, y` |

The plan intended the old names' error to name the new spelling (design step 3).

### Tests per step

- **1:** every BANF op/terminator → decision 3's instructions; slots for params and
  block params; two-param jump pushes two, sets two; swap is correct; `GetField` →
  `const i; host 'field', 2`; `max_stack` is the deepest operand stack. Each `.banf`
  golden gets a `.spindle` listing. notes.md: VM section (pipeline, instructions, frame window).
- **2:** each opcode on edge operands (0, 1, top bit, all ones) matches
  `opcodes.evaluate`; sum 1..n loop; recursion 10000 deep; `udiv` by zero kills the
  fiber; endless loop → `OutOfFuel()`, resumable; unbound import error; bad bytecode
  (jump out of range, uneven depth) rejected; imports reach the host; two `Spindle`s
  independent. Callbacks: three-deep `fiber.call` chain; past `max_host_depth` errors;
  caught error lets the fiber go on; `Call(f, args, k)` gives `k` the result.
  Differential: every golden and JIT-run `llvm_translate_test` program matches.
  notes.md: values, `Spindle`/`Fiber`, host functions, callbacks, traps, fuel.
- **3 (done):** every `run` matches old `evaluate` on edge operands (old table as
  oracle); `'add' {'i32', [01000000], [02000000]}` → `[03000000]~'i32'`; variable
  stays; form computed by β (`(f -> 'add' {f, ...}) 'i32'`) folds; non-literal form
  stays; `add i32 n, ...`, `zext i8 x to i32`; mislabelled `'sub'` subtracts by
  position; every message of decisions 7, 10; core → `op`, non-core → `host`;
  `test_fold_matches_llvm` over the table; lowerings match; all old tests pass.
  notes.md: Opcodes, Built-ins (four `$`), `VmCall`, folding, the core line.
- **4:** goal program with `'ctpop'` as identity yields `7`, resumed with `15` returns
  `16`; generator 0..4 over five resumes then `Returned`; yield crosses a host `Call`,
  `k` runs after resume; yield in `fiber.call` errors; resuming running/dead errors;
  resuming another fiber sees its yields, own status `'normal'`. notes.md: coroutines,
  `Yield`, `Call`, continuations.
- **5:** `'ctpop' {'i32', 7}` is 3; `trace` records and returns; two `trace`s with
  `$seq` in order; rebinding `'ctpop'` changes the VM, not folding; `ctpop` folds,
  `trace` never; `ctpop` → `call i32 @llvm.ctpop.i32`, same under JIT; `trace` in LLVM
  errors; golden `vm_symbol.oymo` runs the goal program. notes.md: VM-only symbols,
  `spindle_lib`.
- **6:** layout of `{i8, i32}`, `<{i8, i32}>`, `[3 x i32]` matches llvmlite; plan_memory's
  goal gives 42; store `'i32'`, load `'i8'` gives target's low/high byte; out-of-bounds
  errors; `alloca` freed on return; two fibers' `alloca`s don't overlap; differential
  on memory programs. notes.md: memory. Then mark this plan **implemented**.

### Verification

`hatch run full-check` after every step. Final: every JIT-run test program gives the
same result in the VM; the goal program calls `putchar` once, yields `7`, and resumed
with `15` returns `5`.
