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
$d ::=$ || *datum terms:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bytes*
&nbsp;| $\lambda x.t$ | *abstraction*
$u ::=$ || *reducible terms:*
&nbsp;| $\lbrace {b_i}^{i\in1..n}\rbrace$ | *native-call*
&nbsp;| $t \ t$ | *application*
$T ::=$ || *well-formed types/keys:*
&nbsp;| $\star$ | *type-of-types*
&nbsp;| $b{:}\star$ | *proper-type*
&nbsp;| $\lambda x{:}T.T$ | *function-type*
$e,E ::=$|| *expressions:*
&nbsp;| $x$ | *variable*
&nbsp;| $\star$ | *type-of-types*
&nbsp;| $t{:}E$ | *typed-term*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $\lambda  x{:}E.\ e$ | *lock*
&nbsp;| $e \ e$ | *unlock*
$v,V ::=$|| *value expressions:*
&nbsp;| $x$ | *variable*
&nbsp;| $\star$ | *type-of-types*
&nbsp;| $t{:}V$ | *typed value*
&nbsp;| $\lambda  x{:}V.\ e$ | *lock*
$r,R ::=$|| *reducible expressions:*
&nbsp;| $\text{let } x{=}e \text{ in } e$| *let-binding*
&nbsp;| $e \ e$ | *unlock*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}e$  | *variable binding*
&nbsp;
$f_i$| $\lambda x_i{:}E_i.e_i$ | *function*

## Notes

&nbsp;| **Notes**
:-:|:-- 
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$!a$| all term or expression except $a$ one
$\circeq$ | unknown equality, needs further evaluation
redex| *REDucible EXpression* is an expression on which we can perform a computation step.
## Operators

$\omicron^{\star}[a]$| **Multi-Step Operator** |$\omicron^{\star}[t] \to t$
:-:|:-:|--:
&nbsp;|$\dfrac{\omicron[a]}{a'}\vdash\dfrac{\omicron^{\star}[a]}{\omicron^{\star}[a']}$| *progress*
&nbsp;|$\dfrac{\omicron[a]}{a}\vdash\dfrac{\omicron^{\star}[a]}{a}$| *no-progress*
&nbsp;
$\psi[t]$| **Term Evaluation** |$\psi[t] \to t$
&nbsp;|$\dfrac{\psi[\lbrace{b_i}^{i\in1..n}\rbrace]}{b_{result}}$ | $\delta$*-reduction*
&nbsp;|$\dfrac{\psi[u_1 \ t_2]}{\psi^\star[u_1] \ t_2}$ | *function progress*
&nbsp;|$\dfrac{\psi[b\ t_2]}{\text{error}}$ | *wrong function*
&nbsp;|$\dfrac{\psi[\text{error}\ t_2]}{\text{error}}$ | *error function*
&nbsp;|$\dfrac{\psi[(\lambda x.t_1) \ u_2]}{(\lambda x.t_1) \ \psi^\star[u_2]}$ | *argument progress*
&nbsp;|$\dfrac{\psi[(\lambda x.t_1)\ \text{error}]}{\text{error}}$ | *error argument*
&nbsp;|$\dfrac{\psi[(\lambda x.\ t)\ d]}{[x\mapsto d]\ t}$ | $\beta$*-reduction*
&nbsp;|$\dfrac{\psi[t]}{t}$ | *otherwise (no evaluation rule)*
&nbsp;
$\xi[e]$|**Expression Evaluation**|$\xi[e]\longrightarrow e$
&nbsp;|| *typed-term*
&nbsp;|$\dfrac{\xi[t{:}R]}{t{:}\xi[R]}$ | *type progress*
&nbsp;|$\dfrac{\xi[t{:}t_1{:}E_1]}{t{:}\phi^\star[t_1{:}E_1]}$ | *typed-term fusion*
&nbsp;|$\dfrac{\xi[t{:}(\lambda x_1{:}E_2.e_3))]}{t{:}(\lambda x_1{:}\xi^\star[E_2].\xi^\star[e_3])}$ | *under abstraction*
&nbsp;|$\dfrac{\xi[t{:}\text{error}{:}\star]}{\text{error}{:}\star}$ | *error type*
&nbsp;|$\dfrac{\xi[u{:}T{:}\star]}{\xi[u]{:}T{:}\star}$ | *well-typed term progress*
&nbsp;|| *let-binding*
&nbsp;|$\dfrac{\xi[\text{let }x{=}r\text{ in }e]}{\text{let }x{=}\xi^\star[r]\text{ in }e}$| *value progress*
&nbsp;|$\dfrac{\xi[\text{let } x{=}\text{error}{:}\star \text{ in } e]}{\text{error}{:}\star}$| *error value*
&nbsp;|$\dfrac{\xi[\text{let } x{=}v \text{ in } e]}{[x\mapsto v]\ e}$| *substitution*
&nbsp;|| *lock*
&nbsp;|$\dfrac{\xi[\lambda x{:}R.e]}{\lambda x{:}\xi[R].e}$ | *argument type progress*
&nbsp;|$\dfrac{\xi[\lambda x{:}\text{error}{:}\star.e]}{\text{error}{:}\star}$ | *error-typed argument*
&nbsp;|| *unlock*
&nbsp;|$\dfrac{\xi[r_1 \ e_2]}{\xi[r_1] \ e_2}$| *function progress*
&nbsp;|$\dfrac{\xi[\star\ e_2]}{\text{error}{:}\star}$| *wrong function*
&nbsp;|$\dfrac{\xi[t_1{:}E_1\ e_2]}{(t_1\ \epsilon[e_2]){:}(E_1\ e_2)}$| *typed-term*
&nbsp;|$\dfrac{\xi[f_1\ r_2]}{(\lambda x{:}E_1.e_1)\ \xi^\star[r_2]}$| *argument progress*
&nbsp;|$\dfrac{f_1\ f_2}{f_1\ \ \epsilon[f_2]{:}\tau[f_2]}$| *type argument*
&nbsp;|$E_1{=} E_2 \vdash \dfrac{(\lambda x_1{:}E_1.e_1)\ \ t_2{:}E_2}{\text{let } x_1{=}t_2{:}E_2\text{ in }e_1}$| *unlock*
&nbsp;|$E_1{\ne} E_2 \vdash \dfrac{(\lambda x_1{:}E_1.e_1)\ \ t_2{:}E_2}{\text{error}{:}\star}$| *type eror*
&nbsp;|$E_1{\circeq} E_2 \vdash \dfrac{(\lambda x_1{:}E_1.e_1)\ \ t_2{:}E_2}{(\lambda x_1{:}\xi^\star[E_1].e_1)\ \ t_2{:}\xi^\star[E_2]}$| *further eval*
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
