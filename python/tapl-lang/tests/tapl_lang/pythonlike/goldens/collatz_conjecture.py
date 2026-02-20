from tapl_lang.lib import tapl_dev

def collatz_sequence(n):
    sequence = []
    if n < 1:
        return sequence
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        sequence.append(n)
    return sequence
tapl_dev.log(tapl_dev.describe(collatz_sequence))
print(collatz_sequence(7))
print(collatz_sequence(19))
print(collatz_sequence(0))
tapl_dev.log(collatz_sequence(4))
