<? Part of the Tapl Language project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *term*
&nbsp;| $d$ | *data*
&nbsp;| $c$ | *code*
&nbsp;| $\lambda.t$ | *function*
&nbsp;| $t{\to}t$ | *lock*
&nbsp;| $t{\ }t$ | *application\|unlock*
&nbsp;| $t{=}t$ | *equivalent*
&nbsp;| $\Sigma(e)$ | *expression as term*
$e ::=$ || *expression*
&nbsp;| $t$ | *term*
&nbsp;| $e{:}e$ | *typed*
&nbsp;| $e{\to}e$ | *lock*
&nbsp;| $e{\ }e$ | *application\|unlock*
&nbsp;| $e{=}e$ | *equivalent*

&nbsp;|**Handy terms**| $t = h{\mid}r$
---|---|--:
$h ::=$| $d\ \mid\ \lambda.t\ \mid\ h{\to}h$ | *normal*
$r ::=$| $c\ \mid\ h{\to}r\ \mid\ r{\to}t\ \mid\ t{\ }t\ \mid\ t{=}t\ \mid\ \Sigma(e)$ | *reducible*
&nbsp;|**Handy expressions**| $e=s{\mid}u$
$s ::=$| $t\ \mid\ s{:}s$ | *separated*
$u ::=$| $s{:}u\ \mid\ u{:}e\ \mid\ e{\to}e\ \mid\ e{\ }e\ \mid\ e{=}e$ | *separable*
$p ::=$| $h\ \mid\ p{:}p$ | *normal*
&nbsp;|**Notes**
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{=}(t)$ and $e{=}(e)$
$\Delta(c)$| code can be wrapped and used as data

$\psi[t]$| **Term Evaluation** |$\psi[t] \to t$
:-:|:-:|--:
&nbsp;|$\dfrac{\psi[h]}{h}$
&nbsp;|$\dfrac{\psi[c]}{h}$| *run the code*
$t{\to}t$|$\dfrac{\psi[r{\to}t]}{\psi[r]{\to}t}$
&nbsp;|$\dfrac{\psi[h{\to}r]}{h{\to}\psi[r]}$
$t{\ }t$|$\dfrac{\psi[t{\ }r]}{t{\ }\psi[r]}$
&nbsp;|$\dfrac{\psi[r{\ }h]}{\psi[r]{\ }h}$
&nbsp;|$\dfrac{\psi[d{\ }h]}{\text{error: not a function}}$
&nbsp;|$\dfrac{\psi[(\lambda.t){\ }h]}{h_\text{ t's result}}$ | *function call*
&nbsp;|$\dfrac{\psi[(h_1{\to}h_2){\ }h_3]}{(\lambda.h_2){\ }\psi[h_1{=}h_3]}$ | *unlock*
$t{=}t$|$\dfrac{\psi[r{=}t]}{\psi[r]{=}t}$
&nbsp;|$\dfrac{\psi[h{=}r]}{h{=}\psi[r]}$
&nbsp;|$\dfrac{\psi[d{=}(\lambda.t)\ \mid\ d{=}(h{\to}h)\ \mid\ (\lambda.t){=}(h{\to}h)]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\psi[d_1{=}d_2]}{d_1\ \mid\ \text{error: not equal}}$
&nbsp;|$\dfrac{\psi[(\lambda.t_1){=}(\lambda.t_2)]}{\lambda.(t_1{=}t_2)}$ | *wrap up*
&nbsp;|$\dfrac{\psi[(h_1{\to}h_2){=}(h_3{\to}h_4)]}{\psi[(h_1{=}h_3){\to}(h_2{=}h_4)]}$
$\Sigma(e)$|$\dfrac{\psi[\Sigma(u)]}{\Sigma(\phi[u])}$
&nbsp;|$\dfrac{\psi[\Sigma(h)]}{h}$
&nbsp;|$\dfrac{\psi[\Sigma(p_1{:}p_2)]}{\Sigma(p_1)}$
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
$e{\to}e$|$\dfrac{\sigma[u{\to}e]}{\sigma[u]{\to}e}$
&nbsp;|$\dfrac{\sigma[s{\to}u]}{s{\to}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{\to}s_1{:}s_2\ \mid\ s_1{:}s_2{\to}t]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\sigma[s_1{:}s_2{\to}s_3{:}s_4]}{(s_1{\to}s_3){:}(s_2{\to}s_4)}$
$e{\ }e$|$\dfrac{\sigma[e{\ }u]}{e{\ }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[u{\ }s]}{\sigma[u]{\ }s}$
&nbsp;|$\dfrac{\sigma[t{\ }s_1{:}s_2\ \mid\ s_1{:}s_2{\ }t]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){\ }(s_3{:}s_4)]}{(s_1{\ }s_3){:}(s_2{\ }s_4)}$
$e{=}e$|$\dfrac{\sigma[u{=}e]}{\sigma[u]{=}e}$
&nbsp;|$\dfrac{\sigma[s{=}u]}{s{=}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{=}s_1{:}s_2\ \mid\ s_1{:}s_2{=}t]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){=}(s_3{:}s_4)]}{(s_1{=}s_3){:}(s_2{=}s_4)}$
