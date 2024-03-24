### Why type is an expression?
because typeof operator returns expression
### Why we need complete type check before substitution?
The type of any expression (even for locks) can be universe. To prevent this $(\lambda x{:}\star. x\ 2{:}Nat)\ 3{:}Nat{:}*$
### What if we design term wrapped by type, and that type plays as term. For example: \x:Nat.x:x:* == (\x. x:x):(_:Nat.*)
In this case, we could not separate types from terms, and could not run types fully before running terms.