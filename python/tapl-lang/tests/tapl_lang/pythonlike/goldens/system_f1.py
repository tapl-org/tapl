from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def simple_id(a):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, a=a)
    s1.tapl_typing.add_return_type(s1, s1.a)
    return s1.tapl_typing.get_return_type(s1)
s0.simple_id = simple_id
s0.tapl.print(s0.simple_id(s0.Int))

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
s0.id_int = s0.poly_id(s0.Int)
s0.id_str = s0.poly_id(s0.Str)
s0.tapl.print(s0.id_int(s0.Int))
s0.tapl.print(s0.tapl.to_string(s0.id_str))
s0.tapl.print(s0.id_str(s0.Str))

def auto_id(a):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, a=a)

    def typed_id(b):
        s2 = s1.tapl_typing.create_scope(parent__sa=s1, b=b)
        s2.tapl_typing.add_return_type(s2, s2.b)
        return s2.tapl_typing.get_return_type(s2)
    s1.typed_id = s1.tapl_typing.create_function([s1.a], typed_id(s1.a))
    s1.tapl_typing.add_return_type(s1, s1.typed_id(s1.a))
    return s1.tapl_typing.get_return_type(s1)
s0.auto_id = auto_id
s0.tapl.print(s0.auto_id(s0.Str))

def Slot(T):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, T=T)

    class Slot_:
        class_name = 'Slot({})'.format(s1.T)

        def __init__(self, value):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self, value=value)
            s2.self._value = s2.value
            return s2.tapl_typing.get_return_type(s2)

        def set(self, value):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self, value=value)
            s2.self._value = s2.value
            return s2.tapl_typing.get_return_type(s2)

        def get(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.tapl_typing.add_return_type(s2, s2.self._value)
            return s2.tapl_typing.get_return_type(s2)

        def __repr__(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.tapl_typing.add_return_type(s2, s2.Str + s2.str(s2.self._value) + s2.Str)
            return s2.tapl_typing.get_return_type(s2)
    s1.Slot_ = s1.tapl_typing.create_class(cls=Slot_, init_args=[s1.T], methods=[('set', [s1.T]), ('get', []), ('__repr__', [])])
    s1.tapl_typing.add_return_type(s1, s1.Slot_)
    return s1.tapl_typing.get_return_type(s1)
s0.Slot = Slot
s0.slot = s0.Slot(s0.Int)(s0.Int)
s0.tapl.print(s0.slot)
s0.tapl.print(s0.slot.set)
