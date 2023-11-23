## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *term:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lbrace {(x{\mid}b)_i}^{i\in1..n}\rbrace$ | *native call*
&nbsp;| $\lambda x.\ t$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $\text{error}$ | *run-time error*
$d ::=$ || *datum:*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lambda x.t$ | *abstraction*
$e ::=$|| *expression:*
&nbsp;| $x$ | *variable*
&nbsp;| $t{:}T$ | *typed term*
&nbsp;| $\lambda  x{:}T.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $*$ | *type of types*
$T ::=$ || *type/key:*
&nbsp;| $x$ | *variable*
&nbsp;| $t{:}*$ | *proper type*
&nbsp;| $\lambda x{:}T.e$ | *type of function*
&nbsp;| $*$ | *type of types*
$v ::=$|| *value:*
&nbsp;| $t{:}T$ | *typed value*
&nbsp;| $\lambda  x{:}T.\ e$ | *lock*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

## Notes

&nbsp;|**Built-in bytes, or notes**
:---:|:--
$!$| bytes{'!'}. Just to annotate unknown type or type error.
$\dfrac{a}{a'}$|$a$ evaluates to $a'$ in one step.

## Operators

$\epsilon[e]$| **Type erasure** | $\epsilon[e] \to t$
:-:|:-:|--:
&nbsp;|$\dfrac{\epsilon[x]}{x}$| *variable*
&nbsp;|$\dfrac{\epsilon[t{:}T]}{t}$| *typed term*
&nbsp;|$\dfrac{\epsilon[\lambda x{:}T.e]}{\lambda x.\epsilon[e]}$| *lock*
&nbsp;|$\dfrac{\epsilon[e_1\ e_2]}{\epsilon[e_1]\ \epsilon[e_2]}$| *unlock*
&nbsp;|$\dfrac{\epsilon[\text{let } x{=}e_1 \text{ in } e_2]}{(\lambda x.\epsilon[e_2])\ \epsilon[e_1]}$| *let-binding*
&nbsp;
$\tau[e]$| **Type of expression** | $(\Gamma\vdash\tau[e]) \to e$
&nbsp;|$x{:}T\in\Gamma\ \vdash\ \dfrac{\Gamma\vdash\tau[x]}{T{:}*}$| *variable*
&nbsp;|$\dfrac{\Gamma \vdash \tau[t{:}T]}{T{:}*}$| *typed term*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\lambda x{:}T.e]}{\lambda x{:}T.(\Gamma, x{:}T \vdash \tau[e])}$| *lock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[e_1\ e_2]}{(\Gamma \vdash \tau[e_1])\ e_2}$| *unlock*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\text{let } x_1{=}e_1 \text{ in } e_2]\qquad \text{where }x_1 \notin FV(\Gamma,x_1{:}x_2\vdash\tau[e_2])}{\text{let } x_2{=}(\Gamma \vdash \tau[e_1])\text{ in } (\Gamma,x_1{:}x_2 \vdash \tau[e_2])}$| *let-binding*
&nbsp;|$\dfrac{\Gamma \vdash \tau[\text{let } x_1{=}e_1 \text{ in } e_2]\qquad \text{where } x_1 \in FV(\Gamma,x_1{:}x_2\vdash\tau[e_2])}{\text{let } x_2{=}(\Gamma \vdash \tau[e_1])\text{ in } \text{let } x_1{=}\epsilon[e_1]{:}x_2 \text{ in } (\Gamma,x_1{:}x_2 \vdash \tau[e_2])}$| *dependent typed let-binding*
&nbsp;
$[x{\mapsto}w]e$| **Expression substitution** | $[x{\mapsto}w]e\to e$
&nbsp;|$\dfrac{[x{\mapsto}w]x}{w}$| *variable*
&nbsp;|$\dfrac{[x{\mapsto}w]t{:}T}{([x{\mapsto}\epsilon[w]]t){:}([x{\mapsto}w]T)}$| *typed term*
&nbsp;|$\dfrac{[x{\mapsto}w](\lambda x{:}T.e)}{(\lambda x{:}[x{\mapsto}w]T.[x{\mapsto}w]e)}$| *lock*
&nbsp;|$\dfrac{[x{\mapsto}w](e_1\ e_2)}{[x{\mapsto}w]e_1\ [x{\mapsto}w]e_2}$| *unlock*
&nbsp;|$\dfrac{[x{\mapsto}w](\text{let }x{=}e_1\text{ in }e_2)}{\text{let }x{=}[x{\mapsto}w]e_1\text{ in }[x{\mapsto}w]e_2}$| *let-binding*
&nbsp;|$\dfrac{[x{\mapsto}w]*}{*}$ | *type of types*
&nbsp;

