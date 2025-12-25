from tapl_lang.pythonlike.predef import *

def simple_id(a):
    return a
tapl_dev.print(simple_id(3))

def poly_id(A):

    def typed_id(a):
        return a
    return typed_id
idInt = poly_id(None)
idStr = poly_id(None)
tapl_dev.print(idInt(3))
tapl_dev.print(tapl_dev.to_string(idStr))
tapl_dev.print(idStr('abc'))
