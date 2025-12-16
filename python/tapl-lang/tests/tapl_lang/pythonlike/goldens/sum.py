from tapl_lang.pythonlike.predef import *
i = 100
sum = 0
while i > 0:
    sum = sum + i
    i = i - 1
print(sum)
sum = 0
for i in range(50):
    sum = sum + i
print(sum)
