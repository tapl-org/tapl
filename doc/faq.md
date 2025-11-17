<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

### Why type is an expression?
because typeof operator returns expression
### Why we need complete type check before substitution?
The type of any expression (even for locks) can be universe. To prevent this $(\lambda x{:}\star. x\ 2{:}Nat)\ 3{:}Nat{:}*$
### What if we design term wrapped by type, and that type plays as term. For example: \x:Nat.x:x:* == (\x. x:x):(_:Nat.*)
In this case, we could not separate types from terms, and could not run types fully before running terms.

### What is the backend of TAPL?
Currently, Python's AST is used as the backend. However, in the near future, Tapl will introduce its own AST/IR/Language as the backend.
The new backend will be purely untyped and will be used solely for defining the computation. The new backend can be converted to other backends,
such as LLVM IR, JVM bytecode, Javascript, or it can run on its own interpreter. As a result, Tapl serves solely as a type introducer.

### Why do class type names have a underscore `_` suffix?
Because class type differs from its instance type. For example (in python code):
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
To distinguish these two types with the same name, we can declare `print_...` functions like these in tapl code:
```
def print_first(shape: Shape)
def print_instance(shape: Shape_)
```

### Why the '|' and '&' Operators Are Not Bitwise Operations in TAPL
These single-symbol operators (| and &) are traditionally used as bitwise operations in many programming languages. However, in modern systems like TypeScript and Python, they have been naturally adopted to represent set-theoretic type operations, specifically Union and Intersection.

Most languages, such as TypeScript and Python, can easily distinguish the operator's context—whether it's a bitwise operation at the value level or a Union/Intersection at the type level—during the parsing stage.

In TAPL, this level of distinction is not made because evaluation can occur at the type level as well. Since these operators are now predominantly used for type construction and bitwise operations are less common in high-level languages, TAPL chooses to reserve | and & exclusively for type constructions (Union and Intersection).