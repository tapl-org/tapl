from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)
s0.i = s0.Int
s0.i = s0.Int
s0.sum = s0.Int
with s0.tapl.typing.scope_forker(s0) as f0:
    s1 = s0.tapl.typing.fork_scope(f0)
    s1.i > s1.Int
    s1.sum = s1.sum + s1.i
    s1.i = s1.i - s1.Int
    s1 = s0.tapl.typing.fork_scope(f0)
s0.print(s0.sum)
s0.sum = s0.Int
with s0.tapl.typing.scope_forker(s0) as f0:
    s1 = s0.tapl.typing.fork_scope(f0)
    s1.i = s1.range(s1.Int).__iter__().__next__()
    s1.sum = s1.sum + s1.i
    s1 = s0.tapl.typing.fork_scope(f0)
s0.print(s0.sum)
