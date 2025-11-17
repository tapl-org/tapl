from tapl_lang.pythonlike.predef1 import predef_scope as s0
s0.i = s0.Int
s0.i = s0.Int
s0.sum = s0.Int
with s0.api__tapl.scope_forker(s0) as f0:
    s1 = s0.api__tapl.fork_scope(f0)
    s1.i > s1.Int
    s1.sum = s1.sum + s1.i
    s1.i = s1.i - s1.Int
    s1 = s0.api__tapl.fork_scope(f0)
s0.print(s0.sum)
s0.sum = s0.Int
with s0.api__tapl.scope_forker(s0) as f0:
    s1 = s0.api__tapl.fork_scope(f0)
    s1.i = s1.range(s1.Int).__iter__().__next__()
    s1.sum = s1.sum + s1.i
    s1 = s0.api__tapl.fork_scope(f0)
s0.print(s0.sum)
