from tapl_lang.pythonlike.predef1 import predef_proxy as s0

def collatz_sequence(n):
    s1 = s0.api__tapl.create_scope(parent__tapl=s0, n=n)
    with s1.api__tapl.scope_forker(s1) as f1:
        s2 = s1.api__tapl.fork_scope(f1)
        s2.n < s2.Int
        s2.api__tapl.add_return_type(s2, s2.ListInt)
        s2 = s1.api__tapl.fork_scope(f1)
    s1.sequence = s1.ListInt
    with s1.api__tapl.scope_forker(s1) as f1:
        s2 = s1.api__tapl.fork_scope(f1)
        s2.n != s2.Int
        with s2.api__tapl.scope_forker(s2) as f2:
            s3 = s2.api__tapl.fork_scope(f2)
            s3.n % s3.Int == s3.Int
            s3.n = s3.n // s3.Int
            s3 = s2.api__tapl.fork_scope(f2)
            s3.n = s3.Int * s3.n + s3.Int
        s2.sequence.append(s2.n)
        s2 = s1.api__tapl.fork_scope(f1)
    s1.api__tapl.add_return_type(s1, s1.sequence)
    return s1.api__tapl.get_return_type(s1)
s0.collatz_sequence = s0.api__tapl.create_function([s0.Int], collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
s0.print(s0.collatz_sequence(s0.Int))
