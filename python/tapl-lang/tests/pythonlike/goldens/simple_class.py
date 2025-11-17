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

def print_area(circle):
    tapl_typing.print_log(circle.area())
print_area(Circle_(2.0))
