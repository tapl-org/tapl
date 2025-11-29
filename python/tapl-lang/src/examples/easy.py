from tapl_lang.pythonlike.predef import *

def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

class Dog_:

    def __init__(self, name):
        self.name = name

    def bark(self):
        if self:
            return self.name + ' says Woof! Woof!'
        return 'You called the Dog factory.'

def greet_dog(dog):
    return 'Hello, ' + dog.name + '!'

def make_dog(factory, name):
    return factory(name)

def main():
    print(factorial(5))
    my_dog = Dog_('Buddy')
    print(my_dog.bark())
    print(greet_dog(my_dog))
    new_dog = make_dog(Dog_, 'Max')
    print(new_dog.bark())
if __name__ == '__main__':
    main()