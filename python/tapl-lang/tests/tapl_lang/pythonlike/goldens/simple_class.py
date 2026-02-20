from tapl_lang.pythonlike.predef import *
from tapl_lang.lib import tapl_dev

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

    def set_radius(self, radius):
        self.radius = radius

    def is_bigger_than(self, radius):
        return self.radius > radius

def print_area(circle):
    tapl_dev.log(circle.area())
    tapl_dev.log(circle.is_bigger_than(1.0))
print_area(Circle(2.0))
