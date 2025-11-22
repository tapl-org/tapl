from tapl_lang.pythonlike.predef1 import predef_scope as s0
s0.x = s0.Int
s0.x = s0.Int
s0.print_dual(s0.x)
s0.a = s0.b = s0.Str
s0.print_dual(s0.a)
s0.print_dual(s0.b)
s0.c = s0.tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int)
s0.print_dual(s0.c)
s0.x = s0.c[s0.Int]
s0.print_dual(s0.c[s0.Int])
s0.c[s0.Int] = s0.Int
del s0.c[s0.Int]
s0.print_dual(s0.c)
s0.dict_obj = s0.tapl_typing.create_typed_dict([s0.Str, s0.Str], [s0.Str, s0.Str])
s0.print_dual(s0.dict_obj)
s0.value = s0.dict_obj[s0.Str]
s0.print_dual(s0.dict_obj[s0.Str])
s0.dict_obj[s0.Str] = s0.Str
del s0.dict_obj[s0.Str]
s0.print_dual(s0.dict_obj)
