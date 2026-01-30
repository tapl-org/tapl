from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def factorial(n):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, n=n)
    s1.factorial = s1.tapl_typing.create_function([s1.Int], s1.Int)
    s1.tapl_typing.set_return_type(s1, s1.Int)
    with s1.tapl_typing.scope_forker(s1) as f1:
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.tapl_typing.create_union(s2.n == s2.Int, s2.n == s2.Int)
        s2.tapl_typing.add_return_type(s2, s2.Int)
        s2 = s1.tapl_typing.fork_scope(f1)
        s2.tapl_typing.add_return_type(s2, s2.n * s2.factorial(s2.n - s2.Int))
    return s1.tapl_typing.get_return_type(s1)
s0.factorial = s0.tapl_typing.create_function([s0.Int], factorial(s0.Int))

class Dog:

    def __init__(self, name):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, name=name)
        s1.self.name = s1.name
        return s1.tapl_typing.get_return_type(s1)

    def bark(self):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self)
        s1.bark = s1.tapl_typing.create_function([], s1.Str)
        s1.tapl_typing.set_return_type(s1, s1.Str)
        s1.tapl_typing.add_return_type(s1, s1.self.name + s1.Str)
        return s1.tapl_typing.get_return_type(s1)
s0.Dog = s0.tapl_typing.create_class(cls=Dog, init_args=[s0.Str], methods=[('bark', [])])

def greet_dog(dog):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, dog=dog)
    s1.greet_dog = s1.tapl_typing.create_function([s1.Dog.result__sa], s1.Str)
    s1.tapl_typing.set_return_type(s1, s1.Str)
    s1.tapl_typing.add_return_type(s1, s1.Str + s1.dog.name + s1.Str)
    return s1.tapl_typing.get_return_type(s1)
s0.greet_dog = s0.tapl_typing.create_function([s0.Dog.result__sa], greet_dog(s0.Dog.result__sa))

def make_dog(factory, name):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, factory=factory, name=name)
    s1.make_dog = s1.tapl_typing.create_function([s1.Dog, s1.Str], s1.Dog.result__sa)
    s1.tapl_typing.set_return_type(s1, s1.Dog.result__sa)
    s1.tapl_typing.add_return_type(s1, s1.factory(s1.name))
    return s1.tapl_typing.get_return_type(s1)
s0.make_dog = s0.tapl_typing.create_function([s0.Dog, s0.Str], make_dog(s0.Dog, s0.Str))

def main():
    s1 = s0.tapl_typing.create_scope(parent__sa=s0)
    s1.print(s1.factorial(s1.Int))
    s1.my_dog = s1.Dog(s1.Str)
    s1.print(s1.my_dog.bark())
    s1.print(s1.greet_dog(s1.my_dog))
    s1.new_dog = s1.make_dog(s1.Dog, s1.Str)
    s1.print(s1.new_dog.bark())
    return s1.tapl_typing.get_return_type(s1)
s0.main = s0.tapl_typing.create_function([], main())
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.__name__ == s1.Str
    s1.main()
    s1 = s0.tapl_typing.fork_scope(f0)