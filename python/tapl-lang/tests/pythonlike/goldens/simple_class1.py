from tapl_lang.pythonlike.predef1 import predef_proxy as s0

class SimplestClass:
    pass
s0.SimplestClass_, s0.SimplestClass = s0.api__tapl.create_class(cls=SimplestClass, init_args=[], methods=[])

def accept(param):
    s1 = s0.api__tapl.create_scope(parent__tapl=s0, param=param)
    pass
    return s1.api__tapl.get_return_type(s1)
s0.accept = s0.api__tapl.create_function([s0.SimplestClass_], accept(s0.SimplestClass_))
s0.accept(s0.SimplestClass())

class Circle:

    def __init__(self, radius):
        s1 = s0.api__tapl.create_scope(parent__tapl=s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return s1.api__tapl.get_return_type(s1)

    def area(self):
        s1 = s0.api__tapl.create_scope(parent__tapl=s0, self=self)
        s1.api__tapl.add_return_type(s1, s1.Float * s1.self.radius * s1.self.radius)
        return s1.api__tapl.get_return_type(s1)
s0.Circle_, s0.Circle = s0.api__tapl.create_class(cls=Circle, init_args=[s0.Float], methods=[('area', [])])

def print_area(circle):
    s1 = s0.api__tapl.create_scope(parent__tapl=s0, circle=circle)
    s1.api__tapl.print_log(s1.circle.area())
    return s1.api__tapl.get_return_type(s1)
s0.print_area = s0.api__tapl.create_function([s0.Circle_], print_area(s0.Circle_))
s0.print_area(s0.Circle(s0.Float))
