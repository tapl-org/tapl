from tapl_lang.pythonlike.predef import *
from tapl_lang.lib import tapl_dev
import examples.easy
tapl_dev.log(examples.easy.factorial(7))
my_dog = examples.easy.Dog('Simba')
print(my_dog.bark())
print(examples.easy.greet_dog(my_dog))
examples.easy.main()
