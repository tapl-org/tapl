from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)

def collatz_sequence(n):
    s1 = s0.tapl.typing.create_scope(parent__sa=s0, n=n)
    s1.sequence = s1.List(s1.Int)
    with s1.tapl.typing.scope_forker(s1) as f1:
        s2 = s1.tapl.typing.fork_scope(f1)
        s2.n < s2.Int
        s2.tapl.typing.add_return_type(s2, s2.sequence)
        s2 = s1.tapl.typing.fork_scope(f1)
    with s1.tapl.typing.scope_forker(s1) as f1:
        s2 = s1.tapl.typing.fork_scope(f1)
        s2.n != s2.Int
        with s2.tapl.typing.scope_forker(s2) as f2:
            s3 = s2.tapl.typing.fork_scope(f2)
            s3.n % s3.Int == s3.Int
            s3.n = s3.n // s3.Int
            s3 = s2.tapl.typing.fork_scope(f2)
            s3.n = s3.Int * s3.n + s3.Int
        s2.sequence.append(s2.n)
        s2 = s1.tapl.typing.fork_scope(f1)
    s1.tapl.typing.add_return_type(s1, s1.sequence)
    return s1.tapl.typing.get_return_type(s1)
s0.collatz_sequence = s0.tapl.typing.create_function([s0.Int], collatz_sequence(s0.Int))
s0.tapl.print(s0.tapl.to_string(s0.collatz_sequence))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.tapl.print(s0.collatz_sequence(s0.Int))
