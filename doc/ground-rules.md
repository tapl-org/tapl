---
title: $\xi$-Calculus Ground Rules
author: Orti Bazar (orti.bazar@gmail.com)
date: \today
documentclass: article
classoption:
  - 11pt
  - letterpaper
geometry: margin=1in
header-includes:
  - \usepackage{amsmath,amssymb,mathtools}
  - \usepackage{xcolor,eso-pic}
  - \AddToShipoutPictureFG{\AtTextCenter{\makebox(0,0){\rotatebox{45}{\scalebox{8}{\textcolor{gray!30}{DRAFT}}}}}}
---

<!-- Part of the TAPL project, under the Apache License v2.0 with LLVM
     Exceptions. See /LICENSE for license information.
     SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception -->

|                | **Syntax**                                                                     |                    |
|:---------------|:------------------------------------------------------------------------------:|-------------------:|
| $t ::=$        |                                                                                | *terms*            |
|                | $x$                                                                            | *variable*         |
|                | $\lambda x.\,t$                                                               | *abstraction*      |
|                | $t\ t$                                                                         | *application*      |
|                | $t{:}t$                                                                        | *layering*         |
|                | $\xi.\,t$                                                                      | *unlayering*       |

|                | **Meta-variables**                                                             | $t = g \mid h$     |
|:---------------|:------------------------------------------------------------------------------:|-------------------:|
| $g ::=$        | $x \mid \lambda x.\,g \mid g\ g \mid \xi.\,t$                                 | *single layer*     |
| $h ::=$        | $\lambda x.\,h \mid g\ h \mid h\ g \mid h\ h \mid t{:}t$                      | *multi layer*      |
|                | **Single Layer Meta-variables**                                                | $g = v \mid r$     |
| $v ::=$        | $\lambda x.\,g$                                                               | *value*            |
| $r ::=$        | $x \mid g\ g \mid \xi.\,t$                                                    | *non-value*        |
|                | **Multi Layer Meta-variables**                                                 | $h = p \mid s$     |
| $p ::=$        | $t{:}t$                                                                        | *separated*        |
| $s ::=$        | $\lambda x.\,h \mid g\ h \mid h\ g \mid h\ h$                                 | *separable*        |

\renewcommand{\arraystretch}{2.5}

|                  | **Evaluation**                                                                          | $\epsilon[t] \to t$ |
|:-----------------|:---------------------------------------------------------------------------------------:|---------------------:|
| $x$              | $\dfrac{\epsilon[x]}{x}$                                                               | *open term*          |
| $\lambda x.\,g$  | $\dfrac{\epsilon[\lambda x.\,g]}{\lambda x.\,g}$                                      | *abstraction*        |
| $g\ g$           | $r\ g \mid v\ r \mid v\ v$                                                             | *application*        |
|                  | $\dfrac{\epsilon[r\ g]}{\epsilon[r]\ g}$                                               | *function*           |
|                  | $\dfrac{\epsilon[v\ r]}{v\ \epsilon[r]}$                                               | *argument*           |
|                  | $\dfrac{\epsilon[(\lambda x.\,g)\ v]}{[x \mapsto v]g}$                                 | *substitution*       |
| $\xi.\,t$        | $\xi.\,g \mid \xi.\,s \mid \xi.\,t{:}t$                                                | *unlayering*         |
|                  | $\dfrac{\epsilon[\xi.\,g]}{\lambda x.\ x\ (\lambda y.\,y)\ g}$                        | *base*               |
|                  | $\dfrac{\epsilon[\xi.\,s]}{\xi.\,\sigma[s]}$                                           | *separate*           |
|                  | $\dfrac{\epsilon[\xi.\,t_1{:}t_2]}{\lambda x.\ x\ (\xi.\,t_2)\ (\xi.\,t_1)}$         | *squash*             |
| $h$              | $\dfrac{\epsilon[h]}{h}$                                                                | *stuck*              |

|                  | **Separation**                                                                          | $\sigma[t] \to t$    |
|:-----------------|:---------------------------------------------------------------------------------------:|---------------------:|
| $g$              | $\dfrac{\sigma[g]}{g}$                                                                  | *single layer*       |
| $p$              | $\dfrac{\sigma[p]}{p}$                                                                  | *already separated*  |
| $\lambda x.\,h$  | $\lambda x.\,s \mid \lambda x.\,p$                                                    | *abstraction*        |
|                  | $\dfrac{\sigma[\lambda x.\,s]}{\lambda x.\,\sigma[s]}$                                 | *separate body*      |
|                  | $\dfrac{\sigma[\lambda x.\,t_1{:}t_2]}{(\lambda x.\,t_1){:}(\lambda x.\,t_2)}$        | *distribute*         |
| $g\ h$           | $\dfrac{\sigma[g\ h]}{g{:}g\ h}$                                                       | *clone function*     |
| $h\ g$           | $\dfrac{\sigma[h\ g]}{h\ g{:}g}$                                                       | *clone argument*     |
| $h\ h$           | $s\ h \mid p\ s \mid p\ p$                                                             | *application*        |
|                  | $\dfrac{\sigma[s\ h]}{\sigma[s]\ h}$                                                   | *function*           |
|                  | $\dfrac{\sigma[p\ s]}{p\ \sigma[s]}$                                                   | *argument*           |
|                  | $\dfrac{\sigma[t_1{:}t_2\ t_3{:}t_4]}{(t_1\ t_3){:}(t_2\ t_4)}$                      | *distribute*         |

