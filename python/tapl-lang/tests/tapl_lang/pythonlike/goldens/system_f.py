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
