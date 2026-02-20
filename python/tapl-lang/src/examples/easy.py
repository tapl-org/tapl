def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

class Dog:

    def __init__(self, name):
        self.name = name

    def bark(self):
        return self.name + ' says Woof! Woof!'

def greet_dog(dog):
    return 'Hello, ' + dog.name + '!'

def make_dog(factory, name):
    return factory(name)

def main():
    print(factorial(5))
    my_dog = Dog('Buddy')
    print(my_dog.bark())
    print(greet_dog(my_dog))
    new_dog = make_dog(Dog, 'Max')
    print(new_dog.bark())
if __name__ == '__main__':
    main()