<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *term*
&nbsp;| $d$ | *data*
&nbsp;| $c$ | *code*
&nbsp;| $\lambda!t_{lock}.t_{body}$ | *function*
&nbsp;| $t_{lock}{\to}t_{result}$ | *function type*
&nbsp;| $t{\ }t$ | *application*
&nbsp;| $t_{lock}{=}t_{key}$ | *unlocking*
&nbsp;| $t{:}t$ | *multi level term*
&nbsp;| $\epsilon.t$ | *flatten levels*

&nbsp;|&nbsp;|&nbsp;
---|---|--:
&nbsp;|**Handy single and multi level terms**| $t = g{\mid}h$
$g ::=$| $-\ \mid\ d\ \mid\ c\ \mid\ \lambda!g.g\ \mid\ g{\ }g\ \mid\ g{=}g\ \mid\ \epsilon.t$ | *single level*
$h ::=$| $\lambda!h.g\ \mid\ \lambda!t.h\ \mid\ h{\ }g\ \ \mid\ t{\ }h\ \mid\ h{=}g\ \mid\ t{=}h\ \mid\ t{:}t$ | *multi level*
&nbsp;|**Handy single level terms**| $g = v{\mid}r$
$v ::=$| $-\ \mid\ d\ \mid\ \lambda!v.g$ | *value*
$r ::=$| $c\ \mid\ \lambda!r{.}g\ \mid\ g{\ }g\ \mid\ g{=}g\ \mid\ \epsilon.t$ | *reducible*
&nbsp;|**Handy multi level terms**| $h=s{\mid}u$
$s ::=$| $g{:}g\ \mid\ g{:}s\ \mid\ s{:}g\ \mid\ s{:}s$ | *separated*
$u ::=$| $t{:}u\ \mid\ u{:}g\ \mid\ u{:}s\ \mid\ \lambda!h.g\ \mid\ \lambda!t.h\ \mid\ h{\ }g\ \ \mid\ t{\ }h\ \mid\ h{=}g\ \mid\ t{=}h$ | *separable*
$s' ::=$| $g\ \mid\ s$ | *single or seperated multi level*
$p ::=$| $v\ \mid\ p{:}p$ | *normal*
&nbsp;|**Notes**
$-$| dash as data means non-existant lock when used as lock term. 
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{=}(t)$
&nbsp;

