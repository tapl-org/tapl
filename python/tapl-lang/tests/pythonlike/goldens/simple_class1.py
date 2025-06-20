from tapl_lang.pythonlike import predef1 as predef
s0 = predef.Scope(predef.predef_scope)

class SimplestClass:
    pass
s0.SimplestClass = predef.Scope(parent=None, __call__=predef.init_class)

def accept(param):
    s1 = predef.Scope(s0, param=param)
    pass
    return predef.get_return_type(s1)
s0.accept = predef.FunctionType([s0.SimplestClass], accept(s0.SimplestClass))
s0.accept(s0.SimplestClass())
