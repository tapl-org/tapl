from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def simple_id(a):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, a=a)
    s1.tapl_typing.add_return_type(s1, s1.a)
    return s1.tapl_typing.get_return_type(s1)
s0.simple_id = simple_id
s0.tapl_dev.print(s0.simple_id(s0.Int))

def poly_id(A):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, A=A)

    def typed_id(a):
        s2 = s1.tapl_typing.create_scope(parent__sa=s1, a=a)
        s2.tapl_typing.add_return_type(s2, s2.a)
        return s2.tapl_typing.get_return_type(s2)
    s1.typed_id = s1.tapl_typing.create_function([s1.A], typed_id(s1.A))
    s1.tapl_typing.add_return_type(s1, s1.typed_id)
    return s1.tapl_typing.get_return_type(s1)
s0.poly_id = poly_id
s0.idInt = s0.poly_id(s0.Int)
s0.idStr = s0.poly_id(s0.Str)
s0.tapl_dev.print(s0.idInt(s0.Int))
s0.tapl_dev.print(s0.tapl_dev.to_string(s0.idStr))
s0.tapl_dev.print(s0.idStr(s0.Str))
