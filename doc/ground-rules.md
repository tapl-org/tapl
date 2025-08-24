<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## TAPL Calculus

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
$x$              | $\dfrac{\epsilon[x]}{x}$                                                     | *variable*
$\lambda{x}.g$   | $\dfrac{\epsilon[\lambda{x}.g]}{\lambda{x}.g}$                               | *abstraction*
$g\ g$           | $r{\ }g\ \mid\ v{\ }r\ \mid\ v{\ }v$                                         | *application*
&nbsp;           | $\dfrac{\epsilon[r{\ }g]}{\epsilon[r]{\ }g}$                                 | *function*
&nbsp;           | $\dfrac{\epsilon[v{\ }r]}{v{\ }\epsilon[r]}$                                 | *argument*
&nbsp;           | $\dfrac{\epsilon[(\lambda{x}.g){\ }v]}{[x{\mapsto}{v}]g}$                    | *substitution*
$\xi.t$          | $\xi.g\ \mid\ \xi.s\ \mid\ \xi.g{:}g\ \mid\ \xi.g{:}h\ \mid\ \xi.h{:}t$      | *unlayering*
&nbsp;           | $\dfrac{\epsilon[\xi.g]}{\xi.g}$                                             | *stuck*
&nbsp;           | $\dfrac{\epsilon[\xi.s]}{\xi.\sigma[s]}$                                     | *separate*
&nbsp;           | $\dfrac{\epsilon[\xi.g_1{:}g_2]}{\lambda{x}.x\ g_2\ g_1}$                    | *squash*
&nbsp;           | $\dfrac{\epsilon[\xi.g{:}h]}{\xi.g{:}h}$                                     | *stuck*
&nbsp;           | $\dfrac{\epsilon[\xi.h{:}t]}{\xi.h{:}t}$                                     | *stuck*
$h$              | $\dfrac{\epsilon[h]}{h}$                                                     | *multi layer*
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
* The Tapl-Calculus ($\xi$-calculus) is an extended version of the Lambda-Calculus ($\lambda$-calculus)
* Tapl doesn't have a type system; it's a multi-layered codebase. Parts of each layer may type-check, evaluate, or perform other operations.
* $\dfrac{a}{a'} \coloneqq a$ evaluates to $a'$ in one step, or forward the evaluation.
* VS Code shows the formulas in a pretty format
* When the evaluation or the seperation opertor returns the same term, it indicates that the term is either a value or has become stuck.
  * A closed term is stuck if it is in normal form but not a value ~ TAPL Book 3.5.15

## Examples
#### Combinators

$I:= \lambda x. x$

$C:= \lambda f.\lambda g. \lambda x.g\ (f\ x)$

$E:= \lambda a.\lambda b. \text{if}\  b<:a\text{ then }b\text{ else }error$

#### Simply Typed Lambda-Calculus (STL) Correspondence
STL: $\lambda x{:}T.t$

TAPL: $C\ I{:}(E\ T)\ (\lambda x.t)$

#### Polymorphic lambda-calculus (System F) Correspondence
System F: $id = \lambda X. \lambda x{:}X. x$

TAPL: $id = \lambda X. C\ I{:}(E\ X)\ (\lambda x. x) $