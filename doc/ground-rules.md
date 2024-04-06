<? Part of the Tapl Language project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *terms:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lambda x.\ t$ | *abstraction*
&nbsp;| $t{\to}t$ | *type-of-functions*
&nbsp;| $t{:}t$ | *typed-term*
&nbsp;| $\text{error}$ | *error*
&nbsp;| $\lbrace {t_i}^{i\in1..n}\rbrace$ | *native-call*
&nbsp;| $t \ t$ | *application*
&nbsp;| $t{\equiv}t$ | *equivalent*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}E$  | *variable binding*

&nbsp;|**Handy terms**| $t = x{\mid}d{\mid}\text{error}{\mid}u$
---|---|--:
$d ::=$| $b\ \mid\ \lambda x.t\ \mid\ d{\to}d\ \mid\ d{:}d$ | *truthy normal*
&nbsp; | $\text{error}$ | *falsy normal*
$u ::=$| | *reducible*
&nbsp; | $d{\to}\text{error}\ \mid\ d{\to}u\ \mid\ \text{error}{\to}t\ \mid\ u{\to}t$
&nbsp; | $\text{error}{:}d\ \mid\ u{:}d\ \mid\ t{:}\text{error}\ \mid\ t{:}u$
&nbsp; | $\lbrace {t_i}^{i\in1..n}\rbrace\ \mid\  t\ t\ \mid\ t{\equiv}t$
&nbsp;
$f ::=$| $\lambda x.t\ \mid\ d{\to}d\ \mid\ d{:}d$ | *truthy function*
&nbsp;| **Notes**
&nbsp;| $a,g,h,i,j,k,l,m,n$ | *reserved letters*
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{=}(t)$ and $e{=}(e)$

