from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)

def one():
    s1 = tapl_typing.create_scope(parent__sa=s0)
    s1.one = tapl_typing.create_function([], s1.Str)
    tapl_typing.set_return_type(s1, s1.Str)
    tapl_typing.add_return_type(s1, s1.Int)
    return tapl_typing.get_return_type(s1)
s0.one = tapl_typing.create_function([], one())
