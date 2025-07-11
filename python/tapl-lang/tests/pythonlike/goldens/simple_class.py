from tapl_lang.pythonlike.predef import *

class SimplestClass:
    pass

def accept(param):
    pass
accept(SimplestClass())

class Circle:

    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return 3.14 * self.radius * self.radius

def print_area(circle):
    print__tapl(circle.area())
print_area(Circle(2.0))