$\omicron^{\star}[a]$| **Multi-Step Operator** |$\omicron^{\star}[a] \to a$
:-:|:-:|--:
&nbsp;|$\dfrac{\omicron[a]}{a'}\vdash\dfrac{\omicron^{\star}[a]}{\omicron^{\star}[a']}$| *can progress*
&nbsp;|$\dfrac{\omicron[a]}{a}\vdash\dfrac{\omicron^{\star}[a]}{a}$| *no progress*
&nbsp;
$\psi[t]$| **Term Evaluation** |$\psi[t] \to t$
*variable*|$\dfrac{\psi[x]}{\text{fatal error: context has to be empty}}$
*bytes*|$\dfrac{\psi[b]}{b}$
*abstraction*|$\dfrac{\psi[\lambda x.t]}{\lambda x.t}$
*type of functions*
&nbsp;|$\dfrac{\psi[d{\to}\text{error}]}{\text{error}}$
&nbsp;|$\dfrac{\psi[d{\to}u]}{d{\to}\psi^{\star}[u]}$
&nbsp;|$\dfrac{\psi[\text{error}{\to}t]}{\text{error}}$
&nbsp;|$\dfrac{\psi[u{\to}t]}{\psi^{\star}[u]{\to}t}$
*typed term*
&nbsp;|$\dfrac{\psi[\text{error}{:}d]}{\text{error}}$
&nbsp;|$\dfrac{\psi[u{:}d]}{\psi^{\star}[u]{:}d}$
&nbsp;|$\dfrac{\psi[t{:}\text{error}]}{\text{error}}$
&nbsp;|$\dfrac{\psi[t{:}u]}{t{:}\psi^{\star}[u]}$
*error*|$\dfrac{\psi[\text{error}]}{\text{error}}$
*native-call*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},u_j,{t_k}^{k\in{j+1}..n}\rbrace]}{\lbrace{b_i}^{i\in1..j-1},\psi^{\star}[u_j],{t_k}^{k\in{j+1}..n}\rbrace}$| *eval reducibles*
&nbsp;|$g\Leftarrow\lambda x.t{\mid}d{\to}d{\mid}d{:}d{\mid}\text{error}\quad\vdash\quad\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},g_j,{t_k}^{k\in{j+1}..n}\rbrace]}{\text{error}}$| *not bytes*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..n}\rbrace]}{b_{result}\mid \text{error}}$ | $\delta$*-reduction*
*application*
&nbsp;|$\dfrac{\psi[u \ t]}{\psi^\star[u] \ t}$ | *1st term progress*
&nbsp;|$g\Leftarrow b{\mid}\text{error}\quad\vdash\quad\dfrac{\psi[g\ t]}{\text{error}}$ | *not a function*
&nbsp;|$\dfrac{\psi[f \ u]}{f \ \psi^\star[u]}$ | *2nd term progress*
&nbsp;|$\dfrac{\psi[f\ \text{error}]}{\text{error}}$ | *error argument*
&nbsp;|$\dfrac{\psi[(\lambda x.t)\ d]}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
&nbsp;|$\dfrac{\psi[(d_1{\to}d_2)\ d_3]}{(\lambda x.d_2)\ d_1{\equiv}d_3}$ | *type check*
&nbsp;|$g\Leftarrow b{\mid}\lambda x.t{\mid}d{\to}d\quad\vdash\quad\dfrac{\psi[(d_1{:}d_2)\ g]}{\text{error}}$ | *typed term expects typed term*
&nbsp;|$\dfrac{\psi[(d_1{:}d_2)\ (d_3{:}d_4)]}{(d_1\ d_3){:}(d_2\ d_4)}$ | *typed term application*
*equivalent*
&nbsp;|$\dfrac{\psi[u{\equiv}t]}{\psi^{\star}[u]{\equiv}t}$ | *1st term progress*
&nbsp;|$\dfrac{\psi[\text{error}{\equiv}t]}{\text{error}}$ | *error term*
&nbsp;|$\dfrac{\psi[d{\equiv}u]}{d{\equiv}\psi^{\star}[u]}$ | *2nd term progress*
&nbsp;|$\dfrac{\psi[d{\equiv}\text{error}]}{\text{error}}$ | *error term*
&nbsp;|$\dfrac{\psi[\ b{\equiv}\lambda x.t\ \mid\ b{\equiv}(d_1{\to}d_2)\ \mid\ b{\equiv}(d_1{:}d_2)\ ]\quad\text{+ reflexive}}{\text{error}}$ | *not bytes form*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_2]\quad\text{where }b_1{\ne}b_2 }{\text{error}}$ | *not same bytes*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_2]\quad\text{where }b_1{=}b_2 }{b_1}$ | *same bytes*
&nbsp;|$\dfrac{\psi[\lambda x.t{\equiv}(d_1{\to}d_2)\ \mid\ \lambda x.t{\equiv}(d_1{:}d_2)\ ]\quad\text{+ reflexive}}{\text{error}}$ | *not abstraction form*
&nbsp;|$\dfrac{\psi[\lambda x.t_1{\equiv}\lambda x.t_2]}{\lambda x.t_1{\equiv}t_2}$ | *enclose-in abstraction*
&nbsp;|$\dfrac{\psi[(d_1{\to}d_2){\equiv}(d_3{:}d_4)\ ]\quad\text{+ reflexive}}{\text{error}}$ | *not type-of-functions form*
&nbsp;|$\dfrac{\psi[(d_1{\to}d_2){\equiv}(d_3{\to}d_4)]}{\psi^{\star}[(d_1{\equiv}d_3){\to}(d_2{\equiv}d_4)]}$ | *check type-of-functions*
&nbsp;|$\dfrac{\psi[(d_1{:}d_2){\equiv}(d_3{:}d_4)]}{\psi^{\star}[(d_1{\equiv}d_3){:}(d_2{\equiv}d_4)]}$ | *check typed-term*
&nbsp;
$\psi[e]$|**Expression Evaluation**|$\psi[e]\longrightarrow e$
*universe*|$\dfrac{\psi[\star]}{\star}$
*typed-term*
&nbsp;|$\dfrac{\psi[t{:}R]}{t{:}\psi^\star[R]}$| *eval reducible type*
&nbsp;|$\dfrac{\psi[t{:}\text{error}{:}{\star}]}{\text{error}{:}{\star}}$| *error*
&nbsp;|$\dfrac{\psi[\text{error}{:}P]}{\text{error}{:}{\star}}$| *error*
&nbsp;|$\dfrac{\psi[u{:}P]}{\psi^\star[u]{:}P}$| *eval reducible term*
&nbsp;|$\dfrac{\psi[d{:}P]}{d{:}P}$
*sequincing*
&nbsp;|$\dfrac{\psi[r;e]}{\psi^\star[r];e}$| *head progress*
&nbsp;|$\dfrac{\psi[q;e]}{q}$| *error value*
&nbsp;|$\dfrac{\psi[p;e]}{\psi^{\star}[e]}$| *tail progress*
*lock*
&nbsp;|$\dfrac{\psi[R{\to}e]}{\psi^{\star}[R]{\to}e}$
&nbsp;|$\dfrac{\psi[(\text{error}{:}{\star}){\to}e]}{\text{error}{:}{\star}}$
&nbsp;|$\dfrac{\psi[P{\to}r]}{P{\to}\psi^{\star}[r]}$
&nbsp;|$\dfrac{\psi[P{\to}\text{error}{:}{\star}]}{\text{error}{:}{\star}}$
&nbsp;|$\dfrac{\psi[P{\to}p]}{P{\to}p}$
*unlock*
&nbsp;|$\dfrac{\psi[r \ e]}{\psi^\star[r] \ e}$| *1st expression progress*
&nbsp;|$\dfrac{\psi[\text{error}{:}{\star}\ e]}{\text{error}{:}\star}$| *1st expression error*
&nbsp;|$\dfrac{\psi[\star\ e]}{\text{error}{:}\star}$| *universe is not a lock*
&nbsp;|$\dfrac{\psi[d{:}P\ e]}{(d\ \epsilon[e]){:}\psi^{\star}[P\ e]}$| *typed-term*
&nbsp;|$\dfrac{\psi[f\ r]}{f\ \psi^\star[r]}$| *2nd expression progress*
&nbsp;|$\dfrac{\psi[f\ \text{error}{:}{\star}]}{\text{error}{:}{\star}}$| *2nd expression error*
&nbsp;|$\dfrac{\psi[f\ p]}{f\ \epsilon[p]{:}\tau[p]}$| *type argument*
&nbsp;|$\dfrac{\psi[(P_1{\to}p)\ \ t{:}P_2]}{P_1{\equiv}P_2;p}$| *unlock*
*equivalent*
&nbsp;|$\dfrac{\psi[R{\equiv}E]}{\psi^\star[R]{\equiv}E}$| *1st expression progress*
&nbsp;|$\dfrac{\psi[Q{\equiv}E]}{Q}$| *1st expression falsy*
&nbsp;|$\dfrac{\psi[P{\equiv}R]}{P{\equiv}\psi^\star[R]}$| *2st expression progress*
&nbsp;|$\dfrac{\psi[P{\equiv}Q]}{Q}$| *2st expression falsy*
&nbsp;|$\dfrac{\psi[\ \star{\equiv}d{:}P\ \mid\ \star{\equiv}P{\to}p\ ]\quad\text{+ reflexive}}{\text{error}{:}{\star}}$ | *not a universe form*
&nbsp;|$\dfrac{\psi[\star{\equiv}\star]}{\star}$ | *same universe*
&nbsp;|$\dfrac{\psi[d{:}P_1{\equiv}P_2{\to}p]\quad\text{+ reflexive}}{d{:}P_1{\equiv}(\epsilon[P_2{\to}p]{:}\tau[P_2{\to}p])}$ | *not typed term*
&nbsp;|$\dfrac{\psi[d_1{:}P_1{\equiv}d_2{:}P_2]}{(d_1{\equiv}d_2){:}(P_1{\equiv}P_2)}$ | *enclose in typed term*
&nbsp;|$\dfrac{\psi[P_1{\to}p_1{\equiv}P_2{\to}p_2]}{(P_1{\equiv}P_2){\to}(p_1{\equiv}p_2)}$ | *enclose in typed term*
&nbsp;
$\epsilon[e]$| **Type erasure** | $\epsilon[e] \to t$
&nbsp;|$\dfrac{\epsilon[x]}{x}$| *variable*
&nbsp;|$\dfrac{\epsilon[\star]}{\star}$ | *universe to atom*
&nbsp;|$\dfrac{\epsilon[t{:}E]}{t}$| *typed-term*
&nbsp;|$\dfrac{\epsilon[e_1;e_2]}{(\lambda x.\epsilon[e_2])\ \epsilon[e_1]}$| *sequincing*
&nbsp;|$\dfrac{\epsilon[E{\to}e]}{\_.\epsilon[e]}$| *lock*
&nbsp;|$\dfrac{\epsilon[e_1\ e_2]}{\epsilon[e_1]\ \epsilon[e_2]}$| *unlock*
&nbsp;|$\dfrac{\epsilon[E_1{\equiv}E_2]}{\epsilon[E_1]{\equiv}\epsilon[E_2]}$| *equivalent*
&nbsp;
$\tau[e]$| **Type of expression** | $(\Gamma\vdash\tau[e]) \to e$
&nbsp;|$x{:}E\in\Gamma\ \vdash\ \dfrac{\Gamma\vdash\tau[x]}{E}$| *variable*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\star]}{\star}$| *universe*
&nbsp;|$\dfrac{\Gamma \vdash \tau[t{:}E]}{E}$| *typed term*
&nbsp;|$\dfrac{\Gamma \vdash \tau[e_1;e_2]}{\Gamma \vdash \tau[e_1];\Gamma \vdash \tau[e_2]}$| *sequencing*
&nbsp;|$\dfrac{\Gamma \vdash \tau[E{\to}e]}{E{\to}(\Gamma, x{:}E \vdash \tau[e])}$| *lock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[e_1\ e_2]}{(\Gamma \vdash \tau[e_1])\ e_2}$| *unlock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[e_1{\equiv}e_2]}{(\Gamma \vdash \tau[e_1]){\equiv}(\Gamma \vdash \tau[e_2])}$| *equivalent*
