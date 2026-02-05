from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)

def union_print(a):
    s1 = s0.tapl.typing.create_scope(parent__sa=s0, a=a)
    s1.tapl.print(s1.a)
    return s1.tapl.typing.get_return_type(s1)
s0.union_print = s0.tapl.typing.create_function([s0.Int | s0.Str], union_print(s0.Int | s0.Str))
s0.union_print(s0.Int)
s0.union_print(s0.Str)
