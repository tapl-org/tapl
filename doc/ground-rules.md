<? Part of the Tapl Language project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *terms:*
&nbsp;| $x$ | *variable*
&nbsp;| $\star$ | *atom*
&nbsp;| $b$ | *bytes*
&nbsp;| $\text{error}$ | *error*
&nbsp;| $\lbrace {t_i}^{i\in1..n}\rbrace$ | *native-call*
&nbsp;| $\Nu x.\ t\qquad \Nu{\in}\{0,1\}$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $t{\equiv}t$ | *equivalent*
$e,E ::=$|| *expressions:*
&nbsp;| $x, X$ | *variable*
&nbsp;| $\star$ | *universe*
&nbsp;| $t{:}E$ | *typed-term*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $\Nu  x{:}E.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
&nbsp;| $E{\equiv}E$ | *equivalent*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}E$  | *variable binding*

&nbsp;|**Handy terms**| &nbsp;
---|---|--:
$d ::=$| $\star\ \mid\ b\ \mid\ 0x.d\ \mid\ 1x.t$ | *truthy normal*
&nbsp; | $\text{error}$ | *falsy normal*
$u ::=$| $x\ \mid\ \lbrace {t_i}^{i\in1..n}\rbrace\ \mid\ 0x.u\ \mid\ 0x.\text{eror}\ \mid\  t\ t\ \mid\ t{\equiv}t$ | *reducible*
&nbsp;| $t = (d\ \mid\ \text{error}\ \mid\ u)$
&nbsp;|**Handy expressions**|&nbsp;
$p,P ::=$| $\star\ \mid\ d{:}P\ \mid\ 0x{:}P.p\ \mid\ \Nu x{:}P.e \quad\text{where }\Nu{\ge}1$ | *truthy normal*
$q,Q ::=$| $\text{error}{:}{\star}$ | *falsy normal*
$r,R ::=$||*reducible*
&nbsp;| $x\ \mid\ \text{let } x{=}e \text{ in } e\ \mid\ e\ e \mid\ E{\equiv}E$
&nbsp;| $u{:}P\ \mid\ \text{error}{:}P\ \mid\ t{:}Q\ \mid\ t{:}R$
&nbsp;| $\Nu x{:}Q.e\ \mid\ \Nu x{:}R.e\ \mid\ 0x{:}P.q\ \mid\ 0x{:}P.r$
&nbsp;| $E = (P\ \mid\ Q\ \mid\ R)$
$f ::=$| $\Nu x.t \ \mid\ \Nu x{:}P.e$
&nbsp;
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
*variable*|$\dfrac{\psi[x]}{\text{fatar error: context is not empty}}$
*atom*|$\dfrac{\psi[\star]}{\star}$
*bytes*|$\dfrac{\psi[b]}{b}$
*error*|$\dfrac{\psi[\text{error}]}{\text{error}}$
*native-call*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},u_j,{t_k}^{k\in{j+1}..n}\rbrace]}{\lbrace{b_i}^{i\in1..j-1},\psi^{\star}[u_j],{t_k}^{k\in{j+1}..n}\rbrace}$| *eval reducibles*
&nbsp;|$g\Leftarrow\star{\mid}\text{error}{\mid}\Nu x.t\quad\vdash\quad\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},g_j,{t_k}^{k\in{j+1}..n}\rbrace]}{\text{error}}$| *not bytes*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..n}\rbrace]}{b_{result}\mid \text{error}}$ | $\delta$*-reduction*
*abstraction*
&nbsp;|$\dfrac{\psi[0x.r]}{0x.\psi^{\star}[r]}$ | *eval reducibles*
&nbsp;|$\dfrac{\psi[0x.\text{error}]}{\text{error}}$ | *error inside*
&nbsp;|$\dfrac{\psi[0x.d]}{0x.d}$
&nbsp;|$\dfrac{\psi[1x.t]}{1x.t}$
*application*
&nbsp;|$\dfrac{\psi[r \ t]}{\psi^\star[r] \ t}$ | *1st term progress*
&nbsp;|$g\Leftarrow\star{\mid}b{\mid}\text{error}\quad\vdash\quad\dfrac{\psi[g\ t]}{\text{error}}$ | *not a function*
&nbsp;|$\dfrac{\psi[(0x.t_1) \ t_2]}{t_1}$ | *ignore*
&nbsp;|$\dfrac{\psi[(1x.t) \ r]}{(1x.t) \ \psi^\star[r]}$ | *2nd term progress*
&nbsp;|$\dfrac{\psi[(1x.t)\ \text{error}]}{\text{error}}$ | *error argument*
&nbsp;|$\dfrac{\psi[(1x.\ t)\ d]}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
*equivalent*
&nbsp;|$\dfrac{\psi[r{\equiv}t]}{\psi^{\star}[r]{\equiv}t}$ | *1st term progress*
&nbsp;|$\dfrac{\psi[\text{error}{\equiv}t]}{\text{error}}$ | *error term*
&nbsp;|$\dfrac{\psi[d{\equiv}r]}{d{\equiv}\psi^{\star}[r]}$ | *2st term progress*
&nbsp;|$\dfrac{\psi[d{\equiv}\text{error}]}{\text{error}}$ | *error term*
&nbsp;|$\dfrac{\psi[\ \star{\equiv}b\ \mid\ \star{\equiv}\Nu x.t\ \mid\ b{\equiv}\Nu x.t\ ]}{\text{error}}$ | *not same form*
&nbsp;|$\dfrac{\psi[\star{\equiv}\star]}{\star}$ | *same atom*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_2]\quad\text{where }b_1{\ne}b_2 }{\text{error}}$ | *not same bytes*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_2]\quad\text{where }b_1{=}b_2 }{b_1}$ | *same bytes*
&nbsp;|$\dfrac{\psi[\Nu_1 x.t_1{\equiv}\Nu_2 x.t_2]\qquad \text{where } \Nu_1{\ne}\Nu_2}{\text{error}}$ | *wrong abstraction arity*
&nbsp;|$\dfrac{\psi[\Nu_1 x.t_1{\equiv}\Nu_2 x.t_2]\qquad \text{where } \Nu_1{=}\Nu_2}{\Nu_1 x.(t_1{\equiv}t_2)}$ | *dig-in abstraction*
&nbsp;
$\psi[e]$|**Expression Evaluation**|$\psi[e]\longrightarrow e$
*variable*|$\dfrac{\psi[x]}{\text{fatar error: context is not empty}}$
*universe*|$\dfrac{\psi[\star]}{\star}$
*typed-term*
&nbsp;|$\dfrac{\psi[t{:}R]}{t{:}\psi^\star[R]}$| *eval reducible type*
&nbsp;|$\dfrac{\psi[t{:}\text{error}{:}{\star}]}{\text{error}{:}{\star}}$| *error*
&nbsp;|$\dfrac{\psi[\text{error}{:}P]}{\text{error}{:}{\star}}$| *error*
&nbsp;|$\dfrac{\psi[u{:}P]}{\psi^\star[u]{:}P}$| *eval reducible term*
&nbsp;|$\dfrac{\psi[d{:}P]}{d{:}P}$| *eval reducible term*
*let-binding*
&nbsp;|$\dfrac{\psi[\text{let }x{=}r\text{ in }e]}{\text{let }x{=}\psi^\star[r]\text{ in }e}$| *value progress*
&nbsp;|$\dfrac{\psi[\text{let } x{=}\text{error}{:}{\star} \text{ in } e]}{\text{error}{:}\star}$| *error value*
&nbsp;|$\dfrac{\psi[\text{let } x{=}p \text{ in } e]}{[x\mapsto p]\ e}$| *substitution*
*lock*
&nbsp;|$\dfrac{\psi[\Nu x{:}R.e]}{\Nu x{:}\psi^{\star}[R].e}$
&nbsp;|$\dfrac{\psi[\Nu x{:}\text{error}{:}{\star}.e]}{\text{error}{:}{\star}}$
&nbsp;|$\dfrac{\psi[\Nu x{:}P.e] \quad\text{where }\Nu{\ge}1}{\Nu x{:}P.e}$
&nbsp;|$\dfrac{\psi[0x{:}P.r]}{0x{:}P.\psi^{\star}[r]}$
&nbsp;|$\dfrac{\psi[0x{:}P.\text{error}{:}{\star}]}{\text{error}{:}{\star}}$
&nbsp;|$\dfrac{\psi[0x{:}P.p]}{0x{:}P.p}$
*unlock*
&nbsp;|$\dfrac{\psi[r \ e]}{\psi^\star[r] \ e}$| *function progress*
&nbsp;|$g\Leftarrow\star{\mid}{\star}{:}P\mid b{:}P\mid\text{error}{:}{\star}\quad\vdash\quad\dfrac{\psi[g\ e]}{\text{error}{:}\star}$| *not a function*
&nbsp;|$\dfrac{\psi[f{:}P\ e]}{(f\ \epsilon[e]){:}\psi[P\ e]}$| *typed-term*
&nbsp;|$\dfrac{\psi[f\ r]}{f\ \psi^\star[r]}$| *argument progress*
&nbsp;|$\dfrac{\psi[f\ \text{error}{:}{\star}]}{\text{error}{:}{\star}}$| *argument error*
&nbsp;|$\dfrac{\psi[f\ p]}{f\ \epsilon[p]{:}\tau[p]}$| *type argument*
&nbsp;|$\dfrac{\psi[(0x{:}P_1.p)\ \ d{:}P_2]}{\text{let }X{=}P_1{\equiv}P_2\text{ in }e}$| *unlock*
&nbsp;|$\dfrac{\psi[(1x{:}E_1.e)\ \ t{:}E_2]}{\text{let }X{=}E_1{\equiv}E_2\text{ in let } x{=}t{:}X\text{ in }e}$| *unlock*
*full eval types*
&nbsp;
&nbsp;|$\dfrac{\psi[e]}{e}$ | *otherwise (no evaluation rule)*
&nbsp;
$\xi[e]$|**Lock Inside Evaluation**|$\xi[e]\longrightarrow e$
&nbsp;|| *typed-term*
&nbsp;|$\dfrac{\xi[t{:}R]}{t{:}\xi[R]}$ | *type progress*
&nbsp;|$\dfrac{\xi[t{:}t_1{:}E_1]}{t{:}\phi^\star[t_1{:}E_1]}$ | *typed-term fusion*
&nbsp;|$\dfrac{\xi[t{:}(\lambda x_1{:}E_2.e_3))]}{t{:}(\lambda x_1{:}\xi^\star[E_2].\xi^\star[e_3])}$ | *under abstraction*
&nbsp;|$\dfrac{\xi[t{:}\text{error}{:}\star]}{\text{error}{:}\star}$ | *error type*
&nbsp;|$\dfrac{\xi[u{:}T{:}\star]}{\xi[u]{:}T{:}\star}$ | *well-typed term progress*
&nbsp;|| *lock*
&nbsp;|$\dfrac{\xi[\lambda x{:}R.e]}{\lambda x{:}\xi[R].e}$ | *argument type progress*
&nbsp;|$\dfrac{\xi[\lambda x{:}\text{error}{:}\star.e]}{\text{error}{:}\star}$ | *error-typed argument*
&nbsp;
&nbsp;|$\dfrac{\xi[e]}{e}$ | *otherwise (no evaluation rule)*
&nbsp;
$\epsilon[e]$| **Type erasure** | $\epsilon[e] \to t$
&nbsp;|$\dfrac{\epsilon[x]}{x}$| *variable*
&nbsp;|$\dfrac{\epsilon[\star]}{\text{error}}$ | *type-of-types*
&nbsp;|$\dfrac{\epsilon[t{:}E]}{t}$| *typed-term*
&nbsp;|$\dfrac{\epsilon[\text{let } x{=}e_1 \text{ in } e_2]}{(\lambda x.\epsilon[e_2])\ \epsilon[e_1]}$| *let-binding*
&nbsp;|$\dfrac{\epsilon[\lambda x{:}E.e]}{\lambda x.\epsilon[e]}$| *lock*
&nbsp;|$\dfrac{\epsilon[e_1\ e_2]}{\epsilon[e_1]\ \epsilon[e_2]}$| *unlock*
&nbsp;
$\phi[d{:}T]$| **Typed-term fusion** | $\phi[d{:}T] \to E$
&nbsp;|$\dfrac{\phi[d{:}x]}{t{:}x}$| *variable*
&nbsp;|$\dfrac{\phi[t{:}\star]}{error{:}\star}$| *type-of-types is not function*
&nbsp;|$\dfrac{\phi[t_1{:}t_2{:}E]}{t_1{:}\phi[t_2{:}E]}$| *typed-term*
&nbsp;|$\dfrac{\phi[t{:}b{:}\star]}{error{:}\star}$| *not function*
&nbsp;|$\dfrac{\phi[t{:}\text{error}{:}\star]}{error{:}\star}$| *error type*
&nbsp;|$\dfrac{\phi[t{:}E]}{t{:}E}$| *otherwise (keep as it is)*
&nbsp;
$\tau[e]$| **Type of expression** | $(\Gamma\vdash\tau[e]) \to e$
&nbsp;|$x{:}E\in\Gamma\ \vdash\ \dfrac{\Gamma\vdash\tau[x]}{E}$| *variable*
&nbsp;|$\dfrac{\Gamma \vdash \tau[t{:}E]}{E}$| *typed term*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\lambda x{:}E.e]}{\lambda x{:}E.(\Gamma, x{:}E \vdash \tau[e])}$| *lock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[e_1\ e_2]}{(\Gamma \vdash \tau[e_1])\ e_2}$| *unlock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\text{let } x_1{=}e_1 \text{ in } e_2]\qquad \text{where }x_1 \notin FV(\Gamma,x_1{:}x_2\vdash\tau[e_2])}{\text{let } x_2{=}(\Gamma \vdash \tau[e_1])\text{ in } (\Gamma,x_1{:}x_2 \vdash \tau[e_2])}$| *let-binding*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\text{let } x_1{=}e_1 \text{ in } e_2]\qquad \text{where } x_1 \in FV(\Gamma,x_1{:}x_2\vdash\tau[e_2])}{\text{let } x_2{=}(\Gamma \vdash \tau[e_1])\text{ in } \text{let } x_1{=}\epsilon[e_1]{:}x_2 \text{ in } (\Gamma,x_1{:}x_2 \vdash \tau[e_2])}$| *dependent typed let-binding*
&nbsp;|$\dfrac{\tau[\star]}{\star}$ | *type of types*
&nbsp;
$\omega[E]$| **Expression as Type** | $\omega[E] \to (T{\mid}\text{error}{:}\star)$
&nbsp;|$\dfrac{\omega[x]}{x}$| *variable*
&nbsp;|$\dfrac{\omega[t:E]}{x}$| *variable*
&nbsp;|$\dfrac{\omega[E]\quad\text{where }\tau[E]{\equiv}K}{E \text{ becomes }T}$| *well-typed*
&nbsp;|$\dfrac{\omega[E]\quad\text{where }\tau[E]{\not\equiv}K}{\text{error}{:}\star}$| *error-typed*
&nbsp;
$[x{\mapsto}w]e$| **Expression substitution** | $[x{\mapsto}w]e\to e$
&nbsp;|$\dfrac{[x{\mapsto}v]x}{v}$| *variable*
&nbsp;|$\dfrac{[x{\mapsto}v]t{:}E}{([x{\mapsto}\epsilon[v]]t){:}([x{\mapsto}v]E)}$| *typed term*
&nbsp;|$\dfrac{[x{\mapsto}v](\lambda x{:}E.e)}{(\lambda x{:}[x{\mapsto}v]E.[x{\mapsto}v]e)}$| *lock*
&nbsp;|$\dfrac{[x{\mapsto}v](e_1\ e_2)}{[x{\mapsto}v]e_1\ [x{\mapsto}v]e_2}$| *unlock*
&nbsp;|$\dfrac{[x{\mapsto}v](\text{let }x{=}e_1\text{ in }e_2)}{\text{let }x{=}[x{\mapsto}v]e_1\text{ in }[x{\mapsto}v]e_2}$| *let-binding*
&nbsp;|$\dfrac{[x{\mapsto}v]\star}{\star}$ | *type of types*
&nbsp;
