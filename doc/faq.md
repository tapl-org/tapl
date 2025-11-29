<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

XXX: Review docs before publishing the blog.

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

### Why does TAPL add an underscore suffix (`_`) to generated class names?
In TAPL, a class and an instance of that class are treated as two distinct, but related, first-class types This distinction is important because 
both the class (as a factory for creating objects) and the instance (the object itself) can be treated as first-class values.

To prevent a name collision between the class factory and its instance, the TAPL compiler differentiates them with a simple naming convention:
* The instance is assigned the original name (e.g., `Dog`).
* The class factory is given the same name with an underscore suffix (e.g., `Dog_`).
(See a simple Dog class example in [python/tapl-lang/src/examples/easy.tapl](../python/tapl-lang/src/examples/easy.tapl).)

We could not find a better syntax than adding an underscore suffix. One idea was to introduce a `new` keyword, but it did not seem like a good solution. We are open to exploring alternative syntaxes.

#### Python Example: Class vs. Instance Name Use
The following Python example illustrates how a single name, `Dog`, can refer to both the class (a factory) and an instance, 
highlighting the underlying distinction TAPL addresses.

Note the difference in method calls:
* On the class: Dog.get(instance) requires the instance to be passed explicitly as the self argument.
* On an instance: my_dog.get() passes the instance (my_dog) implicitly as the self argument.

```
class Dog:
   def __init__(self, name: str):
      self.name = name
   def get(self):
      if self:
        return self.name
      return 'Dog Factory'

print(Dog.get(None))
print(Dog('Buddy').get())
```

Output:
```
Dog Factory
Buddy
```


### Why the '|' and '&' Operators Are Not Bitwise Operations in TAPL
These single-symbol operators (| and &) are traditionally used as bitwise operations in many programming languages. However, in modern systems like TypeScript and Python, they have been naturally adopted to represent set-theoretic type operations, specifically Union and Intersection.

Most languages, such as TypeScript and Python, can easily distinguish the operator's context—whether it's a bitwise operation at the value level or a Union/Intersection at the type level—during the parsing stage.

In TAPL, this level of distinction is not made because evaluation can occur at the type level as well. Since these operators are now predominantly used for type construction and bitwise operations are less common in high-level languages, TAPL chooses to reserve | and & exclusively for type constructions (Union and Intersection).