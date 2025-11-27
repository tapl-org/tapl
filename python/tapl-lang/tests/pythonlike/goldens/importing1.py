from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.tapl_typing.import_module(s0, ['examples.easy'])
s0.tapl_dev.print(s0.examples.easy.factorial(s0.Int))
