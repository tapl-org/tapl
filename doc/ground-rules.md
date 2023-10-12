&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t,T ::=$ || *term:*
&nbsp;| $x$ | *variable*
&nbsp;| $b$ | *binary data*
&nbsp;| $`\{b \; {t_i}^{i\in1..n}\}`$ | *built-in function*
&nbsp;| $`\lambda x{:}T.\;e`$ | *abstraction*
&nbsp;| $`e \; e`$ | *application*
&nbsp;| $\tau[e]$ | *type of expression*
&nbsp;| $![e]$ | *safe expression*
&nbsp;| $\text{error}$ | *run-time error*
$e ::=$|| *expression:*
&nbsp;| $t$ | *term*
&nbsp;| $t{:}T$ | *typed term*
$\Gamma ::=$ || *context:*
&nbsp;| $\varnothing$ | *empty context*
&nbsp;| $\Gamma ,x{:}T$  | *variable binding*

**Derived forms**|&nbsp;|&nbsp;
---|:---:|---:
$(e)$| $`(e_1\;e_2)\;e_3\;\equiv\;e_1\;e_2\;e_3\;\not\equiv\;e_1\;(e_2\;e_3)`$|grouping
$d,D$| $b\;\mid\;\lambda x{:}T.\;e $|datum
$v,V$| $d\;\mid\;d{:}T$|value
$e_1;e_2$| $`(\lambda x{:}T.\;e_2) \; e_1 \quad \text{where } x \notin \text{FV}(e_2) \text{ and } \tau[e_1]\equiv T`$| sequencing notation
$T_1{\to}T_2$| $\lambda x{:}T_1.\;T_2 \quad x\notin \text{FV}(T_2)$|type of function
$c,C$| $\lambda x{:}T.\;e \quad \text{where }\|\text{FV}(\lambda x{:}T.\;e)\|{=}0$| closed abstraction


&nbsp;|**Evaluation rules**|&nbsp;
--:|:---:|---:
1|$`\dfrac{\{b \; {v_i}^{i\in1..n}\}}{{\ll}\text{built-in call}{\gg}}`$ | $\delta$*-reduction*
2|$`\dfrac{e_1 \longrightarrow e_1'}{e_1 \; e_2 \longrightarrow e_1' \; e_2}`$ | *application 1*
3|$`\dfrac{e_2 \longrightarrow e_2'}{v_1 \; e_2 \longrightarrow v_1 \; e_2'}`$ | *application 2*
4|$`\dfrac{(\lambda x{:}T.\;e)\;v}{[x\mapsto v]\;e}`$ | $\beta$*-reduction*
4|$`\dfrac{v_1\;v_2}{\text{error}}`$ | *error application*
5|$`\dfrac{x{:}T\in\Gamma\;\;\text{and}\;\; \tau[x]}{\Gamma\;\vdash\;T}`$ | *type variable*
8|$`\dfrac{\tau[b]}{\text{error}}`$ | *type binary*
6|$`\dfrac{\tau[\{b\;{t_i}^{i\in1..n}\}]}{\text{error}}`$ | *type built-in*
7|$`\dfrac{\tau[\lambda x{:}T.\;e]}{\lambda x{:}T.\tau[e]}`$ | *type abstraction*
8|$`\dfrac{\tau[e_1 \; e_2]}{\tau[e_1]\; e_2}`$ | *type application*
9|$`\dfrac{\tau[t{:}T]}{T}`$ | *type typed term*
11|$`\dfrac{![b]}{b}`$ | *safe binary data*
12|$`\dfrac{![\{b\;{t_i}^{i\in1..n}\}]}{\{b\;{t_i}^{i\in1..n}\}}`$ | *safe built-in*
14|$`\dfrac{![(\lambda x{:}T_1.\;e)\;v{:}T_2]}{\{\text{termEqual}\;T_1\;T_2\};\;![[x\to v]\tau[e]];\;(\lambda x{:}T_1.\;e)\;v{:}T_2}`$ | *safe application*
10|$`\dfrac{![e]}{![\tau[e]];\;e}`$ | *safe expression*

&nbsp;

(~2^termEqual A Y); !([a->y]B); ((\a:A.b:B) y:Y)




Comments:
* `resultType` is a builtin function which checks parameter and argument types and extracts result type from application
* `atom` represents a zero size imaginary bits
* type of `atom` is `atom`
* two `bits` are equal if they have the same bits in the same order

Note: Any datum can be comparable for equivality which returns true or false
