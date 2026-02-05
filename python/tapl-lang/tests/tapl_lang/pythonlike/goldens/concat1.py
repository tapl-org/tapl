from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)

class Vector_:

    def __init__(self, n):
        s1 = s0.tapl.typing.create_scope(parent__sa=s0, self=self, n=n)
        s1.self.n = s1.n
        return s1.tapl.typing.get_return_type(s1)

    def concat(self, m):
        s1 = s0.tapl.typing.create_scope(parent__sa=s0, self=self, m=m)
        s1.tapl.typing.add_return_type(s1, s1.Vector(s1.n + s1.m))
        return s1.tapl.typing.get_return_type(s1)
s0.Vector, s0.Vector_ = s0.tapl.typing.create_class(cls=Vector_, init_args=[s0.Int], methods=[('concat', [s0.Int])])
s0.print(s0.Str)