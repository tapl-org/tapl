from tapl_lang.pythonlike import predef1 as predef
scope0 = predef.Scope(predef.predef_scope)
scope0.int_print(scope0.Int)

def zero():
    scope1 = predef.Scope(scope0)
    return scope1.Int
scope0.zero = predef.FunctionType([], zero())

def increment(a):
    scope1 = predef.Scope(scope0, a=a)
    return scope1.a + scope1.Int
scope0.increment = predef.FunctionType([scope0.Int], increment(scope0.Int))
scope0.int_print(scope0.increment(scope0.zero()))
scope0.Bool
scope0.int_print(scope0.Int)
