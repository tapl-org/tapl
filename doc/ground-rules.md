<? Part of the Tapl Language project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *terms:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lbrace {t_i}^{i\in1..n}\rbrace$ | *native-call*
&nbsp;| $\Nu x.\ t\qquad \Nu{\in}\{0,1\}$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $\text{error}$ | *error*
&nbsp;| $t{\equiv}t$ | *equivalent*
$e,E ::=$|| *expressions:*
&nbsp;| $x, X$ | *variable*
&nbsp;| $\star_{level}$ | *universe*
&nbsp;| $t{:}E$ | *typed-term*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $\Nu  x{:}E.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
&nbsp;| $E{\equiv}E$ | *equivalent*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}E$  | *variable binding*

&nbsp;|**Reserved letters**| &nbsp;
---|---|--:
&nbsp;| $a,i,j,k,l,m,n$
&nbsp;|**Handy terms**
$d ::=$| $b \ \mid\ \Nu x.t\ \mid\ x$ | *normal form*
$u ::=$| $\lbrace {t_i}^{i\in1..n}\rbrace\ \mid\  t\ t\ \mid\ t{\equiv}t$ | *reducible*
&nbsp;
&nbsp;|**Handy expressions**|&nbsp;
$p,P ::=$| $\star\ \mid\ b{:}P$ | *tip-expression*
$q,Q ::=$| $\text{let } x{=}e \text{ in } e\ \mid\ e\ e \mid\ E{\equiv}E$
$r,R ::=$| $q\ \mid t{:}R\ \mid\ u{:}P$
$v ::=$| $x\ \mid\ \star\ \mid\ d{:}P\ \mid\ \Nu  x{:}E.\ e$
$f$| $\Nu x{:}E.e$
&nbsp;
&nbsp;| **Notes**
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{=}(t)$ and $e{=}(e)$

