&nbsp;|**Syntax**|&nbsp;
---|---|---:
$d ::=$ || *datum:*
&nbsp;| $b$ | *binary data*
&nbsp;| $d{\to}d$ | *type of function*
$t ::=$ || *term:*
&nbsp;| $x$ | *variable*
&nbsp;| $d$ | *datum*
&nbsp;| $\lbrace {(x{\mid}d)_i}^{i\in1..n}\rbrace$ | *built-in function*
&nbsp;| $\lambda x.\ t$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $\text{error}$ | *run-time error*
$v ::=$|| *value:*
&nbsp;| $d$ | *datum*
&nbsp;| $\lambda x.t$ | *abstraction*
$T ::=$ || *type:*
&nbsp;| $x$ | *variable*
&nbsp;| $d$ | *datum*
&nbsp;| $T{\to}T$ | *type of function*
$e ::=$|| *expression:*
&nbsp;| $x$ | *variable*
&nbsp;| $t{:}T$ | *typed term*
&nbsp;| $\lambda  x{:}T.\ e$ | *exp-abstraction*
&nbsp;| $e \ e$ | *exp-application*
&nbsp;| $\text{let [lazy] } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $\text{error}$ | *run-time error*
$w ::=$|| *whole:*
&nbsp;| $v{:}d$ | *datum*
&nbsp;| $\lambda  x{:}d.\ e$ | *abstraction*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

&nbsp;| **Operators**
:-:|---
$\epsilon[e]$ | type erasure
$\tau[e]$ | type of expression
$e \longrightarrow e'$|$e$ evaluates to $e'$ in one step

**Type erasure rules**|$\epsilon[e] \to t$
:---:|---:
$\dfrac{\epsilon[x]}{x}$| *variable*
$\dfrac{\epsilon[t{:}T]}{t}$| *typed term*
$\dfrac{\epsilon[\lambda x{:}T.e]}{\lambda x.\epsilon[e]}$| *exp-abstraction*
$\dfrac{\epsilon[\text{let [lazy] } x{=}e_1 \text{ in } e_2]}{\text{let } x{=}\epsilon[e_1] \text{ in } \epsilon[e_2]}$| *let-binding*
$\dfrac{\epsilon[e_1\ e_2]}{\epsilon[e_1]\ \epsilon[e_2]}$| *exp-abstraction*

&nbsp;|**Builtin binary data or functions**
:---:|:--
$Type$| binary data which contains "Type" string


**Type of expression rules**| $\tau[e] \to e$
:---:|---:
$\dfrac{x{:}T\in\Gamma \qquad \tau[x]}{\Gamma \vdash T{:}Type}$| *variable*
$\dfrac{\Gamma \vdash \tau[t{:}T]}{\Gamma \vdash T{:}Type}$| *typed term*
$\dfrac{\Gamma \vdash \tau[\lambda x{:}T.e]}{\Gamma \vdash \lambda x{:}T.\tau[e]}$| *exp-abstraction*
$\dfrac{\Gamma \vdash \tau[e_1\ e_2]}{\Gamma \vdash \tau[e_1]\ e_2}$| *exp-application*
$\dfrac{\Gamma \vdash \tau[\text{let [lazy] } x_1{=}e_1 \text{ in } e_2]}{\Gamma \vdash \text{let } x_2{=}\tau[e_1]\text{ in } \text{let lazy } x_1{=}\epsilon[e_1]{:}x_2 \text{ in } \tau[e_2]}$| *let-binding*

**Term evaluation rules**|$t\longrightarrow t'$
:---:|---:
$\{{d_i}^{i\in1..n}\} \longrightarrow {\ll}\text{built-in call}{\gg}$ | $\delta$*-reduction*
$\dfrac{t_1 \longrightarrow t_1'}{t_1 \; t_2 \longrightarrow t_1' \; t_2}$ | *application 1*
$\text{error}\ t_2\longrightarrow \text{error}$ | *application error 1*
$\dfrac{t_2 \longrightarrow t_2'}{v_1 \; t_2 \longrightarrow v_1 \; t_2'}$ | *application 2*
$v_1 \ \text{error}\longrightarrow \text{error}$ | *application error 2*
$b\ v\longrightarrow \text{error}$ | *application error 3*
$(\lambda x.\;t)\;v \longrightarrow [x\mapsto v]\ t$ | $\beta$*-reduction*


&nbsp;|**Expression evaluation rules**|$e\longrightarrow e'$
--:|:---:|---:
1|$\dfrac{t \longrightarrow t'}{t{:}d\longrightarrow t'{:}d}$ | *typed term*
2|$\text{error}{:}d\longrightarrow \text{error}$| *typed error term*
3|$\dfrac{e_1 \longrightarrow e_1'}{e_1 \  e_2 \longrightarrow e_1' \  e_2}$ | *application 1*
4|$\text{error}\ e_2\longrightarrow \text{error}$ | *application error 1*
5|$\dfrac{e_2 \longrightarrow e_2'}{w_1 \  e_2 \longrightarrow w_1 \  e_2'}$ | *application 2*
6|$w_1 \ \text{error}\longrightarrow \text{error}$ | *application error 2*
7|$w_1\ \ (\lambda x_1{:}d_1.e_1) \longrightarrow w_1\ \ (\text{let } x_2{=}\tau[e_1] \text{ in } \epsilon[e_1]{:}x_2)$  | *application 3*
8|$(\lambda x.t_1){:}d_1{\to}d_2\ \ v{:}d_1\longrightarrow \text{let } x{=}v{:}d_1 \text{ in } t_1{:}d_2$| *apply 1*
9|$(\lambda x{:}d_1.e_1)\ \ v{:}d_1\longrightarrow \text{let } x{=}v{:}d_1 \text{ in } e_1$| *apply 2*
10|$w_1 \ w_2\longrightarrow \text{error}$ | *apply error*
11|$\text{let lazy } x{=}e_1 \text{ in } e_2\text{ where } x\notin FV(e_2)\longrightarrow e_2$| *lazy let-binding 1*
12|$\text{let lazy } x{=}e_1 \text{ in } e_2\longrightarrow \text{let } x{=}e_1 \text{ in } e_2$| *lazy let-binding 2*
13|$\dfrac{e_1 \longrightarrow e_1'}{\text{let } x{=}e_1 \text{ in } e_2 \longrightarrow \text{let } x{=}e_1' \text{ in } e_2}$ | *let-binding 1*
14|$\text{let } x{=}(\lambda x_1{:}d_1.e_1) \text{ in } e \longrightarrow [x\mapsto w]\ e$ | *let-binding 2*
15|$\text{let } x_3{=}(\lambda x_1{:}d_1.e_1) \text{ in } e_2\longrightarrow \text{let } x_3{=}(\text{let } x_2{=}\tau[e_1] \text{ in } \epsilon[e_1]{:}x_2) \text{ in } e_2$| *let-binding 3*
16|$\text{let } x{=}w \text{ in } e \longrightarrow [x\mapsto w]\ e$ | *let-binding 4*


Note:

* $[x\mapsto v{:}d]\ t{:}T \quad \equiv \quad ([x\mapsto v]\ t){:}([x\mapsto v]\ T)$ 