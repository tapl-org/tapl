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
