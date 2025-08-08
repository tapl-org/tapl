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
$s ::=$          | $\lambda{x}.h\mid\ g{\ }h\ \mid\ h{\ }g\mid\ h{\ }h$                         | *separable*
$h ::=$          | $s\ \mid\ t{:}t$                                                             | *multi layer*
&nbsp;           | **Single Layer Meta-variables**                                              | $g = v{\mid}r = x{\mid}w$
$v ::=$          | $\lambda{x}.g$                                                               | *value*
$r ::=$          | $x\ \mid\ g{\ }g\ \mid\ \xi.t$                                               | *non-value*
$w ::=$          | $\lambda{x}.g\ \mid\ g{\ }g\ \mid\ \xi.t$                                    | *non-variable*
&nbsp;
&nbsp;           | **Evaluation**                                                               | $\epsilon[t] \to t$
$x$              | $\dfrac{\epsilon[x]}{x}$                                                     | *variable*
$\lambda{x}.g$   | $\dfrac{\epsilon[\lambda{x}.g]}{\lambda{x}.g}$                               | *abstraction*
$g\ g$           | $r{\ }g\ \mid\ v{\ }r\ \mid\ v{\ }v$                                         | *application*
&nbsp;           | $\dfrac{\epsilon[r{\ }g]}{\epsilon[r]{\ }g}$                                 | *function*
&nbsp;           | $\dfrac{\epsilon[v{\ }r]}{v{\ }\epsilon[r]}$                                 | *argument*
&nbsp;           | $\dfrac{\epsilon[(\lambda{x}.g){\ }v]}{[x{\mapsto}{v}]g}$                    | *substitution*
$\xi.t$          | $\xi.g\ \mid\ \xi.s\ \mid\ \xi.t{:}t$                                        | *unlayering*
&nbsp;           | $\dfrac{\epsilon[\xi.g]}{g}$
&nbsp;           | $\dfrac{\epsilon[\xi.s]}{\xi.\sigma[s]}$
&nbsp;           | $\dfrac{\epsilon[\xi.t_1{:}t_2]}{\lambda{x}.x\ \xi.t_1\ \xi.t_2}$
$h$              | $\dfrac{\epsilon[h]}{h}$                                                     | *multi layer*
&nbsp;
&nbsp;           | **Separation**                                                               | $\sigma[t] \to t$
$g$              | $\dfrac{\sigma[g]}{g}$                                                       | *single layer*
$\lambda{x}.h$   | $\lambda{x}.s\ \mid\ \lambda{x}.t{:}t$                                       | *abstraction*
&nbsp;           | $\dfrac{\sigma[\lambda{x}.s]}{\lambda{x}.\sigma[s]}$
&nbsp;           | $\dfrac{\sigma[\lambda{x}.t_1{:}t_2]}{(\lambda{x}.t_1){:}(\lambda{x}.t_2)}$
$g\ h$           | $x\ h\ \mid\ w\ h$                                                           | *application*
&nbsp;           | $\dfrac{\sigma[x\ h]}{x{:}x\ h}$                                             | *clone variable*
&nbsp;           | $\dfrac{\sigma[w\ h]}{w\ h}$                                                 | *layer mismatch*
$h\ g$           | $h\ x\ \mid\ h\ w$                                                           | *application*
&nbsp;           | $\dfrac{\sigma[h\ x]}{h\ x{:}x}$                                             | *clone variable*
&nbsp;           | $\dfrac{\sigma[h\ w]}{h\ w}$                                                 | *layer mismatch*
$h\ h$           | $\ s\ h\ \mid\ t{:}t\ s\ \mid\ t{:}t\ t{:}t$                                 | *application*
&nbsp;           | $\dfrac{\sigma[s\ h]}{\sigma[s]\ h}$
&nbsp;           | $\dfrac{\sigma[t_1{:}t_2\ s]}{t_1{:}t_2\ \sigma[s]}$
&nbsp;           | $\dfrac{\sigma[t_1{:}t_2\ t_3{:}t_4]}{(t_1\ t_3){:}(t_2\ t_4)}$
$t{:}t$          | $\dfrac{\sigma[t_1{:}t_2]}{t_1{:}t_2}$                                       | *already separated*


## Notes
* The Tapl-Calculus ($\xi$-calculus) is an extended version of the Lambda-Calculus ($\lambda$-calculus)
* Tapl doesn't have a type system; it's a multi-layered codebase. Parts of each layer may type-check, evaluate, or perform other operations.
* $\dfrac{a}{a'} \coloneqq a$ evaluates to $a'$ in one step, or forward the evaluation.
* VS Code shows the formulas in a pretty format
* When the evaluation or the seperation opertor returns the same term, it indicates that the term is either a value or has become stuck.
  * A closed term is stuck if it is in normal form but not a value ~ TAPL Book 3.5.15

## Examples
### Combinators

$I:= \lambda x. x$

$C:= \lambda f.\lambda g. \lambda x.g\ (f\ x)$

$E:= \lambda a.\lambda b. \text{if}\  a{=}b\text{ then }a\text{ else }error$

rule: $A' \equiv A{:}A$

### Simply Typed Lambda-Calculus (STL) Correspondence
STL: $\lambda x{:}T.t$

TAPL: $C'\ ET{:}I\ (\lambda x.t)$

