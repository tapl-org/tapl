&nbsp;|**Syntax**|&nbsp;
---|---|---:
$e,E ::=$ || *expression:*
&nbsp;| $*$ | *atom*
&nbsp;| $x$ | *variable*
&nbsp;| $`\lambda x{:}T.\;t`$ | *abstraction*
&nbsp;| $`t \; t`$ | *application*
&nbsp;| $`\{{t_i}^{i\in1..n} \}`$ | *tuple*
&nbsp;| $\tau[t]$ | *typeof*
$t,T ::=$|| *term:*
&nbsp;| $e$ | *expression*
&nbsp;| $e{:}T$ | *typed expression*
&nbsp;| $b{:}T$ | *bits*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

**Derived forms**|&nbsp;|&nbsp;
---|:---:|---:
$c,C$| $\lambda x{:}T.\;t \quad \|\text{FV}(\lambda x{:}T.\;t)\|{=}0$| closed abstraction
$d,D$| $b{:}D \mid c \mid c{:}D \mid \{{d_i}^{i\in1..n} \} $|datum
$T_1{\to}T_2$| $\lambda x{:}T_1.\;T_2 \quad x\notin \text{FV}(T_2)$|type of function
$v,V$| $b \mid \lambda x{:}V.\;t$|value


&nbsp;|**Rules**|&nbsp;
--:|:---:|---:
1|$`\dfrac{T \longrightarrow T'}{\lambda x{:}T.\;t \longrightarrow \lambda x{:}T'.\;t}`$ | *eval parameter type*
2|$`\dfrac{t_1 \longrightarrow t_1'}{t_1 \; t_2 \longrightarrow t_1' \; t_2}`$ | *eval application 1*
3|$`\dfrac{t_2 \longrightarrow t_2'}{d_1 \; t_2 \longrightarrow d_1 \; t_2'}`$ | *eval application 2*
4|$`\dfrac{(c \equiv \lambda x{:}T_1.\;t)\;d{:}T_2 \qquad d}{[x\mapsto d]t}`$ | $\beta$*-reduction*
5|$`\dfrac{b{:}D \; d}{{\ll}\text{built-in call}{\gg}\;b(d)}`$ | *$\delta$-reduction*
6|$`\dfrac{t_j \longrightarrow t_j'}{\{{d_i}^{i\in1..j-1}, t_j, {t_k}^{k\in{j+1}..n} \} \longrightarrow \{{d_i}^{i\in1..j-1}, t_j', {t_k}^{k\in{j+1}..n} \}}`$ | *eval tuple*
7|$`\dfrac{\tau[*]}{*}`$ | *type atom*
8|$`\dfrac{\tau[x] \qquad x{:}T\in\Gamma}{T}`$ | *type variable*
9|$`\dfrac{\tau[\lambda x{:}T.\;t]}{T{\to}\tau[t]}`$ | *type abstraction*
10|$`\dfrac{\tau[t_1 \; t_2]}{resultType{\;}\{\tau[t_1], \tau[t_2]\}}`$ | *type application*

&nbsp;






Comments:
* `resultType` is a builtin function which checks parameter and argument types and extracts result type from application
* `atom` represents a zero size imaginary bits
* type of `atom` is `atom`
* two `bits` are equal if they have the same bits in the same order

Note: Any datum can be comparable for equivality which returns true or false
