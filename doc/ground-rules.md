&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t,T ::=$ || *term:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *binary data*
&nbsp;| $\lbrace b \ \ {o_i}^{i\in1..n}\rbrace$ | *built-in function*
&nbsp;| $\lambda x{:}T.\ e$ | *abstraction*
&nbsp;| $e \ e$ | *application*
&nbsp;| $\tau[e]$ | *type of expression*
&nbsp;| $![e]$ | *safe expression*
&nbsp;| $\text{error}$ | *run-time error*
$e ::=$|| *expression:*
&nbsp;| $t$ | *term*
&nbsp;| $t{:}T$ | *typed term*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

&nbsp;|Built-in binary data
:-:|---
$*$| a star to represent just type
$\{\text{TERM-EQUAL}\ o_1\ o_2\}$|checks equality of 2 terms

&nbsp;|**Derived forms**|&nbsp;
---|:---:|---:
$(e)$| $(e_1\ e_2)\ e_3\ \equiv\ e_1\ e_2\ e_3\ \not\equiv\ e_1\ (e_2\ e_3)$|grouping
$d,D$| $b\ \mid\ \lambda x{:}T.\ e $|datum
$o$| $x\ \mid\ d $|operand
$v,V$| $d\ \mid\ d{:}T$|value
$a,A$| $e\ e$|application
$e_1;e_2$| $(\lambda x{:}T.\;e_2) \; e_1 \quad \text{where } x \notin \text{FV}(e_2) \text{ and } \tau[e_1]\equiv T$| sequencing notation
$\text{TermEqual}$| $\lambda x_1{:}*.\lambda x_2{:}*.\{\text{TERM-EQUAL}\ x_1\ x_2\}$| check term equality
$T_1{\to}T_2$| $\lambda x{:}T_1.\ T_2 \quad x\notin \text{FV}(T_2)$|type of function
$c,C$| $\lambda x{:}T.\ e \quad \text{where }\|\text{FV}(\lambda x{:}T.\ e)\|{=}0$| closed abstraction
**Evaluation**|&nbsp;|&nbsp;
$e \longrightarrow e'$|$e$ evaluates to $e'$ in one step|&nbsp;


&nbsp;|**Evaluation rules**|&nbsp;
--:|:---:|---:
1|$\{b \; {d_i}^{i\in1..n}\} \longrightarrow {\ll}\text{built-in call}{\gg}$ | $\delta$*-reduction*
2|$\dfrac{e_1 \longrightarrow e_1'}{e_1 \; e_2 \longrightarrow e_1' \; e_2}$ | *application 1*
3|$\text{error}\ e_2\longrightarrow \text{error}$ | *application error 1*
4|$\dfrac{e_2 \longrightarrow e_2'}{v_1 \; e_2 \longrightarrow v_1 \; e_2'}$ | *application 2*
5|$v_1 \ \text{error}\longrightarrow \text{error}$ | *application error 2*
6|$\dfrac{(\lambda x{:}T.\;e)\;v}{[x\mapsto v]\;e}$ | $\beta$*-reduction*
7|$\dfrac{v_1\;v_2}{\text{error}}$ | *application error 3*
8|$\dfrac{x{:}T\in\Gamma}{\tau[x] \longrightarrow T}$ | *type variable*
9|$\tau[b] \longrightarrow \text{error}$ | *type binary data*
10|$\tau[\{b\;{o_i}^{i\in1..n}\}] \longrightarrow \text{error}$ | *type built-in function*
11|$\tau[\lambda x{:}T.\;e] \longrightarrow \lambda x{:}T.\tau[e]$ | *type abstraction*
12|$\tau[e_1 \  e_2] \longrightarrow \tau[e_1]\; e_2$ | *type application*
13|$\tau[t{:}T]\longrightarrow T$ | *type typed term*
14|$\dfrac{![a] \longrightarrow a'}{![a\ e] \longrightarrow\ ![a'\ e]}$ | *safe application 1*
15|$\dfrac{![a] \longrightarrow a'}{![e\ a] \longrightarrow\ ![e'\ a]}$ | *safe application 2*
16|$\dfrac{![(\lambda x{:}T.\;e)\ v]}{\text{TermEqual}\ ![T]\ ![\tau[v]{:}*];\ (\lambda x{:}T.\;e)\ v}$ | *safe application 3*
17|$\dfrac{e \longrightarrow e'}{![e] \longrightarrow\ ![e']}$ | *safe expression 1*
18|$\dfrac{![e]}{![\tau[e]];\;e}$ | *safe expression 2*




Note: Any datum can be comparable for equivality which returns true or false
