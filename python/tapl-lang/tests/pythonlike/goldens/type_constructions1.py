from tapl_lang.pythonlike.predef1 import predef_scope as s0

def union_print(a):
    s1 = s0.tapl_typing.create_scope(parent__tapl=s0, a=a)
    s1.tapl_typing.print_log(s1.a)
    return s1.tapl_typing.get_return_type(s1)
s0.union_print = s0.tapl_typing.create_function([s0.Int], union_print(s0.Int))
s0.union_print(s0.Int)
