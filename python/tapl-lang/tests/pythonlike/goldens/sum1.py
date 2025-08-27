from tapl_lang.lib import api as api__tapl
from tapl_lang.pythonlike import predef1 as predef
s0 = api__tapl.ScopeProxy(predef.predef_scope)
s0.i = s0.Int
s0.print__tapl(s0.i)
