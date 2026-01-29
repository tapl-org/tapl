from tapl_lang.pythonlike.predef import *

class SimplestClass_:
    pass

def accept(param):
    pass
accept(SimplestClass_())

class Circle_:

    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return 3.14 * self.radius * self.radius

    def set_radius(self, radius):
        self.radius = radius

    def is_bigger_than(self, radius):
        return self.radius > radius

def print_area(circle):
    tapl_dev.print(circle.area())
    tapl_dev.print(circle.is_bigger_than(1.0))
print_area(Circle_(2.0))
