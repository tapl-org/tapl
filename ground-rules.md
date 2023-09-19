&nbsp;|**Syntax**|&nbsp;
---|---|---:
$e,E ::=$ || *expression:*
&nbsp;| $*$ | *atom*
&nbsp;| $b$ | *bits*
&nbsp;| $x$ | *variable*
&nbsp;| $\lambda x{:}T.\;t$ | *abstraction*
&nbsp;| $t \; t$ | *application*
$t,T ::=$|| *term:*
&nbsp;| $e$ | *expression*
&nbsp;| $e{:}T$ | *typed expression*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

**Derived forms**|&nbsp;|&nbsp;
---|:---:|---:
$c,C$| $\lambda x{:}T.\;t \quad \|\text{FV}(\lambda x{:}T.\;t)\|{=}0$| closed abstraction
$T_1{\to}T_2$| $\lambda x{:}T_1.\;T_2 \quad x\notin \text{FV}(T_2)$|type of function
$v,V$| $b \mid \lambda x{:}V.\;t$|value
$d,D$| $b \mid C \mid D{\to}D \mid v{:}D$|datum

**Operators**|&nbsp;
:--:|:--
$\theta$| *Evaluation*
$\tau$| *Typing*
$\epsilon$| *Type erasure*
$\delta$| *Built-in function call*
$\triangle$| *Raise error*

&nbsp;|**Rules**|&nbsp;
--:|:---:|---:
1|$\dfrac{\theta[b]}{b}$ | *eval bits*
2|$\dfrac{\theta[x]}{x}$ | *eval variable*
3|$\dfrac{\theta[\lambda x{:}T.\;t]}{\lambda x{:}\theta[T].\;t}$ | *eval abstraction*
4|$\dfrac{\theta[b{:}(\lambda x{:}T_{11}.T_{12})\;v_2{:}T_2] \qquad T_{11}{\equiv}T_2}{\delta[b(v_2)]{:}T_{12}}$ | *$\delta$-reduction*
5|$\dfrac{\theta[b{:}(\lambda x{:}T_{11}.T_{12})\;v_2{:}T_2] \qquad T_{11}{\not\equiv}T_2}{\triangle{\text{TypeError}}}$ | *$\delta$-reduction error*
6|$\dfrac{\theta[x\;t]}{x \; t}$ | *skip eval for variable*
7|$\dfrac{\theta[\lambda x{:}T_1.t_1\;v_2{:}T_2] \qquad T_1{\equiv}T_2}{\theta[\;\|x\mapsto v_2{:}T_2\|t_1\;]}$ | *$\beta$-reduction*
8|$\dfrac{\theta[\lambda x{:}T_1.t_1\;v_2{:}T_2] \qquad T_1{\not\equiv}T_2}{\triangle{\text{TypeError}}}$ | *$\beta$-reduction error*
9|$\dfrac{\theta[t_1\;t_2]}{\theta[\epsilon[t_1]]{:}\tau[t_1]\; \theta[t_2]}$ | *eval application*
&nbsp;
9|$\dfrac{e \; s}{e{:}\tau[e]\;s}$ | *type application function*
9|$\dfrac{s \; e}{s\;e{:}\tau[e]}$ | *type application argument*
9|$\dfrac{t_1 \; t_2}{(t_1 \; t_2){:}\tau[t_1 \; t_2]}$ | *type application*
1|$\dfrac{\tau[d]}{*}$| *typeof bits*
5|$\dfrac{\lambda x{:}T_1.\;e{:}T_2 \qquad x\notin \text{FV}(e{:}T_2)}{(\lambda x{:}T_1.\; e{:}T_2){:}*}$| *type abstraction:free*
9|$\dfrac{\tau[e_1{:}T_1 \; e_1{:}T_2]}{T_1 \; e_2{:}T_2}$ | *typeof application*
&nbsp;
3|$\dfrac{T \longrightarrow T'}{\lambda x{:}T.\;t \longrightarrow \lambda x{:}T'.\;t}$ | *eval abstraction parameter type*
6|$\dfrac{t_1 \longrightarrow t_1'}{t_1 \; t_2 \longrightarrow t_1' \; t_2}$ | *eval application function*
7|$\dfrac{t_2 \longrightarrow t_2'}{t_1 \; t_2 \longrightarrow t_1 \; t_2'}$ | *eval appplication argument*
10|$\dfrac{((\lambda x{:}T.e_1{:}T)!e_2):V}{[x\mapsto e_2]e_1:V}$ | *$\beta$-reduction*

&nbsp;|**Typing**|&nbsp;
--:|:---:|---:
9|$\dfrac{e_1{:}T_1 \; e_2{:}T_2}{(e_1 \; e_2){:}(T_1\;e_2{:}T_2)}$ | *type application*
2|$\dfrac{\Gamma, x{:}T \vdash x}{\Gamma, x{:}T \vdash x{:}T}$| *type variable*
&nbsp;
5|$\dfrac{\lambda x{:}T_1.\;e{:}T_2 \qquad x\in \text{FV}(e{:}T_2)}{(\lambda x{:}T_1.\; e{:}T_2){:}(\lambda x{:}T_1.\; T_2)}$| *type abstraction:bound*
9|$\dfrac{e_1{:}T_1 \; e_2{:}T_2}{(e_1{!}e_2){:}(T_1 \; e_2{:}T_2)}$ | *type application*

&nbsp;|**Evaluation**|&nbsp;
--:|:---:|---:
4|$\dfrac{t \longrightarrow t'}{\lambda x{:}T.\;t \longrightarrow \lambda x{:}T.\;t'}$ | *eval abstraction body*
6|$\dfrac{t_1 \longrightarrow t_1'}{t_1 \; t_2 \longrightarrow t_1' \; t_2}$ | *eval application function*
7|$\dfrac{t_2 \longrightarrow t_2'}{t_1 \; t_2 \longrightarrow t_1 \; t_2'}$ | *eval appplication argument*
12|$\dfrac{E \longrightarrow E'}{t{:}E  \longrightarrow t{:}E'}$ | *eval type of term*
13|$\dfrac{t \longrightarrow t'}{t'{:}V  \longrightarrow t'{:}V}$ | *eval term of term*
11|$\dfrac{b!e:V}{{\ll}\text{built-in call}{\gg}\;b(e):V}$ | *$\delta$-reduction*
11|$\dfrac{*!e:V}{{\ll}\text{raise error}{\gg}\;}$ | *atom-as-function*
14|$\dfrac{(t{:}V_1){:}V_1}{t{:}V_1}$| *merge*
&nbsp;



Note:
* The underscore can be used to ignore variables and types that aren’t used anywhere in the code.
* Untyped expression should be typed
* `atom` represents a zero size imaginary bits
* type of `atom` is `atom`
* two `bits` are equal if they have the same bits in the same order

Note: Any value can be comparable for equivality which returns true or false

$$
\begin{matrix}
1 & 2 & 3 \\
4 & 5 & 6 \\
7 & 8 & 9
\end{matrix}
$$
