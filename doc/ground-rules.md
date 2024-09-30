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
&nbsp;| $t\text{ as }k$ | *rearrage layers*
&nbsp;| $t{:}t$ | *multi layer term*
$path ::=$ || *path*
&nbsp;| $\text{low}$ | *low layer*
&nbsp;| $\text{high}$ | *high layer*
&nbsp;| $path/path$ | *nested path*
&nbsp;| $\epsilon.k$ | *flatten layers*
$k ::=$ || *rearrange*
&nbsp;| $path$ | *path*
&nbsp;| $k{:}k$ | *multi layer paths*

&nbsp;|&nbsp;|&nbsp;
---|---|--:
&nbsp;|**Handy single and multi layer terms**| $t = g{\mid}h$
$g ::=$| $-\ \mid\ d\ \mid\ c\ \mid\ \lambda!g.g\ \mid\ g{\to}g\ \mid\ g{\ }g\ \mid\ g{=}g\ \mid\ \text{raise }g\ \mid\ \text{try }g\text{ with }g\ \mid\ t\text{ as }path$ | *single layer*
$h' ::=$| $\lambda!h.g\ \mid\ h{\to}g\ \mid\ h{\ }g\ \mid\ h{=}g\ \mid\ \text{raise }h\ \mid\ \text{try }h\text{ with }g$ |
&nbsp; | $\lambda!t.h\ \mid\ t{\to}h\ \mid\ t{\ }h\ \mid\ t{=}h\ \mid\ \text{try }t\text{ with }h\ \mid\ t\text{ as }k{:}k$ | *aux multi layer*
$h ::=$| $t{:}t\ \mid\ h'$ | *multi layer*
&nbsp;|**Handy single layer terms**| $g = n{\mid}r$
$v ::=$| $-\ \mid\ d\ \mid\ \lambda!{-}.g\ \mid\ v{\to}v$ | *value*
$n ::=$| $v\ \mid\ \text{raise }v$ | *normal*
$r ::=$| $c\ \mid\ \lambda!\{n\backslash{-}\}{.}g\ \mid\ \lambda!r{.}g\ \mid\ v{\to}\text{raise }v\ \mid\ v{\to}r\ \mid\ \text{raise }v{\to}g\ \mid\ r{\to}g$ |
&nbsp;| $g{\ }g\ \mid\ g{=}g\ \mid\ \text{raise }(\text{raise }v)\ \mid\ \text{raise }r\ \mid\ \text{try }g\text{ with }g\ \mid\ t\text{ as }path$ | *reducible*
&nbsp;|**Handy multi layer terms**| $h=s{\mid}u$
$s ::=$| $g{:}g\ \mid\ g{:}s\ \mid\ s{:}g\ \mid\ s{:}s$ | *separated*
$u ::=$| $t{:}u\ \mid\ u{:}g\ \mid\ u{:}s\ \mid\ h'$ | *separable*
$s' ::=$| $g\ \mid\ s$ | *single or seperated multi layer*
$p ::=$| $n\ \mid\ p{:}p$ | *normal*
&nbsp;|**Notes**
$\dfrac{a}{a'}$| $a$ evaluates to $a'$ in one step.
$()$| groupping: $t{\equiv}(t)$
&nbsp;| $\lambda!t{.}t{\equiv}\lambda{x}!t{.}t$ - $x$ is always present, but might be omitted for simplicity.
&nbsp;| $\lambda\_!t_1{.}t_2{\equiv}\lambda{x}!t_1{.}t_2$ where $x$ is a free variable in $t_2$. $x\notin FV(t_2)$
&nbsp;

$\psi[g]$| **Single layer Term Evaluation** |$\psi[g] \to g$
:-:|:-:|--:
$-$|$\dfrac{\psi[-]}{-}$ | *absence*
$d$|$\dfrac{\psi[d]}{d}$ | *data*
$c$|$\dfrac{\psi[c]}{n}$| *run the code*
$\lambda!g{.}g$|$\lambda!{-}.g\ \mid\ \lambda!\{v\backslash{-}\}.g\ \mid\ \lambda!(\text{raise }v).g\ \mid\ \lambda!r{.}g$ | *function*
&nbsp;|$\dfrac{\psi[\lambda!{-}.g]}{\lambda!{-}.g}$
&nbsp;|$e::=\{v\backslash{-}\}\quad\vdash\quad\dfrac{\psi[\lambda!e{.}g]}{e{\to}\psi[(\lambda!{-}.g)\ e]}$
&nbsp;|$\dfrac{\psi[\lambda!(\text{raise }v){.}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[\lambda!r{.}g]}{\lambda!\psi[r]{.}g}$
$g{\to}g$|$v{\to}v\ \mid\ v{\to}\text{raise }v\ \mid\ v{\to}r\ \mid\ \text{raise }v{\to}g\ \mid\ r{\to}g$ | *function type*
&nbsp;|$\dfrac{\psi[v_1{\to}v_2]}{v_1{\to}v_2}$
&nbsp;|$\dfrac{\psi[v_1{\to}\text{raise }v_2]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{\to}r]}{v{\to}\psi[r]}$
&nbsp;|$\dfrac{\psi[\text{raise }v{\to}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{\to}g]}{\psi[r]{\to}g}$
$g{\ }g$|$\{-{,}d\}{\ }v\ \mid\ (\lambda!{-}.g){\ }v\ \mid\ (v{\to}v){\ }v\ \mid\ v{\ }(\text{raise }v)\ \mid\ v{\ }r\ \mid\ (\text{raise }v){\ }g\ \mid\ r{\ }g$ | *application*
&nbsp;|$\dfrac{\psi[\{-{,}d\}{\ }v]}{\text{raise "Expected a callable"}}$ | *Appendix A*
&nbsp;|$\dfrac{\psi[(\lambda{x}!{-}.g){\ }v]}{[x{\mapsto}{v}]\ g}$ | *apply*
&nbsp;|$\dfrac{\psi[(v_1{\to}v_2){\ }v_3]}{(\lambda\_!{-}.v_2){\ }\psi[v_1{=}v_3]}$
&nbsp;|$\dfrac{\psi[v_1{\ }(\text{raise }v_2)]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{\ }r]}{v{\ }\psi[r]}$
&nbsp;|$\dfrac{\psi[(\text{raise }v){\ }g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{\ }g]}{\psi[r]{\ }g}$
$g{=}g$|$v{=}v\ \mid\ v{=}\text{raise }v\ \mid\ v{=}r\ \mid\ \text{raise }v{=}g\ \mid\ r{=}g$ | *unlocking*
&nbsp;|$\dfrac{\psi[v_1{=}\text{raise }v_2]}{\text{raise }v_2}$
&nbsp;|$\dfrac{\psi[v{=}r]}{v{=}\psi[r]}$
&nbsp;|$\dfrac{\psi[\text{raise }v{=}g]}{\text{raise }v}$
&nbsp;|$\dfrac{\psi[r{=}g]}{\psi[r]{=}g}$
$v{=}v$|$\{\{e\}{=}\{v\backslash{e}\}:e\in v\}\ \mid\ {-}{=}{-}\ \mid\ d{=}d\ \mid\ (\lambda!{-}.g){=}(\lambda!{-}.g)\ \mid\ (v{\to}v){=}(v{\to}v)$ | *equivalence*
&nbsp;|$\dfrac{\psi[\{\{e\}{=}\{v\backslash{e}\}:e\in v\}]}{\text{raise "Not in the same form"}}$
&nbsp;|$\dfrac{\psi[{-}{=}v_{key}]}{v_{key}}$ | *unlocked*
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
&nbsp;|$\dfrac{\sigma[\lambda!h.g\ \mid\ \lambda!g.h]}{\text{error: different layers}}$
&nbsp;|$\dfrac{\sigma[\lambda!(g_1{:}g_2).(s_1{:}s_2)]}{(g_1{.}s_1){:}(g_2{.}s_2)}$
$e{\ }e$|$\dfrac{\sigma[u{\ }e]}{\sigma[u]{\ }e}$
&nbsp;|$\dfrac{\sigma[s{\ }u]}{s{\ }\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{\ }s_1{:}s_2\ \mid\ s_1{:}s_2{\ }t]}{\text{error: not in the same layer}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){\ }(s_3{:}s_4)]}{(s_1{\ }s_3){:}(s_2{\ }s_4)}$
$e{=}e$|$\dfrac{\sigma[u{=}e]}{\sigma[u]{=}e}$
&nbsp;|$\dfrac{\sigma[s{=}u]}{s{=}\sigma[u]}$
&nbsp;|$\dfrac{\sigma[t{=}s_1{:}s_2\ \mid\ s_1{:}s_2{=}t]}{\text{error: not in the same layer}}$
&nbsp;|$\dfrac{\sigma[(s_1{:}s_2){=}(s_3{:}s_4)]}{(s_1{=}s_3){:}(s_2{=}s_4)}$


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