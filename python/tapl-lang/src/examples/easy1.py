from tapl_lang.pythonlike.predef1 import predef_scope as s0

class Dog_:

    def __init__(self, name):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, name=name)
        s1.self.name = s1.name
        return s1.tapl_typing.get_return_type(s1)

    def bark(self):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self)
        s1.tapl_typing.add_return_type(s1, s1.Str)
        return s1.tapl_typing.get_return_type(s1)
s0.Dog, s0.Dog_ = s0.tapl_typing.create_class(cls=Dog_, init_args=[s0.Str], methods=[('bark', [])])