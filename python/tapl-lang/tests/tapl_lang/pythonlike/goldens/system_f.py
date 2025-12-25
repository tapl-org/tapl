from tapl_lang.pythonlike.predef import *

def id1(a):
    return a
tapl_dev.print(id1(3))

def id2(A):

    def id3(a):
        return a
    return id3
idInt = id2(Int)
idStr = id2(Str)
tapl_dev.print(idInt(3))
tapl_dev.print(idStr)
tapl_dev.print(idStr('abc'))
