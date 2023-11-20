## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$d ::=$ || *datum:*
&nbsp;| $b$ | *bytes*
&nbsp;| $d{\to}d$ | *type of function*
$t ::=$ || *term:*
&nbsp;| $x$ | *variable*
&nbsp;| $d$ | *datum*
&nbsp;| $\lbrace {(x{\mid}d)_i}^{i\in1..n}\rbrace$ | *native call*
&nbsp;| $\lambda x.\ t$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $\text{error}$ | *run-time error*
$v ::=$|| *value:*
&nbsp;| $d$ | *datum*
&nbsp;| $\lambda x.t$ | *abstraction*
$T ::=$ || *type/key:*
&nbsp;| $x$ | *variable*
&nbsp;| $d$ | *datum*
$e ::=$|| *expression:*
&nbsp;| $x$ | *variable*
&nbsp;| $t{:}T$ | *typed term*
&nbsp;| $\lambda  x{:}T.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
$w ::=$|| *whole:*
&nbsp;| $v{:}d$ | *typed value*
&nbsp;| $\lambda  x{:}d.\ e$ | *lock*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

## Notes

&nbsp;|**Built-in bytes, or notes**
:---:|:--
$*$| bytes{'*'}. Represents for type of type.
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
&nbsp;|$\dfrac{[x{\mapsto}w]t{:}T}{([x{\mapsto}w]t){:}([x{\mapsto}\xi[w]]T)}$| *typed term*
&nbsp;|$\dfrac{[x{\mapsto}w](\lambda x{:}T.e)}{(\lambda x{:}[x{\mapsto}\xi[w]]T.[x{\mapsto}w]e)}$| *lock*
&nbsp;|$\dfrac{[x{\mapsto}w](e_1\ e_2)}{[x{\mapsto}w]e_1\ [x{\mapsto}w]e_2}$| *unlock*
&nbsp;|$\dfrac{[x{\mapsto}w](\text{let }x{=}e_1\text{ in }e_2)}{\text{let }x{=}[x{\mapsto}w]e_1\text{ in }[x{\mapsto}w]e_2}$| *let-binding*
&nbsp;|$\text{escalate error if whole expression to type has error}$ | *error*
&nbsp;
$\xi[w]$| **Whole Expression to Type** | $\xi[w]\to T$
&nbsp;|$\dfrac{\xi[d_1{:}d_2]}{d_1}$| *typed value*
&nbsp;|$\dfrac{\xi[(\lambda x.v){:}d_1{\to}d_2]\quad\text{where }\|FV(v)\|{=}0}{d_1{\to}\xi[v{:}d_2]}$| *typed abstraction*
&nbsp;|$\dfrac{\xi[\lambda x{:}d_1.v]\quad\text{where }\|FV(v)\|{=}0}{d_1{\to}\xi[v]}$| *lock*
&nbsp;|$\text{rule not found error}$ | *otherwise*

## Evaluation rules

&nbsp;| **Term** |$t\to t'$
:-:|:--:|---:
&nbsp;|$\dfrac{\lbrace{d_i}^{i\in1..n}\rbrace}{{\ll}\text{native call}{\gg}}$ | $\delta$*-reduction*
$t\ t$|$\dfrac{t_1}{t_1'} \vdash \dfrac{t_1 \ t_2}{t_1' \ t_2}$ | *application progres 1*
&nbsp;|$\dfrac{\text{error}\ t_2}{\text{error}}$ | *term error 1*
$v\ t$|$\dfrac{t_2}{t_2'} \vdash \dfrac{v_1 \ t_2}{v_1 \ t_2'}$ | *application progress 2*
&nbsp;|$\dfrac{v_1\ \text{error}}{\text{error}}$ | *term error 2*
$v\ v$|$\dfrac{b\ v_2}{\text{error}}$ | *term error 3*
&nbsp;|$\dfrac{d_1{\to}d_2\ \ v_2}{d_2}$ | *constant function*
&nbsp;|$\dfrac{(\lambda x.\ t)\ v}{[x\mapsto v]\ t}$ | $\beta$*-reduction*
&nbsp;
&nbsp;|**Expression**|$e\longrightarrow e'$
&nbsp;|$\dfrac{t}{t'}\vdash\dfrac{t{:}d}{t'{:}d}$ | *typed term*
$e\ e$|$\dfrac{e_1}{e_1'} \vdash \dfrac{e_1 \ e_2}{e_1' \ e_2}$| *unlock progress 1*
&nbsp;|$\dfrac{\text{error}{:}d_1{\to}d_2\ \ e_2}{\text{error}{:}d_2}$| *exp error 1*
&nbsp;|$\dfrac{\text{error}{:}b\ \ e_2}{\text{error}{:}!}$| *exp error 2*
$w\ e$|$\dfrac{e_2}{e_2'} \vdash \dfrac{w_1 \ e_2}{w_1 \ e_2'}$| *unlock progress 2*
$w\ w$|$\dfrac{w_1\ \ (\lambda x_1{:}d_1.e_1)\quad \text{where } x_1 \notin FV(x_1{:}d_1\vdash\tau[e_1])}{w_1\ (\text{let } x_2{=}\tau[\lambda x_1{:}d_1.e_1]\text{ in } \epsilon[\lambda x_1{:}d_1.e_1]{:}x_2)}$| *to typed term*
&nbsp;|$\dfrac{w_1\ \ (\lambda x_1{:}d_1.e_1)\quad \text{where } x_1 \in FV(x_1{:}d_1\vdash\tau[e_1])}{\text{error}{:}!}$| *exp error 3*
$w\ v{:}d$|$\dfrac{w_1\ \text{error}{:}d}{\text{error}{:}!}$| *exp error 4*
$w\ v{:}d$|$\dfrac{v_1{:}b\ \ v_2{:}d}{\text{error}{:}!}$| *exp error 5*
&nbsp;|$\dfrac{v_1{:}d_1{\to}d_3\ \ v_2{:}d_2\quad \text{where }d_1{\neq}d_2}{\text{error}{:}!}$| *exp error 6*
&nbsp;|$\dfrac{v_1{:}d_1{\to}d_3\ \ v_2{:}d_2\quad \text{where }d_1{=}d_2}{(v_1\ v_2){:}d_3}$| *unlock 1*
&nbsp;|$\dfrac{(\lambda x{:}d_1.e)\ \ v_2{:}d_2\quad \text{where }d_1{\neq}d_2}{\text{error}{:}!}$| *exp error 6*
&nbsp;|$\dfrac{(\lambda x{:}d_1.e)\ \ v_2{:}d_2\quad \text{where }d_1{=}d_2}{\text{let } x{=}v_2{:}d_2\text{ in }e}$| *unlock 2*
$\text{let}$|$\dfrac{e_1}{e_1'} \vdash \dfrac{\text{let }x{=}e_1\text{ in }e_2}{\text{let }x{=}e_1'\text{ in }e_2}$| *let-binding progress*
&nbsp;|$\dfrac{\text{let } x{=}w \text{ in } e}{[x\mapsto w]\ e}$| *let-binding substitution*
