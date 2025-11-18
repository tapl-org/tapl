from tapl_lang.pythonlike.predef import *

def int_print(a):
    print(a)
    print_type(a)
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
print(b)
print_type(b)
