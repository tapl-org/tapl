from tapl_lang.pythonlike.predef1 import predef_scope as s0

def int_print(a):
    s1 = s0.api__tapl.create_scope(parent__tapl=s0, a=a)
    s1.api__tapl.print_log(s1.a)
    return s1.api__tapl.get_return_type(s1)
s0.int_print = s0.api__tapl.create_function([s0.Int], int_print(s0.Int))
s0.int_print(s0.Int)

def zero():
    s1 = s0.api__tapl.create_scope(parent__tapl=s0)
    s1.api__tapl.set_return_type(s1, s1.Int)
    s1.api__tapl.add_return_type(s1, s1.Int)
    return s1.api__tapl.get_return_type(s1)
s0.zero = s0.api__tapl.create_function([], zero())

def increment(a):
    s1 = s0.api__tapl.create_scope(parent__tapl=s0, a=a)
    s1.api__tapl.add_return_type(s1, s1.a + s1.Int)
    return s1.api__tapl.get_return_type(s1)
s0.increment = s0.api__tapl.create_function([s0.Int], increment(s0.Int))
s0.int_print(s0.increment(s0.zero()))
with s0.api__tapl.scope_forker(s0) as f0:
    s1 = s0.api__tapl.fork_scope(f0)
    s1.Bool
    s1.int_print(s1.Int)
    s1 = s0.api__tapl.fork_scope(f0)
s0.a = s0.Int
with s0.api__tapl.scope_forker(s0) as f0:
    s1 = s0.api__tapl.fork_scope(f0)
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = s0.api__tapl.fork_scope(f0)
    s1.b = s1.Str
s0.api__tapl.print_log(s0.b)
