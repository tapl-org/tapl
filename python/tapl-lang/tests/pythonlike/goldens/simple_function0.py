from tapl_lang.pythonlike.predef0 import *
int_print(123)

def zero():
    return 0

def increment(a):
    return a + 1
int_print(increment(zero()))
