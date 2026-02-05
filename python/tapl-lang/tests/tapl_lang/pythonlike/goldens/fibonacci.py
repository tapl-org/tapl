from tapl_lang.pythonlike.predef import *

def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
tapl.print_type(fibonacci)
print(fibonacci(3))
print(fibonacci(4))
