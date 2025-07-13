<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

### Why type is an expression?
because typeof operator returns expression
### Why we need complete type check before substitution?
The type of any expression (even for locks) can be universe. To prevent this $(\lambda x{:}\star. x\ 2{:}Nat)\ 3{:}Nat{:}*$
### What if we design term wrapped by type, and that type plays as term. For example: \x:Nat.x:x:* == (\x. x:x):(_:Nat.*)
In this case, we could not separate types from terms, and could not run types fully before running terms.

### What are the TAPL-specific methods or functions?
Methods, functions, fields, or any name that have the __tapl (double underscores followed by "tapl") suffix are specific to TAPL.

### What is the backend of TAPL?
Currently, Python's AST is used as the backend. However, in the near future, Tapl will introduce its own AST/IR/Language as the backend.
The new backend will be purely untyped and will be used solely for defining the computation. The new backend can be converted to other backends,
such as LLVM IR, JVM bytecode, Javascript, or it can run on its own interpreter. As a result, Tapl serves solely as a type introducer.

### Why do class type names have a underscore `_` suffix?
Because class type differes from its instance type. For example (in python code):
```
class Shape:
   def __init__(self, name: str):
      self.name = name
   def get(self):
      if (self):
        return self.name
      return 'shape'

print_class(Shape.get(None))
print_instance(Shape('square').get())
```

Output:
```
shape
square
```

In this example, `print_class` function takes a `Shape` class object, while `print_instance` takes a instance of `Shape` class.
To distinguish these two types with the same name, we can declare `print_...` functions like this in tapl:
```
def print_first(shape: Shape)
def print_instance(shape: Shape!)
```