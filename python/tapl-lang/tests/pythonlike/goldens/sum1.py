from tapl_lang.pythonlike import predef1 as predef
from tapl_lang.core import api as api__tapl
s0 = api__tapl.ScopeProxy(predef.predef_scope)
s0.i = s0.Int
s0.print__tapl(s0.i)
