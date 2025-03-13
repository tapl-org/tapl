from tapl_lang.pythonlike.predef1 import *

def zero():
    return Int
zero = FunctionType(zero)

def increment(a):
    return a + Int
increment = FunctionType(increment, a=Int)
