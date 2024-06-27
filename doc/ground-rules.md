<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *term*
&nbsp;| $d$ | *data*
&nbsp;| $c$ | *code*
&nbsp;| $\lambda.t$ | *abstraction*
&nbsp;| $t{.}t$ | *lock*
&nbsp;| $t{\ }t$ | *application \| unlock*
&nbsp;| $t{=}t$ | *equivalent*
&nbsp;| $\Sigma(e)$ | *expression as term*
$g ::=$ || *gate*
&nbsp;| $\lambda$ | *parameter*
&nbsp;| $t$ | *keyhole*
&nbsp;| $g{:}g$ | *multi level gate*
$e ::=$ || *expression*
&nbsp;| $t$ | *term*
&nbsp;| $e{:}e$ | *typed \| multi level*
&nbsp;| $g{.}e$ | *abstraction \| lock*
&nbsp;| $e{\ }e$ | *application \| unlock*
&nbsp;| $e{=}e$ | *equivalent*

&nbsp;|**Handy terms**| $t = h{\mid}r$
---|---|--:
$h ::=$| $d\ \mid\ \lambda.t\ \mid\ h{.}h$ | *normal*
$r ::=$| $c\ \mid\ r{.}t\ \mid\ h{.}r\ \mid\ t{\ }t\ \mid\ t{=}t\ \mid\ \Sigma(e)$ | *reducible*
&nbsp;|**Handy expressions**| $e=s{\mid}u$
$s ::=$| $t\ \mid\ s{:}s$ | *separated*
$u ::=$| $u{:}e\ \mid\ s{:}u\ \mid\ g{.}e\ \mid\ e{\ }e\ \mid\ e{=}e$ | *separable*
$p ::=$| $h\ \mid\ p{:}p$ | *normal*
&nbsp;|**Notes**
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{=}(t)$ and $e{=}(e)$
$*$| just a character data
$\Delta(c)$| code can be wrapped and used as data
$t.(\lambda.t)$| semantically correct lock term.<br> if body is not an abstraction, then there will be an error in further evaluation.

$\psi[t]$| **Term Evaluation** |$\psi[t] \to t$
:-:|:-:|--:
&nbsp;|$\dfrac{\psi[h]}{h}$
&nbsp;|$\dfrac{\psi[c]}{h}$| *run the code*
$t{.}t$|$\dfrac{\psi[r{.}t]}{\psi[r]{.}t}$
&nbsp;|$\dfrac{\psi[h{.}r]}{h{.}\psi[r]}$
$t{\ }t$|$\dfrac{\psi[r{\ }t]}{\psi[r]{\ }t}$
&nbsp;|$\dfrac{\psi[h{\ }r]}{h{\ }\psi[r]}$
&nbsp;|$\dfrac{\psi[d{\ }h]}{\text{error: not an abstraction}}$
&nbsp;|$\dfrac{\psi[(\lambda.t){\ }h_{arg}]}{h_\text{ t's result}}$ | *application*
&nbsp;|$\dfrac{\psi[(h_1{.}h_2){\ }h_3]}{h_2{\ }\psi[h_1{=}h_3]}$ | *unlock*
$t{=}t$|$\dfrac{\psi[r{=}t]}{\psi[r]{=}t}$
&nbsp;|$\dfrac{\psi[h{=}r]}{h{=}\psi[r]}$
&nbsp;|$\dfrac{\psi[d{=}(\lambda.t)\ \mid\ d{=}(h{.}h)\ \mid\ (\lambda.t){=}(h{.}h)]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\psi[d_1{=}d_2]}{d_2\ \mid\ \text{error: not equal}}$ | $d_2$ *can be a stateful object,*<br>*and return it to enable substructural type*
&nbsp;|$\dfrac{\psi[(\lambda.t_1){=}(\lambda.t_2)]}{\lambda.(t_1{=}t_2)}$ | *enclose function bodies to enable dependent type*
&nbsp;|$\dfrac{\psi[(h_1{.}h_2){=}(h_3{.}h_4)]}{\psi[(h_1{=}h_3){.}(h_2{=}h_4)]}$
$\Sigma(e)$|$\dfrac{\psi[\Sigma(u)]}{\Sigma(\phi[u])}$
&nbsp;|$\dfrac{\psi[\Sigma(p_1{:}p_2)]}{\Sigma(p_1)}$
&nbsp;|$\dfrac{\psi[\Sigma(h)]}{h}$
&nbsp;
$\phi[e]$| **Expression evaluation** |$\phi[e] \to e$
&nbsp;|$\dfrac{\phi[u]}{\sigma[u]}$
&nbsp;|$\dfrac{\phi[t]}{\psi[t]}$
&nbsp;|$\dfrac{\phi[s_1{:}s_2]}{s_1{:}\phi[{s_2}]}$
&nbsp;|$\dfrac{\phi[s{:}p]}{\phi[s]{:}p}$
&nbsp;
$\sigma[e]$| **Expression separation** |$\sigma[e] \to e$
&nbsp;|$\dfrac{\sigma[s]}{s}$
&nbsp;|$\dfrac{\sigma[e{:}u]}{e{:}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[u{:}s]}{\sigma[u]{:}s}$
$g{.}e$|$\dfrac{\sigma[g{.}u]}{g{.}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[(\lambda{\mid}t){.}(s_1{:}s_2)\ \mid\ (g_1{:}g_2){.}t]}{\text{error: not in the same level}}$
&nbsp;|$\dfrac{\sigma[g_1{:}g_2{.}s_1{:}s_2]}{(g_1{.}s_1){:}(g_2{.}s_2)}$
$e{\ }e$|$\dfrac{\sigma[u{\ }e]}{\sigma[u]{\ }e}$
&nbsp;|$\dfrac{\sigma[s{\ }u]}{s{\ }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{\ }s_1{:}s_2\ \mid\ s_1{:}s_2{\ }t]}{\text{error: not in the same level}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){\ }(s_3{:}s_4)]}{(s_1{\ }s_3){:}(s_2{\ }s_4)}$
$e{=}e$|$\dfrac{\sigma[u{=}e]}{\sigma[u]{=}e}$
&nbsp;|$\dfrac{\sigma[s{=}u]}{s{=}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{=}s_1{:}s_2\ \mid\ s_1{:}s_2{=}t]}{\text{error: not in the same level}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){=}(s_3{:}s_4)]}{(s_1{=}s_3){:}(s_2{=}s_4)}$
