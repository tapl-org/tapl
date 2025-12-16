from tapl_lang.pythonlike.predef import *

def collatz_sequence(n):
    if n < 1:
        return []
    sequence = []
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        sequence.append(n)
    return sequence
print(collatz_sequence(7))
print(collatz_sequence(19))
print(collatz_sequence(0))
tapl_dev.print(collatz_sequence(4))
