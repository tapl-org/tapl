<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Syntax

&nbsp;|**Syntax**|&nbsp;
---|---|---:
$t ::=$ || *term*
&nbsp;| $-$ | *absence*
&nbsp;| $d$ | *data*
&nbsp;| $c$ | *code*
&nbsp;| $\lambda{x}!t_{lock}{.}t_{body}$ | *function*
&nbsp;| $t_{lock}{\to}t_{result}$ | *function type*
&nbsp;| $t_{fun}{\ }t_{arg}$ | *application*
&nbsp;| $t_{lock}{=}t_{key}$ | *unlocking*
&nbsp;| $\text{raise }t$ | *raise exception*
&nbsp;| $\text{try }t_{body}\text{ with }t_{catch}$ | *handle exception*
&nbsp;| $t{:}t$ | *multi layer term*
&nbsp;| $\epsilon.t$ | *flatten layers*
&nbsp;| $t\text{ as }k$ | *rearrage layers*
$path ::=$ || *path*
&nbsp;| $\text{is}$ | *keep it as is*
&nbsp;| $\langle \text{low,high}\rangle/path$ | *nested path*
$k ::=$ || *rearrange*
&nbsp;| $path$ | *path*
&nbsp;| $k{:}k$ | *multi layer*
&nbsp;| $\epsilon.k$ | *flatten layers*

&nbsp;|&nbsp;|&nbsp;
---|---|--:
&nbsp;|**Notes**
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step, or forward the evaluation.
$()$| groupping: $t{\equiv}(t)$
$\langle\rangle$| set
$\text{true}$| just an instance of data $d$
&nbsp;| $\lambda!t{.}t{\equiv}\lambda{x}!t{.}t\qquad$ $x$ is always present, but might be omitted for simplicity.
&nbsp;| $\lambda\bot!t_1{.}t_2{\equiv}\lambda{x}!t_1{.}t_2\qquad$ where $x$ is a free variable in $t_2$. $x\notin FV(t_2)$
&nbsp;| vscode shows the formulas in a pretty format
&nbsp;
&nbsp;|**Handy single and multi layer terms**| $t = g{\mid}h$
$g ::=$| $-\ \mid\ d\ \mid\ c\ \mid\ \lambda!g.g\ \mid\ g{\to}g\ \mid\ g{\ }g\ \mid\ g{=}g\ \mid\ \text{raise }g\ \mid\ \text{try }g\text{ with }g$ | *single layer*
$h' ::=$| $\lambda!h.g\ \mid\ h{\to}g\ \mid\ h{\ }g\ \mid\ h{=}g\ \mid\ \text{raise }h\ \mid\ \text{try }h\text{ with }g$ |
&nbsp; | $\lambda!t.h\ \mid\ t{\to}h\ \mid\ t{\ }h\ \mid\ t{=}h\ \mid\ \text{try }t\text{ with }h\ \mid\ t\text{ as }k\ \mid\ \epsilon.t$ | *aux multi layer*
$h ::=$| $t{:}t\ \mid\ h'$ | *multi layer*
&nbsp;|**Handy single layer terms**| $g = n{\mid}r$
$v ::=$| $-\ \mid\ d\ \mid\ \lambda!{-}.g\ \mid\ v{\to}v$ | *value*
$n ::=$| $v\ \mid\ \text{raise }v$ | *normal*
$r ::=$| $c\ \mid\ \lambda!\langle n\backslash{-}\rangle{.}g\ \mid\ \lambda!r{.}g\ \mid\ v{\to}\text{raise }v\ \mid\ v{\to}r\ \mid\ \text{raise }v{\to}g\ \mid\ r{\to}g$ |
&nbsp;| $g{\ }g\ \mid\ g{=}g\ \mid\ \text{raise }(\text{raise }v)\ \mid\ \text{raise }r\ \mid\ \text{try }g\text{ with }g$ | *reducible*
&nbsp;|**Handy multi layer terms**| $h=s{\mid}u$
$s ::=$| $g{:}g\ \mid\ g{:}s\ \mid\ s{:}g\ \mid\ s{:}s$ | *separated*
$u ::=$| $t{:}u\ \mid\ u{:}g\ \mid\ u{:}s\ \mid\ h'$ | *separable*
$s' ::=$| $g\ \mid\ s$ | *single or seperated multi layer*
&nbsp;

