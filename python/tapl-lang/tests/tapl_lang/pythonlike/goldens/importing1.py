from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)
s0.tapl.typing.import_module(s0, ['examples.easy'])
s0.tapl.print(s0.examples.easy.factorial(s0.Int))
s0.my_dog = s0.examples.easy.Dog(s0.Str)
s0.print(s0.my_dog.bark())
s0.print(s0.examples.easy.greet_dog(s0.my_dog))
s0.examples.easy.main()
