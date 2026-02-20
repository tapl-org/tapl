from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)
s0.x = s0.Int
s0.x = s0.Int
s0.tapl_dev.log(s0.x)
s0.a = s0.b = s0.Str
s0.tapl_dev.log(s0.a)
s0.tapl_dev.log(s0.b)
s0.f = s0.Float
with tapl_typing.scope_forker(s0) as f0:
    s1 = tapl_typing.fork_scope(f0)
    s1.f = s1.Int / s1.Int
    s1 = tapl_typing.fork_scope(f0)
    s1.tapl_dev.log(s1.Str)
    s1 = tapl_typing.fork_scope(f0)
    s1.tapl_dev.log(s1.Str)
s0.c = tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int)
s0.tapl_dev.log(s0.c)
s0.x = s0.c[s0.Int]
s0.tapl_dev.log(s0.c[s0.Int])
s0.c[s0.Int] = s0.Int
del s0.c[s0.Int]
s0.tapl_dev.log(s0.c)
s0.s = tapl_typing.create_typed_set(s0.Int, s0.Int, s0.Int, s0.Int)
s0.tapl_dev.log(s0.s)
with tapl_typing.scope_forker(s0) as f0:
    s1 = tapl_typing.fork_scope(f0)
    s1.Int in s1.s
    s1.tapl_dev.log(s1.Str)
    s1 = tapl_typing.fork_scope(f0)
s0.s.add(s0.Int)
s0.s.remove(s0.Int)
s0.tapl_dev.log(s0.s)
s0.dict_obj = tapl_typing.create_typed_dict([s0.Str, s0.Str], [s0.Str, s0.Str])
s0.tapl_dev.log(s0.dict_obj)
s0.value = s0.dict_obj[s0.Str]
s0.tapl_dev.log(s0.dict_obj[s0.Str])
s0.dict_obj[s0.Str] = s0.Str
del s0.dict_obj[s0.Str]
s0.tapl_dev.log(s0.dict_obj)
s0.print(s0.Str)
