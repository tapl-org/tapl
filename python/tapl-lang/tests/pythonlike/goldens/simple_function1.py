from tapl_lang.pythonlike import predef1 as predef
s0 = predef.create_scope_proxy(scope__tapl=predef.predef_scope)

def int_print(a):
    s1 = predef.create_scope_proxy(s0, a=a)
    s1.print__tapl(s1.a)
    return predef.get_return_type(s1)
s0.int_print = predef.FunctionType([s0.Int], int_print(s0.Int))
s0.int_print(s0.Int)

def zero():
    s1 = predef.create_scope_proxy(s0)
    predef.add_return_type(s1, s1.Int)
    return predef.get_return_type(s1)
s0.zero = predef.FunctionType([], zero())

def increment(a):
    s1 = predef.create_scope_proxy(s0, a=a)
    predef.add_return_type(s1, s1.a + s1.Int)
    return predef.get_return_type(s1)
s0.increment = predef.FunctionType([s0.Int], increment(s0.Int))
s0.int_print(s0.increment(s0.zero()))
with predef.scope_forker(s0) as f0:
    s1 = f0.new_scope()
    s1.Bool
    s1.int_print(s1.Int)
    s1 = f0.new_scope()
s0.a = s0.Int
with predef.scope_forker(s0) as f0:
    s1 = f0.new_scope()
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = f0.new_scope()
    s1.b = s1.Str
s0.print__tapl(s0.b)
