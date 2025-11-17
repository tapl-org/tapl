from tapl_lang.pythonlike.predef1 import predef_scope as s0

def collatz_sequence(n):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, n=n)
    with s1.tapl_typing.scope_forker(s1) as f1:
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.n < s2.Int
        s2.tapl_typing.add_return_type(s2, s2.tapl_typing.create_typed_list())
        s2 = s1.tapl_typing.fork_scope(f1)
    s1.sequence = s1.tapl_typing.create_typed_list()
    with s1.tapl_typing.scope_forker(s1) as f1:
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.n != s2.Int
        with s2.tapl_typing.scope_forker(s2) as f2:
            s3 = s2.tapl_typing.fork_scope(f2)
            s3.n % s3.Int == s3.Int
            s3.n = s3.n // s3.Int
            s3 = s2.tapl_typing.fork_scope(f2)
            s3.n = s3.Int * s3.n + s3.Int
        s2.sequence.append(s2.n)
        s2 = s1.tapl_typing.fork_scope(f1)
    s1.tapl_typing.add_return_type(s1, s1.sequence)
    return s1.tapl_typing.get_return_type(s1)
s0.collatz_sequence = s0.tapl_typing.create_function([s0.Int], collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.tapl_typing.print_log(s0.collatz_sequence(s0.Int))
