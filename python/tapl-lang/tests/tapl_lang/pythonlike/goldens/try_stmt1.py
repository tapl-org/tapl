from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.result = s1.Int / s1.Int
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.print(s1.Str)
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.print(s1.Str)
