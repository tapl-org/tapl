from tapl_lang.pythonlike.predef1 import predef_scope as s0
s0.x = s0.Int
s0.x = s0.Int
s0.tapl_dev.print(s0.x)
s0.a = s0.b = s0.Str
s0.tapl_dev.print(s0.a)
s0.tapl_dev.print(s0.b)
s0.f = s0.Float
s0.f = s0.Int / s0.Int
s0.c = s0.tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int)
s0.tapl_dev.print(s0.c)
s0.x = s0.c[s0.Int]
s0.tapl_dev.print(s0.c[s0.Int])
s0.c[s0.Int] = s0.Int
del s0.c[s0.Int]
s0.tapl_dev.print(s0.c)
s0.s = s0.tapl_typing.create_typed_set(s0.Int, s0.Int, s0.Int, s0.Int)
s0.tapl_dev.print(s0.s)
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.Int in s1.s
    s1.tapl_dev.print(s1.Str)
    s1 = s0.tapl_typing.fork_scope(f0)
s0.s.add(s0.Int)
s0.s.remove(s0.Int)
s0.tapl_dev.print(s0.s)
s0.dict_obj = s0.tapl_typing.create_typed_dict([s0.Str, s0.Str], [s0.Str, s0.Str])
s0.tapl_dev.print(s0.dict_obj)
s0.value = s0.dict_obj[s0.Str]
s0.tapl_dev.print(s0.dict_obj[s0.Str])
s0.dict_obj[s0.Str] = s0.Str
del s0.dict_obj[s0.Str]
s0.tapl_dev.print(s0.dict_obj)
s0.print(s0.Str)
