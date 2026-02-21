<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

# $\xi - calculus$

&nbsp;           | **Syntax**                                                                   | &nbsp;
---              | :-:                                                                          | ---:
$t ::=$          | $\hspace{20em}$                                                              | *term*
&nbsp;           | $x$                                                                          | *variable*
&nbsp;           | $\lambda{x}{.}t$                                                             | *abstraction*
&nbsp;           | $t{\ }t$                                                                     | *application*
&nbsp;           | $t{:}t$                                                                      | *layering*
&nbsp;           | $\xi.t$                                                                      | *unlayering*
&nbsp;
&nbsp;           | **Meta-variables**                                                           | $t = g{\mid}h$
$g ::=$          | $x\ \mid\ \lambda{x}.g\ \mid\ g{\ }g\ \mid\ \xi.t$                           | *single layer*
$h ::=$          | $\lambda{x}.h\mid\ g{\ }h\ \mid\ h{\ }g\mid\ h{\ }h\ \mid\ t{:}t$            | *multi layer*
&nbsp;           | **Single Layer Meta-variables**                                              | $g = v{\mid}r$.
$v ::=$          | $\lambda{x}.g$                                                               | *value*
$r ::=$          | $x\ \mid\ g{\ }g\ \mid\ \xi.t$                                               | *non-value*
&nbsp;           | **Multi Layer Meta-variables**                                               | $h = p{\mid}s$
$p ::=$          | $t{:}t$                                                                      | *separated*
$s ::=$          | $\lambda{x}.h\mid\ g{\ }h\ \mid\ h{\ }g\mid\ h{\ }h$                         | *separable*
&nbsp;
&nbsp;           | **Evaluation**                                                               | $\epsilon[t] \to t$
$x$              | $\dfrac{\epsilon[x]}{x}$                                                     | *open term*
$\lambda{x}.g$   | $\dfrac{\epsilon[\lambda{x}.g]}{\lambda{x}.g}$                               | *abstraction*
$g\ g$           | $r{\ }g\ \mid\ v{\ }r\ \mid\ v{\ }v$                                         | *application*
&nbsp;           | $\dfrac{\epsilon[r{\ }g]}{\epsilon[r]{\ }g}$                                 | *function*
&nbsp;           | $\dfrac{\epsilon[v{\ }r]}{v{\ }\epsilon[r]}$                                 | *argument*
&nbsp;           | $\dfrac{\epsilon[(\lambda{x}.g){\ }v]}{[x{\mapsto}{v}]g}$                    | *substitution*
$\xi.t$          | $\xi.g\ \mid\ \xi.s\ \mid\ \xi.t{:}t$                                        | *unlayering*
&nbsp;           | $\dfrac{\epsilon[\xi.g]}{\lambda{x}.\ x\ (\lambda{y}.y)\ g}$                 | *base*
&nbsp;           | $\dfrac{\epsilon[\xi.s]}{\xi.\sigma[s]}$                                     | *separate*
&nbsp;           | $\dfrac{\epsilon[\xi.t_1{:}t_2]}{\lambda{x}.\ x\ (\xi.t_2)\ (\xi.t_1)}$      | *squash*
$h$              | $\dfrac{\epsilon[h]}{h}$                                                     | *stuck*
&nbsp;
&nbsp;           | **Separation**                                                               | $\sigma[t] \to t$
$g$              | $\dfrac{\sigma[g]}{g}$                                                       | *single layer*
$p$              | $\dfrac{\sigma[p]}{p}$                                                       | *already separated*
$\lambda{x}.h$   | $\lambda{x}.s\ \mid\ \lambda{x}.p$                                           | *abstraction*
&nbsp;           | $\dfrac{\sigma[\lambda{x}.s]}{\lambda{x}.\sigma[s]}$                         | *separate body*
&nbsp;           | $\dfrac{\sigma[\lambda{x}.t_1{:}t_2]}{(\lambda{x}.t_1){:}(\lambda{x}.t_2)}$  | *distribute*
$g\ h$           | $\dfrac{\sigma[g\ h]}{g{:}g\ h}$                                             | *clone function*
$h\ g$           | $\dfrac{\sigma[h\ g]}{h\ g{:}g}$                                             | *clone argument*
$h\ h$           | $\ s\ h\ \mid\ p\ s\ \mid\ p\ p$                                             | *application*
&nbsp;           | $\dfrac{\sigma[s\ h]}{\sigma[s]\ h}$                                         | *function*
&nbsp;           | $\dfrac{\sigma[p\ s]}{p\ \sigma[s]}$                                         | *argument*
&nbsp;           | $\dfrac{\sigma[t_1{:}t_2\ t_3{:}t_4]}{(t_1\ t_3){:}(t_2\ t_4)}$              | *distribute*


## Notes
* The Xi-Calculus ($\xi$-calculus) is an extended version of the Lambda-Calculus ($\lambda$-calculus)
* $\dfrac{a}{a'} \coloneqq a$ evaluates to $a'$ in one step, or forward the evaluation.
* Terms are either open or closed (cf. Pierce, TAPL 5.1.Scope). A closed term that evaluates to itself is either a value ($v$) or stuck. A closed term is stuck if it is in normal form but not a value (cf. Pierce, TAPL 3.5.15). Multi-layer terms ($h$) are stuck under evaluation; they require explicit unlayering via $\xi$ to make progress.
* When separation returns the same term, it is either single-layer ($g$) or already separated ($p$)---both are base cases.
* Unlayering ($\xi$) is total: every sub-case produces a new term. There are no stuck cases in unlayering.

## Examples
#### Combinators

$I:= \lambda x. x$

$B:= \lambda f.\lambda g. \lambda x.f\ (g\ x)$

$G_a:= \lambda a.\lambda b. \text{if}\  b<:a\text{ then }a\text{ else }error$

$G_b:= \lambda a.\lambda b. \text{if}\  b<:a\text{ then }b\text{ else }error$

#### Simply Typed Lambda-Calculus (STL) Correspondence
STL: $\lambda x{:}T.t$

TAPL: $B\ (\lambda x.t)\ (I{:}(G_a\ T))$

#### Polymorphic lambda-calculus (System F) Correspondence
System F: $id = \lambda X. \lambda x{:}X. x$

TAPL: $id = \lambda X. B\ (\lambda x. x)\ (I{:}(G_a\ X))$

#### Substructural type Correspondence

STL: $\lambda x{:}T.t$

TAPL: $B\ (\lambda x.t)\ (I{:}(G_b\ T))$

#### Dependent type Correspondence

$T_D:= \lambda x. t_d$

$G_D:= \lambda a.\lambda b. \lambda x. G_{a\mid b\mid D}\ (a\ x)\ (b\ x)$

Dependent type: $\lambda x{:}T_D.t$

TAPL: $B\ (\lambda x.t)\ (I{:}(G_D\ T_D))$



# Type System Hierarchy

$\text{Nothing} \to T \to \text{Any} \to \text{Any}|\text{None}$