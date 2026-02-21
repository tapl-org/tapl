---
title: |
  The $\xi$-Calculus: Unifying Type Systems \
  through Layered Computation
author: Orti Bazar (orti.bazar@gmail.com)
date: \today
abstract: |
  We present the $\xi$-calculus, an extension of the untyped lambda calculus
  with two operations---layering ($t{:}t$) and unlayering ($\xi.t$)---that
  provides a unified mechanism for expressing the full spectrum of type system
  features. We define the syntax, term classification, evaluation semantics,
  and separation operation, then show that Simply Typed Lambda Calculus,
  System F polymorphism, substructural types, and dependent types all arise as
  configurations of the same mechanism, differing only in the choice of guard
  combinator.
documentclass: article
classoption:
  - 11pt
  - a4paper
geometry: margin=1in
numbersections: true
toc: true
header-includes:
  - \usepackage{amsmath,amssymb,mathtools}
---

\newpage

# Introduction

Most language ecosystems treat the type system as a fundamentally different
mechanism bolted onto the term language. TypeScript adds types to JavaScript.
Mypy adds types to Python. Rust's type system is a separate phase from
evaluation. Each requires its own distinct formalism, its own rules, its own
machinery.

The $\xi$-calculus rejects that dichotomy. It extends the untyped lambda
calculus with just two operations---**layering** ($t{:}t$) and **unlayering**
($\xi.t$)---and shows that type checking, polymorphism, substructural types,
and dependent types all emerge naturally from the same computational substrate.
The layering operation $t{:}t$ says "this term exists simultaneously at
multiple levels," and the **separation** operation decomposes a multi-layer
program into its individual layers.

This has two key consequences:

- **Unified type system hierarchy.** Simply Typed Lambda Calculus, System F,
  substructural types, and dependent types are all encoded using the same
  mechanism. They are not different type systems---they are different
  configurations of the same system.

- **Dependent types become natural.** When types are terms in another layer,
  dependent types---where types depend on values---are not a special feature
  requiring a proof assistant. They are terms that reference values across
  layers.

The $\xi$-calculus is named in the tradition of the $\lambda$-calculus. Where
$\lambda$ denotes abstraction, $\xi$ denotes unlayering---the operation that
inspects and decomposes the layered structure of a term.


# Syntax

The $\xi$-calculus extends the untyped lambda calculus with two constructs:
layering and unlayering.

$$
\begin{array}{rcll}
t \  ::= & & & \textit{terms:} \\[4pt]
  & x & & \textit{variable} \\
  & \lambda x.\, t & & \textit{abstraction} \\
  & t \ t & & \textit{application} \\
  & t {:} t & & \textit{layering} \\
  & \xi.\, t & & \textit{unlayering}
\end{array}
$$

The first three forms are standard lambda calculus. The two new forms are:

- **Layering** ($t_1{:}t_2$): constructs a term that exists simultaneously in
  multiple computational layers.
- **Unlayering** ($\xi.t$): inspects and decomposes the layers of a term.


# Term Classification

Every term is either *single-layer* or *multi-layer*. This distinction is the
engine of the entire system---it drives both evaluation and separation.

$$
\begin{array}{rcll}
  & & & t = g \mid h \\[4pt]
g \ ::= & x \mid \lambda x.\,g \mid g\ g \mid \xi.\,t
  & & \textit{single-layer term} \\
h \ ::= & \lambda x.\,h \mid g\ h \mid h\ g \mid h\ h \mid t{:}t
  & & \textit{multi-layer term}
\end{array}
$$

A single-layer term ($g$) is a conventional lambda calculus term---it lives in
one layer. A multi-layer term ($h$) involves layering or has at least one
multi-layer sub-term. Multi-layer terms are compact representations of code
that *means different things at different layers*.

## Single-Layer Meta-variables

Single-layer terms are further classified into values and non-values:

$$
\begin{array}{rcll}
  & & & g = v \mid r \\[4pt]
v \ ::= & \lambda x.\,g & & \textit{value} \\
r \ ::= & x \mid g\ g \mid \xi.\,t & & \textit{non-value}
\end{array}
$$

## Multi-Layer Meta-variables

Multi-layer terms are classified into *separated* and *separable* terms:

$$
\begin{array}{rcll}
  & & & h = p \mid s \\[4pt]
p \ ::= & t{:}t & & \textit{separated} \\
s \ ::= & \lambda x.\,h \mid g\ h \mid h\ g \mid h\ h
  & & \textit{separable}
\end{array}
$$

A separated term ($p$) is already decomposed into its layers. A separable term
($s$) still needs the separation operation to decompose it.


# Evaluation

The evaluation function $\epsilon[t] \to t$ reduces a term by one step. We
adopt the convention:

