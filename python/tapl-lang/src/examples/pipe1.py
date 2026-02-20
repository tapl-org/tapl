from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)

def double(i):
    s1 = tapl_typing.create_scope(parent__sa=s0, i=i)
    s1.double = tapl_typing.create_function([s1.Int], s1.Int)
    tapl_typing.set_return_type(s1, s1.Int)
    tapl_typing.add_return_type(s1, s1.i * s1.Int)
    return tapl_typing.get_return_type(s1)
s0.double = tapl_typing.create_function([s0.Int], double(s0.Int))

def square(i):
    s1 = tapl_typing.create_scope(parent__sa=s0, i=i)
    s1.square = tapl_typing.create_function([s1.Int], s1.Int)
    tapl_typing.set_return_type(s1, s1.Int)
    tapl_typing.add_return_type(s1, s1.i * s1.i)
    return tapl_typing.get_return_type(s1)
s0.square = tapl_typing.create_function([s0.Int], square(s0.Int))
s0.print(s0.square(s0.double(s0.Int)))
s0.print(s0.double(s0.square(s0.Int)))