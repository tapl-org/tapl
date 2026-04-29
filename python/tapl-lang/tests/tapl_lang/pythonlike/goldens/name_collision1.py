from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)

def s1():
    s1 = tapl_typing.create_scope(parent__sa=s0)
    s1.print(s1.Str)
    return tapl_typing.get_return_type(s1)
s0.s1 = tapl_typing.create_function([], s1())

def f1():
    s1 = tapl_typing.create_scope(parent__sa=s0)
    s1.print(s1.Str)
    return tapl_typing.get_return_type(s1)
s0.f1 = tapl_typing.create_function([], f1())

def s2():
    s1 = tapl_typing.create_scope(parent__sa=s0)
    s1.s1()
    with tapl_typing.scope_forker(s1) as f1:
        s2 = tapl_typing.fork_scope(f1)
        s2.Bool
        s2.f1()
        s2 = tapl_typing.fork_scope(f1)
    return tapl_typing.get_return_type(s1)
s0.s2 = tapl_typing.create_function([], s2())
s0.s2()
