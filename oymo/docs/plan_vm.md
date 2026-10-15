# Plan: Spindle, a virtual machine that runs BANF without LLVM

Status: **paused**, with open questions; 1 of 6 steps.

> [!NOTE]
> Step 3 was done ahead of the rest, with no VM code, under the name **opcode**: the
> table is `opcodes.py` (`Opcode`, `OPCODES`), the BANF op is
> `OpcodeCall(opcode, forms, args)`, an entry computes with `evaluate`, and reduction
> folds through `reduction.fold_opcode`. Where this plan says *VM symbol*, `vm_symbols.py`,
> `VmSymbol`, `VmCall` or `run`, read *opcode*, `opcodes.py`, `Opcode`,
> `OpcodeCall` or `evaluate`. Old `$add_i32` names are a plain
> `Unknown built-in '$add_i32'.`, with no hint of the new spelling, and an unaccepted
> form reads `'add': form must be one of i8, i16, i32, i64, got ptr.`

## Steps

One commit each. Details are in [Implementation steps](#implementation-steps).

- [ ] 1. Stack bytecode, and a compiler from BANF to it (`oymomo: add VM bytecode`)
- [ ] 2. The VM: `Spindle` and `Fiber` objects, host functions, host calls back into the VM (`oymomo: add the VM`)
- [x] 3. Opcodes are VM symbols, polymorphic in `form`: `$add_i32 {a, b}` becomes `'add' {'i32', a, b}`, fields in LLVM's order (`oymomo: opcodes are VM symbols`) — **breaking**
- [ ] 4. Coroutines: a host function yields the fiber, the host resumes it, yields cross host calls by continuations (`oymomo: VM coroutines`)
- [ ] 5. VM symbols that are not LLVM instructions: `'ctpop'`, `'trace'`, as host functions (`oymomo: add VM-only symbols`)
- [ ] 6. Memory as a host library (`oymomo: add memory to the VM`)

Steps 1 and 2 need nothing new in reduction or BANF: the VM runs the BANF that
LLVM gets today. Step 3 is the one breaking step: it renames every opcode, moves
`opcodes.py`, constant folding and `llvm_opcodes.py` into one table, and makes the
form an operand. [plan_memory.md](plan_memory.md) steps 2 and 3 need step 3 (memory
ops are entries of its table), and step 6 needs them.

## Goal

**A verified BANF module runs in Python, with the same results as under LLVM, in a
VM that is tiny and embedded like Lua.** The VM knows integers, control flow and
calls; everything else (structs, memory, imports, coroutine scheduling) is a host
function. Its state is a pair of host objects, `Spindle` and `Fiber`, that the host
creates, runs, resumes, and calls into from inside its own functions.

**Why "Spindle".** A drop spindle is a stick until a hand spins it: it holds nothing
and makes nothing; the spinner gives it motion and the fleece its material. So is
this VM without a host: inert bytecode that runs only when the host resumes it, on
the host's data. And a spindle spins fibers. Its modules are `spindle.py`,
`spindle_bytecode.py`, `spindle_compile.py`, `spindle_lib.py`, `spindle_layout.py`.
The table of VM symbols keeps its name (`vm_symbols.py`, `VmCall`): reduction and
LLVM read it too, so it is not Spindle's alone.

```
convert(term) → BANF → verify → spindle_compile → bytecode → Spindle(program, host) → fiber.resume
                              ↘ llvm_translate → LLVM IR → JIT / object file
```

OR

```
convert(term) → BANF → verify → llvm_translate → LLVM IR -> spindle_compile → bytecode → Spindle(program, host) → fiber.resume
                                                         ↘ JIT / object file
```

In the later case, we can leverage LLVM optimizer.

| Like | What we take |
|---|---|
| Lua | The VM is a value in the host, with no globals; a fiber (Lua's `lua_State`) is created, resumed and yields; host functions call back into the VM, and a yield crosses them by a continuation (Lua 5.2's `lua_callk`) |
| Wren | A stack machine: a function's params and lets are slots in its window of one value stack per fiber |
| wasm3 | A pure interpreter: no JIT, no code generated at run time; bytecode is checked once at load, so the loop checks nothing but fuel and traps |

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

`'add'` is LLVM's `add`, run by the VM core; `'ctpop'` is LLVM's `llvm.ctpop`, run by
a host function from `spindle_lib`; with literal arguments reduction folds both
(decision 8). `module.putchar` and `module.ask` are imports: the host binds them in
the VM, the linker in LLVM. `ask` yields: the fiber stops, `resume` returns to the
host, and the next `resume` gives the call its result. (`$seq` is
[plan_memory.md](plan_memory.md) step 1.)

## Decisions

### What the VM runs (steps 1, 2)

1. **The VM runs bytecode compiled from verified BANF.** Not the oymomo terms (oymomo
   has no blocks, no calls, no effects order) and not BANF directly: compiling
   resolves every name to a slot and every block label to an offset once, so the
   interpreter loop does no lookups. `spindle_compile` takes only modules that
   `banf_terms.verify` accepts, so it never checks a form.
2. **The VM knows integers; every other value is the host's.** An integer of form
   `iN` is a Python `int`, unsigned, below `2^N`, which is what `opcodes.evaluate`
   takes and gives. Any other value on the stack (a struct, a pointer, a fiber) is
   an opaque host value: the VM moves it, passes it to host functions, and never
   looks inside. Constants are decoded once, at compile time, little-endian as
   every byte array
   ([notes.md › Byte arrays are always little-endian](notes.md#byte-arrays-are-always-little-endian)).
3. **The bytecode is a stack machine, as Wren's.** Each function is a flat list of
   instructions. A fiber has one value stack; a frame is a window of it, whose first
   slots are the function's params (the caller pushed them), then one slot per
   block param and let, then the operand stack. A jump pushes its args, then stores
   them into the target's params last to first, so a parallel move (a swap
   `jump loop(b, a)` into `loop(a, b)`) needs no temporaries.

   | Instruction | Stack | BANF |
   |---|---|---|
   | `const k` | → v | a constant atom, defined data |
   | `get s` | → v | a variable |
   | `set s` | v → | a let, a block param |
   | `op o` | a... → r | `OpcodeCall` (a core `VmCall` from step 3) |
   | `call f` | a... → r | `Call` to a function |
   | `host h, n` | a... → r | `Call` to an import; `MakeStruct`, `GetField`, `GetIndex`; a non-core `VmCall` (step 3) |
   | `jump L` | | `Jump`, after its moves |
   | `jump_if L` | c → | `Branch`: to `L` on `c != 0`, else the next instruction |
   | `switch n, L0 ... Ln` | s → | `Switch`: the `s`-th target, or the last |
   | `return` | r → | `Return`: pop the frame, push `r` in the caller's |

   Each edge of a `Branch` or `Switch` with moves gets a stub (moves, then `jump`).
   Ten instructions: the core is these, and nothing else.
4. **An operation whose result LLVM leaves undefined stops the VM.** Where
   `opcodes.evaluate` gives `None` (division by zero, a shift by the width or more),
   LLVM's result is undefined or poison; the VM raises
   `SpindleError: udiv i32: division by zero, in 'main' block 'entry'.` rather than pick a
   value. Reduction already doesn't fold these.
5. **VM calls don't use the Python stack; fuel suspends.** The interpreter is one
   loop over the fiber's frames, so a deep oymomo recursion costs memory, not Python
   recursion depth. Only a host function calling back into the VM nests a loop
   (decision 14). `resume` takes `fuel`, the number of instructions it may run; past
   it the fiber stops between two instructions and `resume` returns `OutOfFuel()`.
   The next `resume` goes on where it stopped, so fuel is both a test's guard against
   an endless loop and the host's way to time-slice fibers.

### Host functions and VM symbols (steps 2, 3, 5)

6. **Two kinds of host function: imports and VM symbols; both bound by the host.**
   - An **import** (`module.putchar {...}`) is declared by the program, as today, and
     bound by whoever runs it: in the VM, by `Spindle(..., imports={'putchar': f})`; in
     LLVM, by the linker. Imported data is bound the same way, to a value.
   - A **VM symbol** (`'add' {...}`) is the same in every program, from the fixed
     table in `vm_symbols.py`. The core runs the integer ones (decision 11); every
     other symbol is a host function in `Spindle(..., symbols=...)`. `spindle_lib.default()`
     binds each to the table's `run`; a host may replace any.
   - The compiler emits two symbols of its own: `'struct'` for `MakeStruct` and
     `'field'` for `GetField` and `GetIndex` (the index pushed as a constant).
     `spindle_lib.default()` makes a struct a Python tuple. This is how the VM has no data
     structures: a host that embeds the VM can make a struct anything it likes.

   `Spindle(...)` checks that every import and symbol the program calls is bound:
   `SpindleError: import 'putchar' is not bound.`, `SpindleError: symbol 'ctpop' is not bound.`
7. **A VM symbol is called as a byte array applied to a struct.** `'name' {args}` is
   `Apply(ByteArray, Struct)`, a shape reduction already leaves stuck (no rule
   matches a byte array in function position), so it needs no new term. Each table
   entry has:

   | Field | Meaning |
   |---|---|
   | `params` | in LLVM's operand order, each with a name for messages and docs; each a **form param** (decision 10) or a value param, whose form is fixed (`'ptr'`) or named by a form param (`form`) |
   | `result` | the result form, fixed or named by a form param |
   | `accepts` | which forms each form param may be: `'add' takes an integer form, got ptr.` |
   | `pure` | it reads and writes nothing but its arguments and result |
   | `core` | the VM core runs it as `op`; otherwise it is a host function (decision 6) |
   | `run` | the Python function on Python values (decision 2): the core's `op`, `spindle_lib`'s default, and reduction's fold |
   | `llvm` | how LLVM lowers it, or `None` |

   `convert` turns `'name' {...}` into a BANF op `VmCall(name, forms, args)`: the
   form params, read as literal forms, and the value args as atoms. It is printed as
   LLVM writes the instruction: `add i32 a, b`, `zext i8 x to i32`.

   **Fields are positional, in LLVM's operand order, and labels are ignored**, as in
   `$seq` and in a branch. `'sub' {'i32', x, y}` is `sub i32 x, y`, `x - y`,
   because LLVM writes `sub i32 %x, %y`; a form param sits where LLVM writes the
   type. Only the number of fields is checked: `'sub' takes 3 fields, got 2.`
   Optional params come last (`'alloca' {form, count}`), so leaving one out is
   leaving off the end. A label is free to write and means nothing:
   `'sub' {form = 'i32', subtrahend = x, minuend = y}` is still `x - y`. This drops
   [notes.md › Labels fit the op](notes.md#labels-fit-the-op): the order to
   remember is LLVM's, which the BANF and LLVM printouts show.

   A name not in the table is `Unknown VM symbol 'foo'.`; in LLVM, a symbol with no
   `llvm` is `'name' runs only in the VM.` This is also why decision 8 of
   [plan_memory.md](plan_memory.md) writes LLVM's aggregate types as tagged structs
   (`{'array', count, element}`) and not as `'array' {...}`: that shape is a call.
8. **Reduction folds a pure VM symbol on literal arguments**, one rule for every
   symbol: when the name is a pure symbol, every form param is a literal form it
   folds on (integer forms, for now), and every value param a literal of its form,
   `run` gives the result, formed as `result`. This is today's constant folding
   ([plan_constant_folding.md](implemented/plan_constant_folding.md)) with the
   per-opcode rules replaced by this one. An impure symbol never
   folds; it stays a call, ordered by `$seq` like an import. The rule reads only
   literals, so it commutes with reduction, as [plan_confluence.md](plan_confluence.md)
   asks of every built-in rule. `vm_symbols.py` imports only `terms`, so `reduction` can
   use it; LLVM lowerings are attached in `llvm_opcodes.py`, keyed by name, so the
   table stays free of llvmlite. Folding uses `run` from the table, never the host's
   binding, so a host that replaces a symbol can't change what reduction computes.
9. **`$` is kept only where reduction or `convert` treats a term specially.** A VM
   symbol is a function on values, so it has no `$`. What keeps it:

   | Built-in | Why it isn't a VM symbol |
   |---|---|
   | `$fix` | a reduction rule on terms, not values |
   | `$struct_to_fields`, `$fields_to_struct` | they rewrite terms, and must reduce away before BANF |
   | `$seq` | gives its last field only once the others are literals, and `convert` drops a stuck one ([plan_memory.md](plan_memory.md)) |

### Opcodes polymorphic in `form` (step 3)

10. **The form is an operand, not part of the name.** One symbol per LLVM
    instruction, as LLVM writes `add i32 %a, %b`. A **form param** must reduce to a
    literal form; it is a form, not an operand, so it stays in place and is never
    let-bound (the other exception to
    [notes.md › Operands must be atoms](notes.md#operands-must-be-atoms), with
    `$seq`).

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
      accepted wherever LLVM accepts one; reduction folds only scalar integer forms.
    - **BANF ops carry their form params**, as LLVM's instructions carry their type.
      [notes.md › BANF](notes.md#banf)'s "ops carry no form, as in Cranelift" no
      longer holds for `VmCall`.
11. **The table replaces three files, and draws the core's line.** `opcodes.py`'s
    generated names become about 25 entries; `opcodes.evaluate` becomes each
    entry's `run`; `llvm_opcodes.py`'s builders become each entry's `llvm`.
    `OpcodeCall` becomes `VmCall`. The entries that were opcodes (integer
    arithmetic, bitwise, comparisons, `zext`, `sext`, `trunc`) are `core`: the VM
    runs them as `op`, with no host call. Every symbol added later (`ctpop`,
    floats, memory) is a host function unless it is moved into the core on
    purpose, so the core does not grow with the table.

### The VM as a host object (steps 2, 4)

12. **The VM's state is two host objects, and nothing global.** As Lua splits
    `global_State` from `lua_State`:
    - `Spindle(program, symbols, imports)` holds the loaded program and the bindings,
      shared by its fibers. Two `Spindle`s share nothing.
    - `Fiber`, from `machine.fiber(function, args)`, holds a value stack, a frame stack,
      and a status: `'suspended'` (new, yielded, or out of fuel), `'running'`,
      `'normal'` (it resumed another fiber, which is running), `'dead'` (returned or
      failed). `fiber.resume(value=None, fuel=None)` runs it and returns
      `Returned(value)`, `Yielded(value)` or `OutOfFuel()`; an error raises
      `SpindleError` and leaves it dead. Resuming a fiber that isn't suspended is
      `SpindleError: cannot resume a running fiber.`
    - `fiber.frames()` lists `(function, block)` from the top, for messages and
      debuggers; `fiber.host` is a slot the host may set (Lua's extra space), where
      a host library keeps per-fiber state (decision 17).
    - `machine.call(function, args, fuel=None)` is the short form: a new fiber, resumed to
      the end; a yield is `SpindleError: 'main' yielded, but machine.call can't resume it.`
13. **A host function is a Python function `f(fiber, *args)`.** It gets the fiber it
    runs on and the args as VM values, in field order, and returns one of:

    | Return | The fiber |
    |---|---|
    | a value | goes on, with the value as the call's result |
    | `Yield(value, k=None)` | stops; `resume` returns `Yielded(value)`; the next `resume(v)` calls `k(fiber, v)`, and with no `k`, `v` is the call's result |
    | `Call(function, args, k=None)` | calls a program function on the same fiber, in the same loop; its result `r` goes to `k(fiber, r)`, or with no `k` is the call's result |

    `k` returns any of the three again, so a host function is a chain of steps.
    This is Lua 5.2's continuation (`lua_KFunction`) without `longjmp`: the host
    function returns before the VM runs anything else, so nothing on the Python
    stack has to be unwound. A Python exception from a host function is
    `SpindleError: host function 'putchar' failed: ...`, chained, with `fiber.frames()`.
14. **A host function may call back into the VM, recursively.** Two ways:

    ```python
    def twice(fiber, x):        # nested: simple, but nothing inside may yield
        return fiber.call('double', [fiber.call('double', [x])])

    def twice_k(fiber, x):      # through the loop: anything inside may yield
        return spindle.Call('double', [x], lambda fiber, y: spindle.Call('double', [y]))
    ```

    - `fiber.call(function, args)` runs a nested loop on the same fiber, above the
      host function's frame, and returns the result, as `lua_call`. The VM may call
      the host again inside it, to any depth up to `Spindle(..., max_host_depth=200)`
      (Lua's `LUAI_MAXCCALLS`): `SpindleError: host calls nested deeper than 200.` A
      yield inside is
      `SpindleError: 'ask' yielded inside fiber.call from host function 'twice'; return spindle.Call(...) to let it yield.`,
      and so is running out of fuel inside.
    - `Call(...)` (decision 13) nests nothing: the loop runs the call and then
      `k`. A host function that may run code that yields uses it.
    - An error inside `fiber.call` raises `SpindleError` in the host function, with the
      nested frames already popped: a host function that catches it goes on, and
      the fiber with it (Lua's `pcall`, for free). Uncaught, it kills the fiber.
    - A host function may also resume *another* fiber; that nests a loop too, and
      its fiber is `'normal'` meanwhile.
15. **Coroutines are host functions, not instructions.** The core has no `yield`:
    a program yields by calling an import or symbol whose host function returns
    `Yield`. `spindle_lib.coroutines()` gives `'yield' {form, value}`, which yields
    `value` and gives back what `resume` was given, so the host can drive a fiber as
    a generator. Creating and resuming fibers from oymomo code needs function values
    ([plan_c_interop.md](plan_c_interop.md) 1.6): until then, only the host does.
16. **A pure interpreter, written so a C port is a straight translation.**
    - **No JIT, nothing generated at run time.** `Spindle(...)` checks the bytecode once,
      as wasm3 validates at load: every jump target in range, the stack depth at
      every label the same along every path and within the function's
      `max_stack`, every `call` and `host` of the right arity, every binding
      present. The loop then checks only fuel and traps.
    - **Plain data.** A `Program` is a code array of integers (an opcode, then its
      immediates, each opcode of a fixed size), a constant pool, a function table
      (entry, arity, slots, `max_stack`) and a table of host slots (name, arity).
      A fiber is one value list and one frame list of `(function, pc, base)`
      records. The loop is a `while` over a `match` on the opcode. No Python
      closures, generators or exceptions in the core, except host continuations,
      which in C are a function pointer and a context.
    - In C, the loop is a `switch`, computed `goto`, or wasm3's tail-call threading
      over pre-decoded handlers; the bytecode allows each, since every opcode has a
      fixed size and every check was done at load.

### Memory (step 6)

17. **Memory is a host library; the VM never learns of it.** `spindle_lib.memory(layout)`
    binds `'alloca'`, `'getelementptr'`, `'load'`, `'store'`
    ([plan_memory.md](plan_memory.md)'s entries) to one `bytearray` per `Spindle`; a
    pointer is an `int` offset into it, an ordinary integer to the VM. It is laid out
    as LLVM lays it out for the target: sizes, alignment and struct padding come from
    LLVM's data layout (llvmlite's `get_abi_size` and `get_element_offset` on the
    target data), and byte order is the target's, as [plan_memory.md](plan_memory.md)
    decision 12 says. So a program that reads memory reads the same bytes in the VM
    and under LLVM.
    - `alloca` takes space from a per-fiber stack area, kept in `fiber.host`. A
      function that calls `alloca` is compiled with `'stacksave'` on entry and
      `'stackrestore'` before each return (LLVM's `llvm.stacksave` and
      `llvm.stackrestore`), two more symbols of the library, so memory is given back
      on return without the VM knowing.
    - Offset 0 is never handed out, so a stray zero pointer faults. An access outside
      what was allocated is
      `SpindleError: load of 4 bytes at 0x10 is outside memory.` where LLVM would be
      undefined.

---

## Design

### A. Bytecode and compiler (step 1)

| Module | Change |
|---|---|
| `spindle_bytecode.py` (new) | the opcodes of decision 3 and their sizes; `Function(name, arity, slots, max_stack, entry)`, `HostSlot(kind, name, arity)`, `Program(code, constants, functions, host_slots, data)`; `show(program)`, an assembly listing with block labels |
| `spindle_compile.py` (new) | `compile(module) -> Program`: a slot per param, block param and let, in order; operands pushed, the result `set`; jumps push args then `set` last to first; branch and switch edges with moves get stubs; labels to offsets in a second pass; `max_stack` per function; `MakeStruct` is `host 'struct', n`, `GetField` `const i; host 'field', 2` with `banf_terms.field_index`; constants decoded with their form |

### B. The VM (step 2)

| Module | Change |
|---|---|
| `spindle.py` (new) | `Spindle(program, symbols, imports, max_host_depth)`, which checks the bytecode and bindings (decision 16); `Fiber` with `resume`, `call`, `status`, `frames`, `host`; `Returned`, `OutOfFuel`, `Call`; `SpindleError` with the function and block; `op` runs `opcodes.evaluate` |
| `spindle_lib.py` (new) | `default()`: `'struct'` (a tuple) and `'field'` (an index); later steps add to it |

### C. Opcodes are VM symbols (step 3)

| Module | Change |
|---|---|
| `vm_symbols.py` (new) | `VmSymbol(name, params, result, accepts, pure, core, run)`, `VM_SYMBOLS`; one entry per LLVM instruction of decision 10, all `core`, `run` taken from `opcodes.evaluate`'s templates |
| `opcodes.py` | removed; `bit_width` and `byte_width` move to `vm_symbols.py` |
| `reduction.py` | `_fold` rules replaced by one rule for `Apply(ByteArray, Struct)` (decision 8) |
| `banf_shape.py` | a VM symbol call: form params reduced to normal form in place, value params reduced as atoms |
| `banf_terms.py` | `OpcodeCall(opcode, args)` → `VmCall(symbol, forms, args)`; `form_of` from `result`; verifier from `params` and `accepts`; printed as LLVM writes it |
| `banf_translate.py` | `'name' {...}` read as `VmCall`; `$name` is only `$fix`, `$struct_to_fields`, `$fields_to_struct`, `$seq`; any other `$name` is `Unknown built-in '$add_i32'; opcodes are VM symbols now: 'add' {'i32', a, b}.` |
| `llvm_opcodes.py` | builders keyed by symbol name, taking the form params |
| `printer.py` | prints `'add' {'i32', x, y}` |
| `spindle_compile.py` | a `core` `VmCall` is `op`, any other `host`, with its form params as immediates |
| `spindle.py` | `op` runs the entry's `run` |
| `spindle_lib.py` | `default()` binds every non-`core` entry to its `run` (none yet) |
| tests, goldens, `docs/notes.md` | every `$name_iN` rewritten |

### D. Coroutines (step 4)

| Module | Change |
|---|---|
| `spindle.py` | `Yield`; `resume(value)` after a yield; `k` in `Yield` and `Call`; `'normal'` status; the errors of decision 14 for a yield or fuel out inside `fiber.call` |
| `vm_symbols.py` | `yield` (form param `form`, `value`, impure, not `core`; no `llvm`) |
| `spindle_lib.py` | `coroutines()`: `'yield'` |

### E. VM-only and intrinsic symbols (step 5)

| Module | Change |
|---|---|
| `vm_symbols.py` | `ctpop` (form param `form`, `value`, pure, not `core`; LLVM `llvm.ctpop`) and `trace` (form param `form`, `value`, impure, not `core`; no `llvm`) |
| `spindle_lib.py` | `default()` binds `ctpop`; `tracer(out)` binds `'trace'` to append to the host's list `out` and give `value` back |
| `llvm_translate.py` | a `VmCall` with no lowering is `'trace' runs only in the VM.` |

### F. Memory (step 6)

| Module | Change |
|---|---|
| `spindle_layout.py` (new) | size, alignment and field offsets of a form, from llvmlite's target data, so the VM and LLVM share one layout |
| `spindle_lib.py` | `memory(layout)`: `'alloca'`, `'getelementptr'`, `'load'`, `'store'`, `'stacksave'`, `'stackrestore'` on one `bytearray`; loads and stores encode and decode in the target's byte order |
| `spindle_compile.py` | `'stacksave'` and `'stackrestore'` around a function that calls `'alloca'` |

---

## Breaking changes

Step 3: every opcode is renamed and takes its form as a field.

| Before | After |
|---|---|
| `$add_i32 {a = x, b = y}` | `'add' {'i32', x, y}` |
| `$sub_i32 {minuend = x, subtrahend = y}` | `'sub' {'i32', x, y}` |
| `$zext_i8_i32 {value = x}` | `'zext' {'i8', x, 'i32'}` |
| BANF `add_i32 x, y` | BANF `add i32 x, y` |

The old names give an error that names the new spelling (design C). Steps 1, 2, 4, 5
and 6 break nothing: `'name' {args}` was stuck in reduction and an error in
`convert`.

---

## Open questions

> [!IMPORTANT]
> 1. **Trap or not** (decision 4). Stopping on an undefined operation makes the VM
>    stricter than LLVM, which is what tests want. A program that relies on what
>    LLVM happens to give would then run under LLVM and stop in the VM.
> 2. **Which VM-only symbols first** (step 5). `trace` is there for tests; Anvil's
>    layer-1 helpers (type values, errors) are the likely next users.
> 3. **Imports in `spindle_lib`.** Could `spindle_lib` give common imports (`putchar`,
>    `malloc`), so a test binds less? An import bound by no one is still an error.
> 4. **Function values.** A host function names program functions by name
>    (decision 14). Passing a function to the host as a value, and creating fibers
>    from oymomo, wait for function pointers
>    ([plan_c_interop.md](plan_c_interop.md) 1.6).
> 5. **A REPL and a CLI.** There is no driver yet. `oymo run --spindle a.oymo` and a REPL
>    that converts and runs one expression are the obvious users; a plan of their
>    own.
> 6. **Speed.** A Python loop is slow next to a JIT, and every struct and field is a
>    host call. Fine for tests; if Anvil's layer 1 runs in the VM at compile time,
>    `struct` and `field` could become core instructions, against "the VM has no
>    data structures".
> 7. **Values in a C port** (decision 16). An `iN` up to 64 bits fits a machine
>    word; wider integers and host values need handles, and someone must release a
>    handle a dead fiber held: the VM has no GC, so the host, when a fiber dies.

---

## Implementation steps

Each step is one commit and leaves `hatch run full-check` green. Each step updates
`docs/notes.md` for its own part.

### Step 1: stack bytecode and compiler

- A.
- Tests:
  - `spindle_compile`: every BANF op and terminator compiles to the instructions of
    decision 3; params and block params get slots; a jump to a block with two
    params pushes two and sets two; a swap (`jump loop(b, a)` into `loop(a, b)`)
    is still correct; `GetField` becomes `const i; host 'field', 2` with the
    field's position; `max_stack` is the deepest the operand stack gets.
  - goldens: each `.banf` golden gets a `.spindle` listing beside it.
- `docs/notes.md`: a VM section: the pipeline, the instruction table, the frame
  window.

Commit: `oymomo: add VM bytecode`

### Step 2: the VM

- B.
- Tests:
  - `spindle`: each opcode on edge operands (0, 1, the top bit, all ones) gives
    `opcodes.evaluate`'s result; a loop (sum 1 to n) gives the sum; a recursive
    function 10000 deep returns (no Python recursion); `udiv` by zero is `SpindleError`
    and kills the fiber; an endless loop returns `OutOfFuel()`, and resuming it
    with more fuel goes on from where it stopped; an unbound import is
    `import 'putchar' is not bound.`; bad bytecode (a jump out of range, uneven
    stack depth at a label) is rejected by `Spindle(...)`; an import reaches the host;
    two `Spindle`s of one program don't share state.
  - callbacks: a host function that `fiber.call`s a program function that calls
    the host again, three deep, gives the right result; past `max_host_depth` is
    `SpindleError`; an error inside `fiber.call` caught by the host function lets the
    fiber go on; `Call(f, args, k)` gives `k` the result.
  - differential: every golden and every program in `llvm_translate_test` that runs
    under the JIT gives the same result in the VM.
- `docs/notes.md`: values, `Spindle` and `Fiber`, host functions, callbacks, traps, fuel.

Commit: `oymomo: add the VM`

### Step 3: opcodes are VM symbols

- C.
- Tests:
  - `vm_symbols`: every entry's `run` gives what `opcodes.evaluate` gave for every
    old opcode, on edge operands (the old table is kept in the test as the oracle).
  - `reduction`: `'add' {'i32', [01000000], [02000000]}` folds to
    `[03000000]~'i32'`; with a variable it stays; with `form` computed by β
    (`(f -> 'add' {f, ...}) 'i32'`) it folds; with a non-literal form it stays.
  - `banf_translate`: `'add' {'i32', args.n, ...}` is `add i32 n, ...`;
    `'zext' {'i8', x, 'i32'}` is `zext i8 x to i32`; `'sub'` with labels written in
    the wrong order still subtracts by position; every message of decisions 7 and
    10 (field count, `accepts`, operand size, `to` width, unknown symbol);
    `$add_i32` names the new spelling.
  - `spindle_compile`: a `core` symbol is `op`; a non-`core` test symbol is `host`.
  - `llvm_translate`: `test_fold_matches_llvm` over the new table; every lowering
    matches the old one.
  - every existing test and golden passes after the rewrite.
- `docs/notes.md`: Opcodes rewritten (polymorphic in `form`, and why still strict);
  Built-ins lists only the four `$` built-ins; BANF's `VmCall`; folding; the core
  line.

Commit: `oymomo: opcodes are VM symbols`

### Step 4: coroutines

- D.
- Tests:
  - `spindle`: the goal program, with `'ctpop'` replaced by an identity, yields `7`,
    and resumed with `15` returns `16`; a generator (a loop that yields `i` for `i`
    in 0 to 4) gives 0 to 4 over five resumes, then `Returned`; a yield inside a
    host function's `Call` crosses it, and `k` runs after the resume; a yield inside
    `fiber.call` is the `SpindleError` of decision 14; resuming a running or dead fiber is
    `SpindleError`; a host function that resumes another fiber sees that fiber's yields,
    and its own fiber is `'normal'` meanwhile.
- `docs/notes.md`: coroutines, `Yield`, `Call`, continuations.

Commit: `oymomo: VM coroutines`

### Step 5: VM-only and intrinsic symbols

- E.
- Tests:
  - `spindle`: `'ctpop' {'i32', 7}` is 3; `trace` records its argument in the host's
    list and gives it back; two `trace`s chained with `$seq` record in order; a
    host that rebinds `'ctpop'` changes what the VM gives, not what reduction folds.
  - `reduction`: `ctpop` folds on a literal; `trace` never does.
  - `llvm_translate`: `ctpop` is `call i32 @llvm.ctpop.i32` and runs under the JIT
    with the VM's result; `trace` is `'trace' runs only in the VM.`
  - golden `vm_symbol.oymo`: the goal program, run to the end.
- `docs/notes.md`: VM-only symbols, `spindle_lib`.

Commit: `oymomo: add VM-only symbols`

### Step 6: memory

Needs [plan_memory.md](plan_memory.md) steps 2 and 3.

- F.
- Tests:
  - `spindle_layout`: sizes and offsets of `{i8, i32}`, `<{i8, i32}>`, `[3 x i32]` match
    llvmlite's for the host target.
  - `spindle`: the goal of [plan_memory.md](plan_memory.md) gives 42; a store of `'i32'`
    and a load of `'i8'` at the same pointer gives the target's low or high byte; an
    out-of-bounds load is `SpindleError`; memory from `alloca` is given back on return;
    two fibers' `alloca`s don't overlap.
  - differential: every memory program in `llvm_translate_test` gives the same
    result in the VM.
- `docs/notes.md`: memory in `spindle_lib`.
- Status of this plan: **implemented**.

Commit: `oymomo: add memory to the VM`

---

## Verification

After every step:

```
hatch run full-check
```

The final check: every program that runs under LLVM's JIT in the test suite runs in
the VM with the same result, and the goal program calls `putchar` once, yields `7`,
and resumed with `15` returns `5`.
