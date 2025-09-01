from tapl_lang.pythonlike.predef import *

def int_print(a):
    api__tapl.print_log(a)
int_print(123)

def zero():
    return 0

def increment(a):
    return a + 1
int_print(increment(zero()))
if True:
    int_print(456)
a = 5
if a == 2:
    b = 7
else:
    b = 'banana'
api__tapl.print_log(b)
