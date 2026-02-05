from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)

def fibonacci(n):
    s1 = s0.tapl.typing.create_scope(parent__sa=s0, n=n)
    s1.fibonacci = s1.tapl.typing.create_function([s1.Int], s1.Int)
    s1.tapl.typing.set_return_type(s1, s1.Int)
    with s1.tapl.typing.scope_forker(s1) as f1:
        s2 = s1.tapl.typing.fork_scope(f1)
        s2.n <= s2.Int
        s2.tapl.typing.add_return_type(s2, s2.n)
        s2 = s1.tapl.typing.fork_scope(f1)
        s2.tapl.typing.add_return_type(s2, s2.fibonacci(s2.n - s2.Int) + s2.fibonacci(s2.n - s2.Int))
    return s1.tapl.typing.get_return_type(s1)
s0.fibonacci = s0.tapl.typing.create_function([s0.Int], fibonacci(s0.Int))
s0.tapl.print_type(s0.fibonacci)
s0.print(s0.fibonacci(s0.Int))
s0.print(s0.fibonacci(s0.Int))