## Evaluation rules

&nbsp;| **Term** |$t\to t'$
:-:|:--:|---:
&nbsp;|$\dfrac{\lbrace{b_i}^{i\in1..n}\rbrace}{{\ll}\text{native call}{\gg}}$ | $\delta$*-reduction*
$t\ t$|$\dfrac{t_1}{t_1'} \vdash \dfrac{t_1 \ t_2}{t_1' \ t_2}$ | *function progress*
&nbsp;|$\dfrac{\text{error}\ t_2}{\text{error}}$ | *error function*
$d\ t$|$\dfrac{t_2}{t_2'} \vdash \dfrac{d_1 \ t_2}{d_1 \ t_2'}$ | *argument progress*
&nbsp;|$\dfrac{v_1\ \text{error}}{\text{error}}$ | *error argument*
$d\ d$|$\dfrac{b\ d_2}{\text{error}}$ | *wrong function*
&nbsp;|$\dfrac{(\lambda x.\ t)\ d}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
&nbsp;
&nbsp;|**Expression**|$e\longrightarrow e'$
&nbsp;|$\dfrac{t}{t'}\vdash\dfrac{t{:}*}{t'{:}*}$ | *type*
&nbsp;|$\dfrac{t}{t'}\vdash\dfrac{t{:}b{:}*}{t'{:}b{:}*}$ | *typed term*
$e\ e$|$\dfrac{e_1}{e_1'} \vdash \dfrac{e_1 \ e_2}{e_1' \ e_2}$| *function progress*
&nbsp;|$\dfrac{\text{error}{:}T_1\ e_2}{\text{error}{:}!{:}*}$| *error function*
$v\ e$|$\dfrac{e_2}{e_2'} \vdash \dfrac{v_1 \ e_2}{v_1 \ e_2'}$| *argument progress*
$v\ v$|$\dfrac{v_1\ \ (\lambda x_1{:}T_1.e_1)}{v_1\ \ \epsilon[\lambda x_1{:}T_1.e_1]{:}\tau[\lambda x_1{:}T_1.e_1]}$| *to typed term*
$v\ t{:}T$|$\dfrac{t_1{:}*\ t_2{:}T_2}{\text{error}{:}!{:}*}$| *wrong function 1*
&nbsp;|$\dfrac{t_1{:}t_2{:}*\ t_2{:}T_2}{\text{error}{:}!{:}*}$| *wrong function 2*
&nbsp;|$\dfrac{t_1{:}(\lambda x_1{:}T_1.e_2)\ \ t_2{:}T_2}{\text{let }x_3{=}((\lambda x_1{:}T_1.e_2)\ \ t_2{:}T_2)\text{ in }(t_1\ t_2){:}x_3}$| *unlock 1*
&nbsp;|$\dfrac{(\lambda x{:}T_1.e)\ \ t_2{:}T_2\quad \text{where }T_1{\neq}T_2}{\text{error}{:}!{:}*}$| *type error*
&nbsp;|$\dfrac{(\lambda x{:}T_1.e)\ \ t_2{:}T_2\quad \text{where }T_1{=}T_2}{\text{let } x{=}t_2{:}T_2\text{ in }e}$| *unlock 2*
$\text{let}$|$\dfrac{e_1}{e_1'} \vdash \dfrac{\text{let }x{=}e_1\text{ in }e_2}{\text{let }x{=}e_1'\text{ in }e_2}$| *let-binding progress*
&nbsp;|$\dfrac{\text{let } x{=}w \text{ in } e}{[x\mapsto w]\ e}$| *let-binding substitution*
