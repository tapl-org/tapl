from tapl_lang.pythonlike.predef1 import *
int_print(Int)

@function_type()
def zero():
    return Int

@function_type(Int)
def increment(a):
    return a + Int
