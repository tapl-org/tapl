# 2. Function Syntax

Date: 2024-08-27

## Status

Accepted

## Context

*The issue motivating this decision, and any context that influences or constrains the decision.*

We need syntaxes for regular functions, function types, dependent types, and substructural types that are distinct
and don't overlap. Having separate, non-orthogonal or weak syntax for each explodes the number of rules and makes the system error prone.
We don't necessarily need a single syntax for everything, but each one should be clear and independent.

## Decision

*The change that we're proposing or have agreed to implement.*

Dependent type is a just regular function on the type level.
Function type is a just dependent type where argument is not used in the body.
Substructural type is a just dependent type where argument can be a statful object.

We can devide them into 2 kinds: dependent and non-dependent. 
* Dependent: function, dependent type, and substructural type
  * $\lambda{x}!t_{lock}.t_{body}$
* Non-dependent is function-type (a.k.a arrow type)
  * $t_{argument}{\to}t_{result}$



## Consequences

*What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.*

## Appendi
### A: In Python, argument is needed before checking whether the caller is callable or not
I guess, to identify whether the caller side is a callable or not, it needs some extra logic. So python do not adds extra logic to do this, instead prepares the argument and calls the function with that argument. On the otherhand, when the caller side raises an error, then then interpretator knows about that the caller is not a callable, then justs escalates that error.
What if the caller is not a callable, but the argument evaluates to an error. Then the error should be re-raised, or new "Expected a function" error should be raised. I guess re-raise the argument error will be effective.
So the order: caller error, argument error, caller is a callable, and then application.
```python
def get_function1():
    print('get_function1 called')
    def greeting(input):
        print('greeting called')
        print('Hello ' + input)
    return greeting

def get_function2():
    print('get_function2 called')
    return 'greeting'

def get_name():
    print("get_name called")
    return 'World'

get_function1()(get_name())
get_function2()(get_name())
```

Output
```text
get_function1 called
get_name called
greeting called
Hello World
get_function2 called
get_name called
Traceback (most recent call last):
  File "/Users/orti/projects/python/test2.py", line 17, in <module>
    get_function2()(get_name())
TypeError: 'str' object is not callable
```