$$
\dfrac{a}{a'} \coloneqq \text{``}a \text{ evaluates to } a' \text{ in one step''}
$$

When evaluation returns the same term, the term is either a value or stuck. A
closed term is stuck if it is in normal form but not a value (cf. Pierce,
Definition 3.5.15).

## Variable and Abstraction

Variables and abstractions are already in normal form:

$$
\dfrac{\epsilon[x]}{x}
\quad (\text{E-Var})
\qquad\qquad
\dfrac{\epsilon[\lambda x.\,g]}{\lambda x.\,g}
\quad (\text{E-Abs})
$$

## Application

Application of two single-layer terms ($g\ g$) decomposes into three
sub-cases: $r\ g \mid v\ r \mid v\ v$.

When the function is a non-value, evaluate it first:

$$
\dfrac{\epsilon[r\ g]}{\epsilon[r]\ g}
\quad (\text{E-App-Fun})
$$

When the function is a value but the argument is not, evaluate the argument:

$$
\dfrac{\epsilon[v\ r]}{v\ \epsilon[r]}
\quad (\text{E-App-Arg})
$$

When both are values, perform $\beta$-reduction:

$$
\dfrac{\epsilon[(\lambda x.\,g)\ v]}{[x \mapsto v]\,g}
\quad (\text{E-App-Beta})
$$

## Unlayering

Unlayering ($\xi.t$) decomposes into three sub-cases:
$\xi.g \mid \xi.s \mid \xi.(t_1{:}t_2)$.

If the body is single-layer, produce a terminal selector with the identity
function as a sentinel:

$$
\dfrac{\epsilon[\xi.\,g]}{\lambda x.\, x\ (\lambda y.\,y)\ g}
\quad (\text{E-Xi-Sep1})
$$

The selector provides the term $g$ in one position and the identity
$\lambda y.\,y$ in the other. The identity signals "there are no further
layers"---it is the base case of unlayering.

If the body is separable, apply the separation operation:

$$
\dfrac{\epsilon[\xi.\,s]}{\xi.\,\sigma[s]}
\quad (\text{E-Xi-Sep2})
$$

If the body is a layered term, *squash* it into a selector that recursively
unlayers each component:

$$
\dfrac{\epsilon[\xi.\,(t_1{:}t_2)]}{\lambda x.\, x\ (\xi.\,t_2)\ (\xi.\,t_1)}
\quad (\text{E-Xi-Squash})
$$

The recursive $\xi$ in the squash result ensures that each sub-term is
itself unlayered when the selector is applied. For single-layer sub-terms,
the recursion bottoms out at E-Xi-Sep1, producing a terminal selector. For
multi-layer sub-terms, squash is applied again, peeling off one level of
layering at a time. All paths terminate with no stuck cases.

## Multi-Layer Terms

Multi-layer terms do not reduce under evaluation---they must be explicitly
unlayered:

$$
\dfrac{\epsilon[h]}{h}
\quad (\text{E-Multi})
$$


# Separation

The separation function $\sigma[t] \to t$ transforms a multi-layer term into
a layered term $t_1{:}t_2$ where each component belongs to a single layer.
Separation is the key operation of the $\xi$-calculus: it is the formal
mechanism by which a multi-layer program is decomposed into independent
single-layer computations.

## Base Cases

Single-layer terms and already-separated terms are unchanged by separation:

$$
\dfrac{\sigma[g]}{g}
\quad (\text{S-Single})
\qquad\qquad
\dfrac{\sigma[p]}{p}
\quad (\text{S-Separated})
$$

## Abstraction

Abstraction over a multi-layer body ($\lambda x.\,h$) has two sub-cases:
$\lambda x.\,s \mid \lambda x.\,p$.

If the body is separable, recurse into the body:

$$
\dfrac{\sigma[\lambda x.\,s]}{\lambda x.\,\sigma[s]}
\quad (\text{S-Abs-Body})
$$

If the body is already separated, distribute the abstraction over the layers:

$$
\dfrac{\sigma[\lambda x.\,(t_1{:}t_2)]}{(\lambda x.\,t_1){:}(\lambda x.\,t_2)}
\quad (\text{S-Abs-Dist})
$$

A function whose body spans two layers becomes two functions, one per layer.

## Cloning

When a single-layer term interacts with a multi-layer term in an application,
the single-layer term is **cloned** into both layers:

$$
\dfrac{\sigma[g\ h]}{(g{:}g)\ h}
\quad (\text{S-Clone-Fun})
\qquad\qquad
\dfrac{\sigma[h\ g]}{h\ (g{:}g)}
\quad (\text{S-Clone-Arg})
$$

This is how ordinary code participates in multiple layers simultaneously.
The same source term appears in every layer.

## Application of Multi-Layer Terms

Application of two multi-layer terms ($h\ h$) decomposes into:
$s\ h \mid p\ s \mid p\ p$.

If the function is separable, separate it first:

$$
\dfrac{\sigma[s\ h]}{\sigma[s]\ h}
\quad (\text{S-App-Fun})
$$

If the function is separated but the argument is separable, separate the
argument:

$$
\dfrac{\sigma[p\ s]}{p\ \sigma[s]}
\quad (\text{S-App-Arg})
$$

If both are separated, distribute the application over the layers:

$$
\dfrac{\sigma[(t_1{:}t_2)\ (t_3{:}t_4)]}{(t_1\ t_3){:}(t_2\ t_4)}
\quad (\text{S-App-Dist})
$$

Applying a layered function to a layered argument produces a layered result,
where each layer's function is applied to that layer's argument.


# Encoding Type System Features

One of the most significant results of the $\xi$-calculus is that multiple type
system features emerge from the same layering mechanism. This section defines
the combinators used in the encodings and presents each correspondence.

## Combinators

$$
\begin{array}{rcl}
I &\coloneqq& \lambda x.\, x \\[4pt]
B &\coloneqq& \lambda f.\,\lambda g.\,\lambda x.\, f\ (g\ x) \\[4pt]
G_a &\coloneqq& \lambda a.\,\lambda b.\
  \text{if } b <: a \text{ then } a \text{ else } \mathit{error} \\[4pt]
G_b &\coloneqq& \lambda a.\,\lambda b.\
  \text{if } b <: a \text{ then } b \text{ else } \mathit{error}
\end{array}
$$

$I$ is the identity combinator. $B$ is the composition combinator. $G_a$
is a type guard that checks subtyping and returns the *annotation* type, while
$G_b$ is a type guard that returns the *input* type---preserving precise type
information.

## Simply Typed Lambda Calculus

In the standard Simply Typed Lambda Calculus (STLC), a typed abstraction is
written $\lambda x{:}T.\, t$. In the $\xi$-calculus, this is encoded as:

$$
\lambda x{:}T.\, t \quad\Longleftrightarrow\quad B\ (\lambda x.\,t)\ (I{:}(G_a\ T))
$$

The layering $I{:}(G_a\ T)$ creates a two-layer term: the identity function at
the evaluation layer (pass the argument through unchanged) and a type guard at
the type-checking layer (check that the argument is a subtype of $T$ and return
$T$). The composition combinator $B$ threads the argument through both layers.

## System F (Polymorphism)

In System F, the polymorphic identity is $\mathit{id} = \lambda X.\, \lambda
x{:}X.\, x$. In the $\xi$-calculus:

$$
\mathit{id} = \lambda X.\, B\ (\lambda x.\, x)\ (I{:}(G_a\ X))
$$

Polymorphism is not a separate feature. It arises because $X$ is a variable
that can be bound to any type. The same abstraction mechanism that works for
terms works for types, because in the $\xi$-calculus types *are* terms.

## Substructural Types

Substructural types use the same encoding as STLC, replacing $G_a$ with $G_b$:

$$
\lambda x{:}T.\, t \quad\Longleftrightarrow\quad B\ (\lambda x.\,t)\ (I{:}(G_b\ T))
$$

The only difference is the guard combinator. $G_a$ returns the annotation type
$a$ (discarding the precise input type), while $G_b$ returns the input type $b$
(preserving it). This distinction controls how type information flows through
the system, which is the essence of substructural typing.

## Dependent Types

For dependent types, we introduce a type function $T_D = \lambda x.\, t_d$
(a type that depends on a value) and a dependent guard combinator:

$$
G_D \coloneqq \lambda a.\,\lambda b.\,\lambda x.\, G_{a \mid b \mid D}\ (a\ x)\ (b\ x)
$$

A dependent typed abstraction $\lambda x{:}T_D.\, t$ is then encoded as:

$$
B\ (\lambda x.\,t)\ (I{:}(G_D\ T_D))
$$

The guard $G_D$ applies both the type function and the value to the argument,
then checks compatibility. Since types are terms, a type that depends on a
value is simply a function from values to types---no special machinery is
required.

## Type Hierarchy

The $\xi$-calculus induces a natural type hierarchy:

$$
\mathit{Nothing} \longrightarrow T \longrightarrow \mathit{Any}
  \longrightarrow \mathit{Any} \mid \mathit{None}
$$

- **Nothing**: the bottom type, subtype of all types. Represents computations
  that never return.
- **Any**: the top type for non-nullable values. Supertype of all types except
  $\mathit{None}$.
- **Any $\mid$ None**: the true top type. Supertype of everything.

By default, types are non-nullable. A function returning $\mathit{Int}$ cannot
return $\mathit{None}$---one must explicitly use $\mathit{Int} \mid
\mathit{None}$.


# Conclusion

The $\xi$-calculus demonstrates that a single mechanism---layered computation
with separation---is sufficient to express the full spectrum of type system
features. Simply Typed Lambda Calculus, System F, substructural types, and
dependent types are not distinct formalisms; they are configurations of
the same system, differing only in the choice of guard combinator
($G_a$, $G_b$, or $G_D$).

The separation rules provide a formal mechanism for decomposing a multi-layer
program into independent single-layer computations. The cloning rules ensure
that ordinary code participates in every layer, while the distribution rules
ensure that layered structures are correctly projected. Together, these rules
define a complete and deterministic procedure for deriving separate
computations---one per layer---from a single source program.

A companion paper, *TAPL: A Language Framework Built on the $\xi$-Calculus*,
describes how this calculus is realized as a practical compiler framework.

\bigskip
\noindent\textit{Named in the tradition of the $\lambda$-calculus. Inspired by
Benjamin C. Pierce's \textbf{Types and Programming Languages} (MIT Press,
2002).}
