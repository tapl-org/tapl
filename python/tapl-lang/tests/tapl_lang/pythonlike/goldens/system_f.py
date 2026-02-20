from tapl_lang.lib import tapl_dev
from tapl_lang.lib import builtin_types
Int = builtin_types.Int

def simple_id(a):
    return a
tapl_dev.log(simple_id(3))

def poly_id(A):

    def typed_id(a):
        return a
    return typed_id
id_int = poly_id(None)
id_str = poly_id(None)
tapl_dev.log(id_int(3))
tapl_dev.log(tapl_dev.describe(id_str))
tapl_dev.log(id_str('abc'))

def auto_id(a):

    def typed_id(b):
        return b
    return typed_id(a)
tapl_dev.log(auto_id('hello'))

def Slot(T):

    class Slot_:
        class_name = 'Slot({})'.format(T)

        def __init__(self, value):
            self._value = value

        def set(self, value):
            self._value = value

        def get(self):
            return self._value

        def __repr__(self):
            return 'Slot(' + str(self._value) + ')'
    return Slot_
slot = Slot(Int)(5)
tapl_dev.log(slot)
tapl_dev.log(slot.set)
