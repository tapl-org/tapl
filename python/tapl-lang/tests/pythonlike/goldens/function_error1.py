from tapl_lang.pythonlike.predef1 import predef_scope as s0

def one():
    s1 = s0.tapl_typing.create_scope(parent__sa=s0)
    s1.tapl_typing.set_return_type(s1, s1.Str)
    s1.tapl_typing.add_return_type(s1, s1.Int)
    return s1.tapl_typing.get_return_type(s1)
s0.one = s0.tapl_typing.create_function([], one())
