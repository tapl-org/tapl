from tapl_lang.pythonlike import predef1 as predef
s0 = predef.Scope(predef.predef_scope)

class SimplestClass:
    pass
s0.SimplestClass = predef.Scope(label__tapl='SimplestClass')
s0.SimplestClass_ = predef.Scope(label__tapl='SimplestClass_')
s0.SimplestClass.__call__ = predef.FunctionType([s0.SimplestClass], s0.SimplestClass_)

def accept(param):
    s1 = predef.Scope(s0, param=param)
    pass
    return predef.get_return_type(s1)
s0.accept = predef.FunctionType([s0.SimplestClass_], accept(s0.SimplestClass_))
s0.accept(s0.SimplestClass())
