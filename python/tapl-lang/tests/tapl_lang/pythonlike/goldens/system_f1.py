from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)

def simple_id(a):
    s1 = tapl_typing.create_scope(parent__sa=s0, a=a)
    tapl_typing.add_return_type(s1, s1.a)
    return tapl_typing.get_return_type(s1)
s0.simple_id = simple_id
s0.tapl_dev.log(s0.simple_id(s0.Int))

def poly_id(A):
    s1 = tapl_typing.create_scope(parent__sa=s0, A=A)

    def typed_id(a):
        s2 = tapl_typing.create_scope(parent__sa=s1, a=a)
        tapl_typing.add_return_type(s2, s2.a)
        return tapl_typing.get_return_type(s2)
    s1.typed_id = tapl_typing.create_function([s1.A], typed_id(s1.A))
    tapl_typing.add_return_type(s1, s1.typed_id)
    return tapl_typing.get_return_type(s1)
s0.poly_id = poly_id
s0.id_int = s0.poly_id(s0.Int)
s0.id_str = s0.poly_id(s0.Str)
s0.tapl_dev.log(s0.id_int(s0.Int))
s0.tapl_dev.log(s0.tapl_dev.describe(s0.id_str))
s0.tapl_dev.log(s0.id_str(s0.Str))

def auto_id(a):
    s1 = tapl_typing.create_scope(parent__sa=s0, a=a)

    def typed_id(b):
        s2 = tapl_typing.create_scope(parent__sa=s1, b=b)
        tapl_typing.add_return_type(s2, s2.b)
        return tapl_typing.get_return_type(s2)
    s1.typed_id = tapl_typing.create_function([s1.a], typed_id(s1.a))
    tapl_typing.add_return_type(s1, s1.typed_id(s1.a))
    return tapl_typing.get_return_type(s1)
s0.auto_id = auto_id
s0.tapl_dev.log(s0.auto_id(s0.Str))

def Slot(T):
    s1 = tapl_typing.create_scope(parent__sa=s0, T=T)

    class Slot_:
        class_name = 'Slot({})'.format(s1.T)

        def __init__(self, value):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self, value=value)
            s2.self._value = s2.value
            return tapl_typing.get_return_type(s2)

        def set(self, value):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self, value=value)
            s2.self._value = s2.value
            return tapl_typing.get_return_type(s2)

        def get(self):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self)
            tapl_typing.add_return_type(s2, s2.self._value)
            return tapl_typing.get_return_type(s2)

        def __repr__(self):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self)
            tapl_typing.add_return_type(s2, s2.Str + s2.str(s2.self._value) + s2.Str)
            return tapl_typing.get_return_type(s2)
    s1.Slot_ = tapl_typing.create_class(cls=Slot_, init_args=[s1.T], methods=[('set', [s1.T]), ('get', []), ('__repr__', [])])
    tapl_typing.add_return_type(s1, s1.Slot_)
    return tapl_typing.get_return_type(s1)
s0.Slot = Slot
s0.slot = s0.Slot(s0.Int)(s0.Int)
s0.tapl_dev.log(s0.slot)
s0.tapl_dev.log(s0.slot.set)
