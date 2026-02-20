from tapl_lang.pythonlike.predef import *
from tapl_lang.lib import tapl_dev

def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
print(fibonacci(3))
print(fibonacci(4))