\renewcommand{\arraystretch}{1}

# Notes

* The Xi-Calculus ($\xi$-calculus) is an extended version of the Lambda-Calculus ($\lambda$-calculus).
* $\dfrac{a}{a'} \coloneqq a$ evaluates to $a'$, either directly or by forwarding evaluation to a sub-term.
* Terms are either open or closed (cf. Pierce, TAPL 5.1.Scope). A closed term that evaluates to itself is either a value ($v$) or stuck. A closed term is stuck if it is in normal form but not a value (cf. Pierce, TAPL 3.5.15). Multi-layer terms ($h$) are stuck under evaluation; they require explicit unlayering via $\xi$ to make progress.
* When separation returns the same term, it is either single-layer ($g$) or already separated ($p$)---both are base cases.
* Unlayering ($\xi$) is total: every sub-case produces a new term. There are no stuck cases in unlayering.

# Examples

## Combinators

$I:= \lambda x. x$

$B:= \lambda f.\lambda g. \lambda x.f\ (g\ x)$

For simplicity, $G$ uses $\text{if}$ clauses and a $\text{TypeError}$ keyword. I also use pseudocode for names such as the predefined types $Int$ and $Str$ for integers and strings, and the addition operator $+$.

$G_a:= \lambda a.\lambda b. \text{if}\  b<:a\text{ then }a\text{ else }\text{TypeError}$

$G$ takes two arguments: $a$, the formal parameter type declared in the function signature, and $b$, the type of the argument actually passed. $G_a$ returns $a$---the declared type---making the type check independent of the argument's type. This is the common case. When the result must depend on the argument's type (e.g. resource management), we use $G_b$ instead (see Substructural types below).

## Simply Typed Lambda-Calculus (STL) Correspondence

STL: $\lambda x{:}T.t$

$\xi$-Calculus: $B\ (\lambda x.t)\ (I{:}(G_a\ T))$

Example---increment function:

$(\lambda x{:}Int. x + 1)\ 2$

= $(B\ (\lambda x.x + (1{:}Int))\ (I{:}(G_a\ Int)))\ (2{:}Int)$

By $B\ f\ g\ x = f\ (g\ x)$:

= $(\lambda x.x + (1{:}Int))\ ((I{:}(G_a\ Int))\ (2{:}Int))$

Distribute application over layers ($p\ p$, *distribute*):

= $(\lambda x.x + (1{:}Int))\ ((I\ 2){:}((G_a\ Int)\ Int))$

$I\ 2 = 2$, and $(G_a\ Int)\ Int = (\lambda b.\ \text{if}\ b<:Int\ \text{then}\ Int\ \text{else}\ \text{TypeError})\ Int = Int$:

= $(\lambda x.x + (1{:}Int))\ (2{:}Int)$

Separate $(\lambda x.x + (1{:}Int))$ (*distribute* through abstraction):

= $((\lambda x.x + 1){:}(\lambda x.x + Int))\ (2{:}Int)$

Distribute application over layers ($p\ p$, *distribute*):

= $((\lambda x.x + 1)\ 2){:}((\lambda x.x + Int)\ Int)$

= $(2 + 1){:}(Int + Int) = 3{:}Int$

## Polymorphic Lambda-Calculus (System F) Correspondence

System F: $id = \lambda X. \lambda x{:}X. x$

$\xi$-Calculus: $id = \lambda X. B\ (\lambda x. x)\ (I{:}(G_a\ X))$

## Substructural Type Correspondence

$G_b:= \lambda a.\lambda b. \text{if}\  b<:a\text{ then }b\text{ else }\text{TypeError}$

Here the argument type may carry state---for example, whether a file is open or closed.

STL: $\lambda x{:}T.t$

$\xi$-Calculus: $B\ (\lambda x.t)\ (I{:}(G_b\ T))$

## Dependent Type Correspondence

$T_D:= \lambda x. t_d$

$G_D:= \lambda a.\lambda b. \lambda x. G_{a\mid b\mid D}\ (a\ x)\ (b\ x)$

$G_D$ is a delayed dependent type guard. When type checking depends on a value that is not yet available, we wrap the type check in an abstraction ($\lambda x$). The check is then executed later, once the value is supplied.

Dependent type: $\lambda x{:}T_D.t$

$\xi$-Calculus: $B\ (\lambda x.t)\ (I{:}(G_D\ T_D))$
