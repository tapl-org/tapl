from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)

def fibonacci(n):
    s1 = tapl_typing.create_scope(parent__sa=s0, n=n)
    s1.fibonacci = tapl_typing.create_function([s1.Int], s1.Int)
    tapl_typing.set_return_type(s1, s1.Int)
    with tapl_typing.scope_forker(s1) as f1:
        s2 = tapl_typing.fork_scope(f1)
        s2.n <= s2.Int
        tapl_typing.add_return_type(s2, s2.n)
        s2 = tapl_typing.fork_scope(f1)
        tapl_typing.add_return_type(s2, s2.fibonacci(s2.n - s2.Int) + s2.fibonacci(s2.n - s2.Int))
    return tapl_typing.get_return_type(s1)
s0.fibonacci = tapl_typing.create_function([s0.Int], fibonacci(s0.Int))
s0.tapl_dev.log(s0.fibonacci)
s0.print(s0.fibonacci(s0.Int))
s0.print(s0.fibonacci(s0.Int))
