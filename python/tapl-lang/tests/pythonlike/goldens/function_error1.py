from tapl_lang.pythonlike.predef1 import predef_proxy as s0

def one():
    s1 = s0.api__tapl.create_scope(parent__tapl=s0)
    s1.api__tapl.set_return_type(s1, s1.Str)
    s1.api__tapl.add_return_type(s1, s1.Int)
    return s1.api__tapl.get_return_type(s1)
s0.one = s0.api__tapl.create_function([], one())
