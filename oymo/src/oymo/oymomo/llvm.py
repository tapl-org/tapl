# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from llvmlite import ir

# 1. Create a new module container
module = ir.Module(name='main_module')

# 2. Define the types (32-bit integer)
int_type = ir.IntType(32)

# 3. Define the function type for main: returns i32, takes no arguments
func_type = ir.FunctionType(int_type, [])

# 4. Declare the "main" function
main_func = ir.Function(module, func_type, name='main')

# 5. Create a basic entry block and instruction builder
block = main_func.append_basic_block(name='entry')
builder = ir.IRBuilder(block)

# 6. Generate the return statement with a constant value of 0
zero_constant = ir.Constant(int_type, 0)
builder.ret(zero_constant)

# 7. Print the generated LLVM IR
print(str(module))
