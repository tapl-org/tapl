from tapl_lang.pythonlike.predef import *
try:
    result = 10 / 0
except ZeroDivisionError:
    print('Cannot divide by zero')
finally:
    print('Execution completed')