$\omicron^{\star}[a]$| **Multi-Step Operator** |$\omicron^{\star}[a] \to a$
:-:|:-:|--:
&nbsp;|$\dfrac{\omicron[a]}{a'}\vdash\dfrac{\omicron^{\star}[a]}{\omicron^{\star}[a']}$| *can progress*
&nbsp;|$\dfrac{\omicron[a]}{a}\vdash\dfrac{\omicron^{\star}[a]}{a}$| *no progress*
&nbsp;
$\psi[t]$| **Term Evaluation** |$\psi[t] \to t$
*native-call*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},\Nu x.t,{t_k}^{k\in{j+1}..n}\rbrace]}{\text{error}}$| *not expected abstraction*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},\text{error},{t_k}^{k\in{j+1}..n}\rbrace]}{\text{error}}$|
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..j-1},u_j,{t_k}^{k\in{j+1}..n}\rbrace]}{\lbrace{b_i}^{i\in1..j-1},\psi^{\star}[u_j],{t_k}^{k\in{j+1}..n}\rbrace}$| *eval arguments*
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..n}\rbrace]}{b_{result}\mid \text{error}}$ | $\delta$*-reduction*
*application*
&nbsp;|$\dfrac{\psi[u \ t]}{\psi^\star[u] \ t}$ | *1st term progress*
&nbsp;|$\dfrac{\psi[b\ t]}{\text{error}}$ | *not function*
&nbsp;|$\dfrac{\psi[\text{error}\ t]}{\text{error}}$ | *error function*
&nbsp;|$\dfrac{\psi[(0x.t_1) \ t_2]}{t_1}$ | *ignore*
&nbsp;|$\dfrac{\psi[(1x.t) \ u]}{(1x.t) \ \psi^\star[u]}$ | *2nd term progress*
&nbsp;|$\dfrac{\psi[(1x.t_1)\ \text{error}]}{\text{error}}$ | *error argument*
&nbsp;|$\dfrac{\psi[(1x.\ t)\ d]}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
*equivalent*||*+reflection*
&nbsp;|$\dfrac{\psi[\text{error}{\equiv}t]}{\text{error}}$ | *error term*
&nbsp;|$\dfrac{\psi[u{\equiv}t]}{\psi^{\star}[u]{\equiv}t}$ | *term progress*
&nbsp;|$\dfrac{\psi[x_1{\equiv}x_1]}{x_1}$ | *same variables*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_1]}{b_1}$ | *same bytes*
&nbsp;|$\dfrac{\psi[b_1{\equiv}b_2]}{\text{error}}$ | *different bytes*
&nbsp;|$\dfrac{\psi[b_1{\equiv}\Nu x.t]}{\text{error}}$ |
&nbsp;|$\dfrac{\psi[\lbrace {t_i}^{i\in1..n}\rbrace{\equiv}\lbrace {t_j}^{j\in1..m}\rbrace]\qquad \text{where }n\ne m}{\text{error}}$ |
&nbsp;|$\dfrac{\psi[\lbrace {t_{1i}}^{i\in1..n}\rbrace{\equiv}\lbrace {t_{2i}}^{i\in1..n}\rbrace]}{\lbrace {(t_{1i}{\equiv}t_{2i})}^{i\in1..n}\rbrace}$ |
&nbsp;|$\dfrac{\psi[\lbrace {t_i}^{i\in1..n}\rbrace{\equiv}\Nu x.t_k]}{\text{error}}$ |
&nbsp;|$\dfrac{\psi[\Nu_1 x.t_1{\equiv}\Nu_2 x.t_2]\qquad \text{where } \Nu_1\ne\Nu_2}{\text{error}}$ |
&nbsp;|$\dfrac{\psi[\Nu_1 x.t_1{\equiv}\Nu_1 x.t_2]}{\Nu_1 x.t_1{\equiv}t_2}$ |
&nbsp;|$\dfrac{\psi[(t_{11}\ t_{12})\ {\equiv}\ (t_{21}\ t_{22})]}{(t_{11}{\equiv}t_{21})\ (t_{12}{\equiv}t_{22})}$ |
*otherwise*
&nbsp;|$\dfrac{\psi[t]}{t}$ | *no evaluation rule*
&nbsp;
$\psi[e]$|**Expression Evaluation**|$\psi[e]\longrightarrow e$
*typed-term*
&nbsp;|$\dfrac{\psi[t{:}R]}{t{:}\psi^\star[R]}$| *eval type*
&nbsp;|$\dfrac{\psi[u{:}P]}{\psi^\star[u]{:}P}$| *eval term*
*let-binding*
&nbsp;|$\dfrac{\psi[\text{let }x{=}r\text{ in }e]}{\text{let }x{=}\psi^\star[r]\text{ in }e}$| *value progress*
&nbsp;|$\dfrac{\psi[\text{let } x{=}\text{error}{:}\star \text{ in } e]}{\text{error}{:}\star}$| *error value*
&nbsp;|$\dfrac{\psi[\text{let } x{=}v \text{ in } e]}{[x\mapsto v]\ e}$| *substitution*
*unlock*
&nbsp;|$\dfrac{\psi[q \ e]}{\psi^\star[q] \ e}$| *function progress*
&nbsp;|$\dfrac{\psi[\star\ e]}{\text{error}{:}\star}$| *not function*
&nbsp;|$\dfrac{\psi[t{:}E\ e]}{(t\ \epsilon[e]){:}(E\ e)}$| *typed-term*
&nbsp;|$\dfrac{\psi[f\ q]}{f\ \psi^\star[q]}$| *argument progress*
&nbsp;|$\dfrac{\psi[f_1\ f_2]}{f_1\ \ \epsilon[f_2]{:}\tau[f_2]}$| *type argument*
&nbsp;|$\dfrac{\psi[(0x{:}E_1.e)\ \ t{:}E_2]}{\text{let }X{=}E_1{\equiv}E_2\text{ in }e}$| *unlock*
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
