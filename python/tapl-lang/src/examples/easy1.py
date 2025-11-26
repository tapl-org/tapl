from tapl_lang.pythonlike.predef1 import predef_scope as s0

def factorial(n):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, n=n)
    s1.factorial = s1.tapl_typing.create_function([s1.Int], s1.Int)
    s1.tapl_typing.set_return_type(s1, s1.Int)
    with s1.tapl_typing.scope_forker(s1) as f1:
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.tapl_typing.create_union(s2.n == s2.Int, s2.n == s2.Int)
        s2.tapl_typing.add_return_type(s2, s2.Int)
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.tapl_typing.add_return_type(s2, s2.n * s2.factorial(s2.n - s2.Int))
    return s1.tapl_typing.get_return_type(s1)
s0.factorial = s0.tapl_typing.create_function([s0.Int], factorial(s0.Int))

class Dog_:

    def __init__(self, name):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, name=name)
        s1.self.name = s1.name
        return s1.tapl_typing.get_return_type(s1)

    def bark(self):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self)
        s1.bark = s1.tapl_typing.create_function([], s1.Str)
        s1.tapl_typing.set_return_type(s1, s1.Str)
        s1.tapl_typing.add_return_type(s1, s1.self.name + s1.Str)
        return s1.tapl_typing.get_return_type(s1)
s0.Dog, s0.Dog_ = s0.tapl_typing.create_class(cls=Dog_, init_args=[s0.Str], methods=[('bark', [])])