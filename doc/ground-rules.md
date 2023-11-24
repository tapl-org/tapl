## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *terms:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lbrace {(x{\mid}b)_i}^{i\in1..n}\rbrace$ | *native-call*
&nbsp;| $\lambda x.\ t$ | *abstraction*
&nbsp;| $t \ t$ | *application*
&nbsp;| $\text{error}$ | *run-time-error*
$d ::=$ || $b\subset t\quad$ *datum:*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lambda x.t$ | *abstraction*
$e,E ::=$|| *expressions:*
&nbsp;| $x$ | *variable*
&nbsp;| $t{:}E$ | *typed-term*
&nbsp;| $\lambda  x{:}E.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $\star$ | *type-of-types*
$K ::=$ || $K\subset E\quad$ *kinds:*
&nbsp;| $\star$ | *proper-kind*
&nbsp;| $\lambda x{:}T.K$ | *function-kind*
$T ::=$ || $T\subset E\quad$ *types/keys:*
&nbsp;| $x$ | *variable*
&nbsp;| $b{:}\star$ | *proper-type*
&nbsp;| $\lambda x{:}T.e \quad\text{where }\tau[e]{\equiv}K$ | *function-type*
$v ::=$|| $v\subset e\quad$ *values:*
&nbsp;| $d{:}T$ | *typed value*
&nbsp;| $\lambda  x{:}T.\ e$ | *lock*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}E$  | *variable binding*

## Notes

&nbsp;| **Notes**
:-:|:-- 
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
## Operators

$\psi[t]$| **Term Evaluation** |$\psi[t] \to t'$
:-:|:-:|--:
&nbsp;|$\dfrac{\lbrace{b_i}^{i\in1..n}\rbrace}{{\ll}\text{native call}{\gg}}$ | $\delta$*-reduction*
$t\ t$|$t_1{\rightarrow}t_1' \vdash \dfrac{t_1 \ t_2}{t_1' \ t_2}$ | *function progress*
&nbsp;|$\dfrac{\text{error}\ t_2}{\text{error}}$ | *error function*
$d\ t$|$t_2{\rightarrow}t_2' \vdash \dfrac{d_1 \ t_2}{d_1 \ t_2'}$ | *argument progress*
&nbsp;|$\dfrac{v_1\ \text{error}}{\text{error}}$ | *error argument*
$d\ d$|$\dfrac{b\ d_2}{\text{error}}$ | *wrong function*
&nbsp;|$\dfrac{(\lambda x.\ t)\ d}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
&nbsp;
&nbsp;|**Expression**|$e\longrightarrow e'$
&nbsp;|$E{\rightarrow}E'\vdash\dfrac{t{:}E}{t{:}E'}$ | *type progress of typed term*
&nbsp;|$E{\nrightarrow}E'\vdash\dfrac{t{:}E}{t{:}\omega[E]}$ | *check well-typed term*
&nbsp;|$\dfrac{t{:}\text{error}{:}\star}{\text{error}{:}\star}$ | *error-typed term*
&nbsp;|$t{\rightarrow}t'\vdash\dfrac{t{:}T}{t'{:}T}$ | *well-typed term progress*
&nbsp;|$E{\rightarrow}E'\vdash\dfrac{\lambda x{:}E.e}{\lambda x{:}E'.e}$ | *type progress of lock*
&nbsp;|$E{\nrightarrow}E'\vdash\dfrac{\lambda x{:}E.e}{\lambda x{:}\omega[E].e}$ | *check well-typed lock*
&nbsp;|$\dfrac{\lambda x{:}\text{error}{:}\star.e}{\text{error}{:}\star}$ | *error-typed lock*
$e\ e$|$e_1{\rightarrow}e_1' \vdash \dfrac{e_1 \ e_2}{e_1' \ e_2}$| *function progress*
&nbsp;|$\dfrac{\text{error}{:}\star\ e_2}{\text{error}{:}\star}$| *error function*
$v\ e$|$\dfrac{e_2}{e_2'} \vdash \dfrac{v_1 \ e_2}{v_1 \ e_2'}$| *argument progress*
&nbsp;|$\dfrac{v_1\ \ (\lambda x_1{:}T_1.e_1)}{v_1\ \ \epsilon[\lambda x_1{:}T_1.e_1]{:}\tau[\lambda x_1{:}T_1.e_1]}$| *type argument*
$v\ t{:}T$|$\dfrac{d_1{:}\star\ t_2{:}T_2}{\text{error}{:}\star}$| *wrong function 1*
&nbsp;|$\dfrac{d_{11}{:}d_{12}{:}\star\ t_2{:}T_2}{\text{error}{:}\star}$| *wrong function 2*
&nbsp;|$\dfrac{d_1{:}(\lambda x_1{:}T_1.e_2)\ \ t_2{:}T_2}{(d_1\ t_2){:}((\lambda x_1{:}T_1.e_2)\ \ t_2{:}T_2)}$| *unlock 1*
&nbsp;|$\dfrac{(\lambda x{:}T_1.e)\ \ t_2{:}T_2\quad \text{where }T_1{\neq}T_2}{\text{error}{:}!{:}*}$| *type error*
&nbsp;|$\dfrac{(\lambda x{:}T_1.e)\ \ t_2{:}T_2\quad \text{where }T_1{=}T_2}{\text{let } x{=}t_2{:}T_2\text{ in }e}$| *unlock 2*
$\text{let}$|$e_1{\rightarrow}e_1' \vdash \dfrac{\text{let }x{=}e_1\text{ in }e_2}{\text{let }x{=}e_1'\text{ in }e_2}$| *let-binding progress*
&nbsp;|$\dfrac{\text{let } x{=}\text{error}{:}\star \text{ in } e}{\text{error}{:}\star}$| *error let-binding*
&nbsp;|$\dfrac{\text{let } x{=}v \text{ in } e}{[x\mapsto v]\ e}$| *let-binding substitution*
&nbsp;
$\epsilon[e]$| **Type erasure** | $\epsilon[e] \to t$
&nbsp;|$\dfrac{\epsilon[x]}{x}$| *variable*
&nbsp;|$\dfrac{\epsilon[t{:}E]}{t}$| *typed term*
&nbsp;|$\dfrac{\epsilon[\lambda x{:}E.e]}{\lambda x.\epsilon[e]}$| *lock*
&nbsp;|$\dfrac{\epsilon[e_1\ e_2]}{\epsilon[e_1]\ \epsilon[e_2]}$| *unlock*
&nbsp;|$\dfrac{\epsilon[\text{let } x{=}e_1 \text{ in } e_2]}{(\lambda x.\epsilon[e_2])\ \epsilon[e_1]}$| *let-binding*
&nbsp;|$\dfrac{\epsilon[\star]}{\text{error}}$ | *type of types*
&nbsp;
$\phi[E]$| **Type forming** | $\phi[E] \to T$
&nbsp;|$\dfrac{\rho[x]}{x}$| *variable*
&nbsp;|$\dfrac{\rho[t{:}x]}{t{:}x}$| *variable type in typed-term*
&nbsp;|$\dfrac{\rho[t{:}t{:}E]}{error{:}\star}$| *typed-term type in typed-term*
&nbsp;|$\dfrac{\rho[t{:}t{:}E]}{error{:}\star}$| *typed-term type in typed-term*
&nbsp;|$\dfrac{\epsilon[\lambda x{:}E.e]}{\lambda x.\epsilon[e]}$| *lock*
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
$\xi[E]$| **Merge typed term** | $\xi[E] \to (T{\mid}\text{error}{:}\star)$
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
