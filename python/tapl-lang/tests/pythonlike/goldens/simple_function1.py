from tapl_lang.pythonlike import predef1 as predef
from tapl_lang.lib import api as api__tapl
s0 = api__tapl.ScopeProxy(predef.predef_scope)

def int_print(a):
    s1 = api__tapl.create_scope(s0, a=a)
    s1.print__tapl(s1.a)
    return api__tapl.get_return_type(s1)
s0.int_print = predef.FunctionType([s0.Int], int_print(s0.Int))
s0.int_print(s0.Int)

def zero():
    s1 = api__tapl.create_scope(s0)
    api__tapl.add_return_type(s1, s1.Int)
    return api__tapl.get_return_type(s1)
s0.zero = predef.FunctionType([], zero())

def increment(a):
    s1 = api__tapl.create_scope(s0, a=a)
    api__tapl.add_return_type(s1, s1.a + s1.Int)
    return api__tapl.get_return_type(s1)
s0.increment = predef.FunctionType([s0.Int], increment(s0.Int))
s0.int_print(s0.increment(s0.zero()))
with api__tapl.scope_forker(s0) as f0:
    s1 = api__tapl.fork_scope(f0)
    s1.Bool
    s1.int_print(s1.Int)
    s1 = api__tapl.fork_scope(f0)
s0.a = s0.Int
with api__tapl.scope_forker(s0) as f0:
    s1 = api__tapl.fork_scope(f0)
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = api__tapl.fork_scope(f0)
    s1.b = s1.Str
s0.print__tapl(s0.b)