$\psi[g]$| **Single layer Term Evaluation** |$\psi[g] \to g$
:-:|:-:|--:
$-$|$\dfrac{\psi[-]}{-}$ | *absence*
$d$|$\dfrac{\psi[d]}{d}$ | *data*
$c$|$\dfrac{\psi[c]}{n}$| *run the code*
$\lambda!g{.}g$|$\lambda!{-}.g\ \mid\ \lambda!\langle v\backslash{-}\rangle.g\ \mid\ \lambda!(\text{raise }v).g\ \mid\ \lambda!r{.}g$ | *function*
&nbsp;|$\dfrac{\psi[\lambda!{-}.g]}{\lambda!{-}.g}$
&nbsp;|$e::=\langle v\backslash{-}\rangle\quad\vdash\quad\dfrac{\psi[\lambda!e{.}g]}{e{\to}((\lambda!{-}.g)\ e)}$
&nbsp;|$\dfrac{\psi[\lambda!(\text{raise }v){.}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[\lambda!r{.}g]}{\lambda!\psi[r]{.}g}$
$g{\to}g$|$v{\to}v\ \mid\ v{\to}\text{raise }v\ \mid\ v{\to}r\ \mid\ \text{raise }v{\to}g\ \mid\ r{\to}g$ | *function type*
&nbsp;|$\dfrac{\psi[v_1{\to}v_2]}{v_1{\to}v_2}$
&nbsp;|$\dfrac{\psi[v_1{\to}\text{raise }v_2]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{\to}r]}{v{\to}\psi[r]}$
&nbsp;|$\dfrac{\psi[\text{raise }v{\to}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{\to}g]}{\psi[r]{\to}g}$
$g\ g$|$v{\ }v\ \mid\ v{\ }(\text{raise }v)\ \mid\ v{\ }r\ \mid\ (\text{raise }v){\ }g\ \mid\ r{\ }g$ | *application*
$v\ v$|$\langle -,d\rangle\ v\ \mid\ (\lambda!{-}.g){\ }v\ \mid\ (v{\to}v){\ }v$
&nbsp;|$\dfrac{\psi[\langle -,d\rangle{\ }v]}{\text{raise "Expected a callable"}}$ | *Appendix A*
&nbsp;|$\dfrac{\psi[(\lambda{x}!{-}.g){\ }v]}{[x{\mapsto}{v}]\ g}$ | *apply*
&nbsp;|$\dfrac{\psi[(v_1{\to}v_2){\ }v_3]}{(\lambda\bot!{-}.v_2){\ }(v_1{=}v_3)}$
&nbsp;|$\dfrac{\psi[v_1{\ }(\text{raise }v_2)]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{\ }r]}{v{\ }\psi[r]}$
&nbsp;|$\dfrac{\psi[(\text{raise }v){\ }g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{\ }g]}{\psi[r]{\ }g}$
$g{=}g$|$v{=}v\ \mid\ v{=}(\text{raise }v)\ \mid\ v{=}r\ \mid\ (\text{raise }v){=}g\ \mid\ r{=}g$ | *unlocking*
$v{=}v$|$\langle e_1{=}e_2: e_1,e_2\in v\text{ and }e_1{\not\equiv}e_2\rangle\ \mid\ {-}{=}{-}\ \mid\ d{=}d\ \mid\ (\lambda!{-}.g){=}(\lambda!{-}.g)\ \mid\ (v{\to}v){=}(v{\to}v)$
&nbsp;|$\dfrac{\psi[\langle e_1{=}e_2: e_1,e_2\in v\text{ and }e_1{\not\equiv}e_2\rangle]}{\text{raise "Not in the same form"}}$
&nbsp;|$\dfrac{\psi[-{=}-]}{\text{true}}$
&nbsp;|$\dfrac{\psi[d_{lock}{=}d_{key}]}{\text{true}\ \mid\ \text{raise "not equal"}}$
&nbsp;|$\dfrac{\psi[(\lambda!{-}.g_1){=}(\lambda!{-}.g_2)]}{\lambda!{-}.g_1{=}g_2}$ | *dependent type*
&nbsp;|$\dfrac{\psi[(v_1{\to}v_2){=}(v_3{\to}v_4)]}{(v_1{=}v_3){\to}(v_2{=}v_4)}$
&nbsp;|$\dfrac{\psi[v_1{=}(\text{raise }v_2)]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{=}r]}{v{=}\psi[r]}$
&nbsp;|$\dfrac{\psi[(\text{raise }v){=}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{=}g]}{\psi[r]{=}g}$
$\text{raise }g$|$\text{raise }v\ \mid\ \text{raise }(\text{raise }v)\mid\ \text{raise }r$ | *raise exception*
&nbsp;|$\dfrac{\psi[\text{raise }v]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[\text{raise }(\text{raise }v)]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[\text{raise }r]}{\text{raise }\psi[r]}$
$\text{try }g\text{ with }g$|$\text{try }v\text{ with }g\ \mid\ \text{try }(\text{raise }v)\text{ with }g\ \mid\ \text{try }r\text{ with }g$ | *handle exception*
&nbsp;|$\dfrac{\psi[\text{try }v\text{ with }g]}{v}$
&nbsp;|$\dfrac{\psi[\text{try }(\text{raise }v)\text{ with }g]}{g\ v}$
&nbsp;|$\dfrac{\psi[\text{try }r\text{ with }g]}{\text{try }\psi[r]\text{ with }g}$
&nbsp;
$\sigma[t]$| **Term separation** |$\sigma[t] \to t$
$\langle -,d,c\rangle$|$\dfrac{\sigma[-]}{-},\dfrac{\sigma[d]}{d},\dfrac{\sigma[c]}{c}$ | *absense, data, and code*
$\lambda!t.t$|$\lambda!u{.}t\ \mid\ \lambda!s'{.}u\ \mid\ \langle\lambda!g{.}s\ ,\ \lambda!s{.}g\rangle\ \mid\ \lambda!g{.}g\ \mid\ \lambda!s{.}s$ | *function*
&nbsp;|$\dfrac{\sigma[\lambda!u{.}t]}{\lambda!\sigma[u].t}$
&nbsp;|$\dfrac{\sigma[\lambda!s'{.}u]}{\lambda!s'.\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\langle\lambda!g{.}s\ ,\ \lambda!s{.}g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[\lambda!g_1{.}g_2]}{\lambda!g_1{.}g_2}$
&nbsp;|$\dfrac{\sigma[\lambda!(s'_1{:}s'_2){.}(s'_3{:}s'_4)]}{(\lambda!s'_1.s'_3){:}(\lambda!s'_2.s'_4)}$ | $\lambda!s{.}s$
$t{\to}t$|$u{\to}t\ \mid\ s'{\to}u\ \mid\ \langle g{\to}s\ ,\ s{\to}g\rangle\ \mid\ g{\to}g\ \mid\ s{\to}s$ | *function type*
&nbsp;|$\dfrac{\sigma[u{\to}t]}{\sigma[u]{\to}t}$
&nbsp;|$\dfrac{\sigma[s'{\to}u]}{s'{\to}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\langle g{\to}s\ ,\ s{\to}g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[g_1{\to}g_2]}{g_1{\to}g_2}$
&nbsp;|$\dfrac{\sigma[(s'_1{:}s'_2){\ }(s'_3{:}s'_4)]}{(s'_1{\ }s'_3){:}(s'_2{\ }s'_4)}$ | $s{\ }s$
$t{\ }t$|$u{\ }t\ \mid\ s'{\ }u\ \mid\ \langle g{\ }s\ ,\ s{\ }g\rangle\ \mid\ g{\ }g\ \mid\ s{\ }s$ | *application*
&nbsp;|$\dfrac{\sigma[u{\ }t]}{\sigma[u]{\ }t}$
&nbsp;|$\dfrac{\sigma[s'{\ }u]}{s'{\ }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\langle g{\ }s\ ,\ s{\ }g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[g_1{\ }g_2]}{g_1{\ }g_2}$
&nbsp;|$\dfrac{\sigma[(s'_1{:}s'_2){\ }(s'_3{:}s'_4)]}{(s'_1{\ }s'_3){:}(s'_2{\ }s'_4)}$ | $s{\ }s$
$t{=}t$|$u{=}t\ \mid\ s'{=}u\ \mid\ \langle g{=}s\ ,\ s{=}g\rangle\ \mid\ g{=}g\ \mid\ s{=}s$ | *unlocking*
&nbsp;|$\dfrac{\sigma[u{=}t]}{\sigma[u]{=}t}$
&nbsp;|$\dfrac{\sigma[s'{=}u]}{s'{=}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\langle g{=}s\ ,\ s{=}g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[g_1{=}g_2]}{g_1{=}g_2}$
&nbsp;|$\dfrac{\sigma[(s'_1{:}s'_2){=}(s'_3{:}s'_4)]}{(s'_1{=}s'_3){:}(s'_2{=}s'_4)}$ | $s{=}s$
$\text{raise }t$|$\text{raise u}\ \mid\ \text{raise }g\ \mid\ \text{raise }s$ | *raise exception*
&nbsp;|$\dfrac{\sigma[\text{raise }u]}{\text{raise }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\text{raise }g]}{\text{raise }g}$
&nbsp;|$\dfrac{\sigma[\text{raise }(s'_1{:}s'_2)]}{(\text{raise }s'_1):(\text{raise }s'_2)}$| $\text{raise }s$
$\text{try }t\text{ with }t$|$\text{try }u\text{ with }t\ \mid\ \text{try }s'\text{ with }u\ \mid\ \langle\text{try }g\text{ with }s , \text{try }s\text{ with }g\rangle\ \mid\ \text{try }g\text{ with }g\ \mid\ \text{try }s\text{ with }s$ | *handle exception*
&nbsp;|$\dfrac{\sigma[\text{try }u\text{ with }t]}{\text{try }\sigma[u]\text{ with }t}$
&nbsp;|$\dfrac{\sigma[\text{try }s'\text{ with }u]}{\text{try }s'\text{ with }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\langle\text{try }g\text{ with }s , \text{try }s\text{ with }g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[\text{try }g_1\text{ with }g_2]}{\text{try }g_1\text{ with }g_2}$
&nbsp;|$\dfrac{\sigma[\text{try }s'_1{:}s'_2\text{ with }s'_3{:}s'_4]}{(\text{try }s'_1\text{ with }s'_3){:}(\text{try }s'_2\text{ with }s'_4)}$ | $\text{try }s_1\text{ with }s_2$
$t{:}t$|$t{:}u\ \mid\ u{:}s'\ \mid\ \langle g{:}s\ ,\ s{:}g\rangle\ \mid\ g{:}g\ \mid\ s{:}s$ | *multi layer terms*
&nbsp;|$\dfrac{\sigma[t{:}u]}{t{:}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[u{:}s']}{\sigma[u]{:}s'}$
&nbsp;|$\dfrac{\sigma[\langle g{:}s\ ,\ s{:}g\rangle]}{\text{compile error: different layers}}$
&nbsp;|$\dfrac{\sigma[g_1{:}g_2]}{g_1{:}g_2}$
&nbsp;|$\dfrac{\sigma[(s'_1{:}s'_2){:}(s'_3{:}s'_4)]}{(s'_1{:}s'_3){:}(s'_2{:}s'_4)}$ | $s{:}s$
$\epsilon.t$|$\epsilon.u\ \mid\ \epsilon.g\ \mid\ \epsilon.s$ | *flatten layers*
&nbsp;|$\dfrac{\sigma[\epsilon.u]}{\epsilon.\sigma[u]}$
&nbsp;|$\dfrac{\sigma[\epsilon.g]}{g}$
&nbsp;|$\dfrac{\sigma[\epsilon.(s'_1{:}s'_2)]}{(\lambda\bot!{-}.\epsilon.s'_1)\ \epsilon.s'_2}$
$t\text{ as }k$|$u\text{ as }k\ \mid\ s'\text{ as }k{:}k\ \mid\ s'\text{ as }\epsilon.k\ \mid\ s'\text{ as is}\ \mid\ s'\text{ as }\langle\text{low,high}\rangle/path$ | *rearrange layers*
&nbsp;|$\dfrac{\sigma[u\text{ as }k]}{\sigma[u]\text{ as }k}$
&nbsp;|$\dfrac{\sigma[s'\text{ as }k_1{:}k_2]}{(s'\text{ as }k_1){:}(s'\text{ as }k_2)}$
&nbsp;|$\dfrac{\sigma[s'\text{ as }\epsilon.k]}{\epsilon.(s'\text{ as }k)}$
&nbsp;|$\dfrac{\sigma[s'\text{ as is}]}{s'}$
&nbsp;|$\dfrac{\sigma[g\text{ as }\langle\text{low,high}\rangle/path]}{\text{compile error: expected multi layer}}$
&nbsp;|$\dfrac{\sigma[s'_1{:}s'_2\text{ as }\text{low}/path]}{s'_1\text{ as }path}$
&nbsp;|$\dfrac{\sigma[s'_1{:}s'_2\text{ as }\text{high}/path]}{s'_2\text{ as }path}$
&nbsp;
$\phi[t]$| **Term Evaluation** |$\phi[t] \to t$
&nbsp;|$\dfrac{\phi[t]}{\psi[\sigma[\epsilon.t]]}$


## Appendix
### A: In Python, argument is needed before checking whether the caller is callable or not
I guess, to identify whether the caller side is a callable or not, it needs some extra logic. So python do not adds extra logic to do this, instead prepares the argument and calls the function with that argument. On the otherhand, when the caller side raises an error, then then interpretator knows about that the caller is not a callable, then justs escalates that error.
What if the caller is not a callable, but the argument evaluates to an error. Then the error should be re-raised, or new "Expected a function" error should be raised. I guess re-raise the argument error will be effective.
So the order: caller error, argument error, caller is a callable, and then application.
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