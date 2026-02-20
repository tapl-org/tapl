from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)
tapl_typing.import_module(s0, ['examples.easy'])
s0.tapl_dev.log(s0.examples.easy.factorial(s0.Int))
s0.my_dog = s0.examples.easy.Dog(s0.Str)
s0.print(s0.my_dog.bark())
s0.print(s0.examples.easy.greet_dog(s0.my_dog))
s0.examples.easy.main()
