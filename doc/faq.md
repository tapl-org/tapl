<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>


### What is the backend of TAPL?
TAPL currently uses Python's AST as its backend. Soon, TAPL will introduce its own untyped AST/IR that focuses purely on computation. This backend can be compiled to LLVM IR, JVM bytecode, JavaScript, or executed by its own interpreter. TAPL itself will serve as the syntax and type system layer on top of this backend.

### Why does TAPL use the `!` symbol for instance types?

A key difference from Python's syntax is TAPL's use of the "bang" sigil (`!`) to distinguish between a class and an instance of that class.

In Python, a name like `Dog` is ambiguous; it can refer to the class object or an instance type depending on the context. TAPL enforces a strict separation:

*   `Dog`: Refers to the class itself (the blueprint).
*   `Dog!`: Refers to an instance of the class.

This design supports TAPL's philosophy of *Intentional Symmetry*, where a name consistently refers to the same kind of object in both the value layer and the type layer.

#### Code Example: Python vs. TAPL

In Python, `type[Dog]` is used to specify the class, while `Dog` specifies an instance.

```python
class Dog:
   pass

dog: Dog = Dog()  # `Dog` is both an instance type and a factory for creating instances.

def recruit_dog(species: type[Dog], individual: Dog):
   # 'species' is a class, and 'individual' is an object.
   pass
```

TAPL uses `Dog` for the class and `Dog!` for an instance, providing a clearer visual distinction.

```python
dog: Dog! = Dog() # `Dog!` is the instance type, and `Dog` is the factory.

def recruit_dog(species: Dog, individual: Dog!):
   # 'species' is a class, and 'individual' is an object.
   pass
```

> Vibe Note: the ! sigil transforms a static class name into a vivid, high-energy marker of realization, signaling that the abstract "blueprint" has been activated into a stateful, living object.


### Why the '|' and '&' Operators Are Not Bitwise Operations in TAPL
These single-symbol operators (`|` and `&`) are traditionally used for bitwise operations in many programming languages. However, in modern systems like TypeScript and Python, they have been naturally adopted to represent set-theoretic type operations, specifically Union and Intersection.

Most languages, such as TypeScript and Python, can easily distinguish the operator's context—whether it's a bitwise operation at the value level or a Union/Intersection at the type level—during the parsing stage.

In TAPL, this level of distinction is not made because evaluation can occur at the type level as well. Since these operators are now predominantly used for type construction and bitwise operations are less common in high-level languages, TAPL reserves `|` and `&` exclusively for type constructions (Union and Intersection).
