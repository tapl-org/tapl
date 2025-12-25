from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def id1(a):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, a=a)
    s1.tapl_typing.add_return_type(s1, s1.a)
    return s1.tapl_typing.get_return_type(s1)
s0.id1 = id1
s0.tapl_dev.print(s0.id1(s0.Int))

def id2(A):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, A=A)

    def id3(a):
        s2 = s1.tapl_typing.create_scope(parent__sa=s1, a=a)
        s2.tapl_typing.add_return_type(s2, s2.a)
        return s2.tapl_typing.get_return_type(s2)
    s1.id3 = s1.tapl_typing.create_function([s1.A], id3(s1.A))
    s1.tapl_typing.add_return_type(s1, s1.id3)
    return s1.tapl_typing.get_return_type(s1)
s0.id2 = id2
s0.idInt = s0.id2(s0.Int)
s0.idStr = s0.id2(s0.Str)
s0.tapl_dev.print(s0.idInt(s0.Int))
s0.tapl_dev.print(s0.idStr)
s0.tapl_dev.print(s0.idStr(s0.Str))
