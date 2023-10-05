&nbsp;|**Syntax**|&nbsp;
---|---|---:
$e,E ::=$ || *expression:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *bits*
&nbsp;| $`\lambda x{:}E.\;t`$ | *abstraction*
&nbsp;| $`t \; t`$ | *application*
&nbsp;| $\tau[t]$ | *typeof*
&nbsp;| $![t]$ | *unsafe expression*
$t,T ::=$|| *term:*
&nbsp;| $e$ | *expression*
&nbsp;| $e{:}E$ | *typed expression*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

**Derived forms**|&nbsp;|&nbsp;
---|:---:|---:
$c,C$| $\lambda x{:}T.\;t \quad \|\text{FV}(\lambda x{:}T.\;t)\|{=}0$| closed abstraction
$d,D$| $b \mid c $|datum
$T_1{\to}T_2$| $\lambda x{:}T_1.\;T_2 \quad x\notin \text{FV}(T_2)$|type of function
$v,V$| $b \mid \lambda x{:}V.\;t$|value
$t_1;t_2$| $`(\lambda x{:}X.\;t_2) \; t_1 \quad \text{where } x \notin \text{FV}(t_2) \text{ and typeof}(t_1)\equiv X`$| sequence statements
$(t)$| $ t_1 (t_2 t_3) \equiv R=t_2 t_3; t_1 R $|grouping

**Bits encoding**|&nbsp;
---|---:
~[number]\^[string] | builtin function pointer: [number]=number of arguments, [string]=id
~[number] | number literal
~[string] | string literal
{~[number]\^[string] arg1 arg2 .. argn} | closure


&nbsp;|**Rules**|&nbsp;
--:|:---:|---:
2|$`\dfrac{t_1 \longrightarrow t_1'}{t_1 \; t_2 \longrightarrow t_1' \; t_2}`$ | *eval application 1*
3|$`\dfrac{t_2 \longrightarrow t_2'}{d_1 \; t_2 \longrightarrow d_1 \; t_2'}`$ | *eval application 2*
4|$`\dfrac{(c \equiv \lambda x{:}T_1.\;t)\;d{:}T_2 \qquad d}{[x\mapsto d]t}`$ | $\beta$*-reduction*
5|$`\dfrac{b \; d}{{\ll}\text{built-in call}{\gg}\;b(d)}`$ | $\delta$*-reduction*
8|$`\dfrac{x{:}T\in\Gamma\;\vdash\; \tau[x]}{T}`$ | *type variable*
9|$`\dfrac{\tau[\lambda x{:}T.\;t]}{\lambda x{:}T.\tau[t]}`$ | *type abstraction*
10|$`\dfrac{\tau[t_1 \; t_2]}{\tau[t_1]\; t_2}`$ | *type application*
10|$`\dfrac{![x]}{![\tau[x]]; x}`$ | *unsafe variable*
10|$`\dfrac{![b]}{b}`$ | *unsafe variable*
10|$`\dfrac{![b]}{b}`$ | *unsafe bits*
10|$`\dfrac{![\lambda x{:}E.\;t]}{\lambda x{:}E.\;t}`$ | *unsafe abstraction*
10|$`\dfrac{![(\lambda a{:}A.\;b{:}B)\;y{:}Y]}{(\sim2\text{:termEqual A Y});\;![[a->y]B];\;((\lambda a{:}A.\;b{:}B)\;y{:}Y)}`$ | *unsafe abstraction*

&nbsp;

(~2^termEqual A Y); !([a->y]B); ((\a:A.b:B) y:Y)




Comments:
* `resultType` is a builtin function which checks parameter and argument types and extracts result type from application
* `atom` represents a zero size imaginary bits
* type of `atom` is `atom`
* two `bits` are equal if they have the same bits in the same order

Note: Any datum can be comparable for equivality which returns true or false
