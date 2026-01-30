from tapl_lang.pythonlike.predef import *

def simple_id(a):
    return a
tapl_dev.print(simple_id(3))

def poly_id(A):

    def typed_id(a):
        return a
    return typed_id
id_int = poly_id(None)
id_str = poly_id(None)
tapl_dev.print(id_int(3))
tapl_dev.print(tapl_dev.to_string(id_str))
tapl_dev.print(id_str('abc'))

def auto_id(a):

    def typed_id(b):
        return b
    return typed_id(a)
tapl_dev.print(auto_id('hello'))

def create_slot_class(T):

    class Slot:

        def __init__(self, value):
            self._value = value

        def set(self, value):
            self._value = value

        def get(self):
            return self._value

        def __repr__(self):
            return 'Slot(' + str(self._value) + ')'
    return Slot
slot = create_slot_class(Int)(5)
tapl_dev.print(slot)
tapl_dev.print(slot.set)
