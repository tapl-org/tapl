from tapl_lang.pythonlike.predef import *
x = 42
print_dual(x)
a = b = 'hello'
print_dual(a)
print_dual(b)
c = [1, 2, 3]
print_dual(c)
x = c[1]
print_dual(c[1])
c[2] = 42
del c[0]
print_dual(c)
dict_obj = {'key1': 'value1', 'key2': 'value2'}
print_dual(dict_obj)
value = dict_obj['key1']
print_dual(dict_obj['key1'])
dict_obj['key2'] = 'new_value2'
del dict_obj['key1']
print_dual(dict_obj)
