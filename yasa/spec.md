This is a project of lambda calculus based programming language. its syntax will be described below.
It will be translated into various machine code via MLIR, Cranelift, qbe, and c-backed, and others
it is a formally verifiable language.
Why this project exist: we know that programming language is basically a construction, this is where word "yasa" comes.
So we need a such a language which is formally verifiable, and also convertable by its shape to the machine code.
how it works. programm written in lambda calculus first evaluated partially using lambda calculus reduction techniques like beta, eta, theta reductions
after that whatever left is translated to ssa form based on the shape or structure.

This language is fully support strong reduction

todo:
[ ] design terms
[ ] design s-expression syntax (configurable: show bruijn, show store type)
[ ] design evaluation
[ ] implement how to store type the lambda
[ ] design how to introduce memory, and remove memory parameter when generating machine code


supported syntaxes
variable
function/abstraction (parameter may have store type as annotation)
call/application/(syntax sugar: let)
record
variant
data/bits with store type
! operator for fixing record: !A.label = (A !A).label



Examples:
Factorial

F = \E. {fact=\n. if n = 1 then 1 else n * E.fact(n-1)}

!F.fact 2
=(\n. if n = 1 then 1 else n * !F.fact(n-1)) 2
= 2 * !F.fact(1)
= 2 * (\n. if n = 1 then 1 else n * !F.fact(n-1))(1)
= 2 * 1
= 2

P = \E. {
    even = \n. if n = 0 then false else E.odd(n-1),
    odd = \n. if n = 0 then true else E.even(n-1)
}

!P.even 2
= (\n. if n = 0 then false else !P.odd(n-1)) 2
= if 2 = 0 then false else !P.odd(2-1)
= !P.odd(1)
= (\n. if n = 0 then true else !P.even(n-1)) 1
= !P.even(0)
= (\n. if n = 0 then false else !P.odd(n-1)) 0
= !P.odd(0)
= (\n. if n = 0 then true else !P.even(n-1)) 0
= true