$\psi[g]$| **Single Level Term Evaluation** |$\psi[g] \to g$
:-:|:-:|--:
&nbsp;|$\dfrac{\psi[v]}{v}$
&nbsp;|$\dfrac{\psi[c]}{v}$| *run the code*
&nbsp;|$\dfrac{\psi[\lambda!r{.}g]}{\lambda!\psi[r]{.}g}$
&nbsp;|$\dfrac{\psi[r{\ }g]}{\psi[r]{\ }g}$
&nbsp;|$\dfrac{\psi[v{\ }r]}{v{\ }\psi[r]}$ | *find a reason why waiting for argument is*<br>*required even a caller is not a function*
&nbsp;|$\dfrac{\psi[(-{\mid}d){\ }v]}{\text{error: not a function}}$
&nbsp;|$\dfrac{\psi[(\lambda!{-}.g){\ }v]}{[\lambda{\mapsto}{v}]\ g}$ | *apply*
&nbsp;|$e::=d\mid\lambda!v.g\quad\vdash\quad\dfrac{\psi[(\lambda!e_{lock}.t){\ }v_{key}]}{(\lambda!{-}.t)\ e_{lock}{=}v_{key}}$ | *unlock*
&nbsp;|$\dfrac{\psi[r{=}g]}{\psi[r]{=}g}$
&nbsp;|$\dfrac{\psi[v{=}r]}{v{=}\psi[r]}$
&nbsp;|$\dfrac{\psi[{-}{=}v_{key}]}{v_{key}}$ | *unlocked*
&nbsp;|$\dfrac{\psi[d{=}(\lambda!v.g)\ \mid\ (\lambda!v.g){=}{-}\ \mid\ (\lambda!v.g){=}d]}{\text{error: not in the same form}}$
&nbsp;|$\dfrac{\psi[d_{lock}{=}d_{key}]}{d_{key}\ \mid\ \text{error: not equal}}$ | $d_{key}$ *can be a stateful object,*<br>*and return it to enable substructural type*
&nbsp;|$\dfrac{\psi[(\lambda!v_1.g_1){=}(\lambda!v_2.g_2)]}{\lambda!(v_2{=}v_1).(g_1{=}g_2)}$ | *enclose function bodies to enable dependent type ???1*
&nbsp;|$\dfrac{\psi[\epsilon.u]}{\Sigma(\phi[u])}$
&nbsp;|$\dfrac{\psi[\epsilon.p_1{:}p_2]}{\epsilon.p_1}$
&nbsp;|$\dfrac{\psi[\epsilon.v]}{v}$
&nbsp;
$\phi[t]$| **Term Evaluation** |$\phi[t] \to t$
&nbsp;|$\dfrac{\phi[u]}{\sigma[u]}$
&nbsp;|$\dfrac{\phi[s'{:}p]}{\phi[s']{:}p}$
&nbsp;|$\dfrac{\phi[s'_1{:}s'_2]}{s'_1{:}\phi[{s'_2}]}$
&nbsp;|$\dfrac{\phi[g]}{\psi[g]}$
&nbsp;
$\sigma[t]$| **Term separation** |$\sigma[t] \to t$
&nbsp;|$\dfrac{\sigma[s']}{s'}$
&nbsp;|$\dfrac{\sigma[t{:}u]}{t{:}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[u{:}s']}{\sigma[u]{:}s'}$
&nbsp;|$\dfrac{\sigma[\lambda!(g_1{:}g_2).(s_1{:}s_2)]}{(g_1{.}s_1){:}(g_2{.}s_2)}$
&nbsp;|$\dfrac{\sigma[\lambda!h.g\ \mid\ \lambda!g.h]}{\text{error: different levels}}$
&nbsp;|$\dfrac{\sigma[\lambda!(g_1{:}g_2).(s_1{:}s_2)]}{(g_1{.}s_1){:}(g_2{.}s_2)}$
$e{\ }e$|$\dfrac{\sigma[u{\ }e]}{\sigma[u]{\ }e}$
&nbsp;|$\dfrac{\sigma[s{\ }u]}{s{\ }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{\ }s_1{:}s_2\ \mid\ s_1{:}s_2{\ }t]}{\text{error: not in the same level}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){\ }(s_3{:}s_4)]}{(s_1{\ }s_3){:}(s_2{\ }s_4)}$
$e{=}e$|$\dfrac{\sigma[u{=}e]}{\sigma[u]{=}e}$
&nbsp;|$\dfrac{\sigma[s{=}u]}{s{=}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{=}s_1{:}s_2\ \mid\ s_1{:}s_2{=}t]}{\text{error: not in the same level}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){=}(s_3{:}s_4)]}{(s_1{=}s_3){:}(s_2{=}s_4)}$


## Appendix
### In Python, argument is needed before checking whether the caller is function or not
```python
def get_function1():
    print('get_function1 called')
    def greeting(input):
        print('greeting called')
        print('Hello ' + input)
    return greeting

def get_function2():
    print('get_function2 called')
    return 'greeting'

def get_name():
    print("get_name called")
    return 'World'

get_function1()(get_name())
get_function2()(get_name())
```

Output
```text
get_function1 called
get_name called
greeting called
Hello World
get_function2 called
get_name called
Traceback (most recent call last):
  File "/Users/orti/projects/python/test2.py", line 17, in <module>
    get_function2()(get_name())
TypeError: 'str' object is not callable
```

### ???1 
During lock part of function to function unlocking, need to figure out what will be the result for substructural type.