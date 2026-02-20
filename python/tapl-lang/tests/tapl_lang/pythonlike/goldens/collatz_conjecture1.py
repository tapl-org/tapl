from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)

def collatz_sequence(n):
    s1 = tapl_typing.create_scope(parent__sa=s0, n=n)
    s1.sequence = s1.List(s1.Int)
    with tapl_typing.scope_forker(s1) as f1:
        s2 = tapl_typing.fork_scope(f1)
        s2.n < s2.Int
        tapl_typing.add_return_type(s2, s2.sequence)
        s2 = tapl_typing.fork_scope(f1)
    with tapl_typing.scope_forker(s1) as f1:
        s2 = tapl_typing.fork_scope(f1)
        s2.n != s2.Int
        with tapl_typing.scope_forker(s2) as f2:
            s3 = tapl_typing.fork_scope(f2)
            s3.n % s3.Int == s3.Int
            s3.n = s3.n // s3.Int
            s3 = tapl_typing.fork_scope(f2)
            s3.n = s3.Int * s3.n + s3.Int
        s2.sequence.append(s2.n)
        s2 = tapl_typing.fork_scope(f1)
    tapl_typing.add_return_type(s1, s1.sequence)
    return tapl_typing.get_return_type(s1)
s0.collatz_sequence = tapl_typing.create_function([s0.Int], collatz_sequence(s0.Int))
s0.tapl_dev.log(s0.tapl_dev.describe(s0.collatz_sequence))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.tapl_dev.log(s0.collatz_sequence(s0.Int))
