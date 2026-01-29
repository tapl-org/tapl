from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

class SimplestClass_:
    pass
s0.SimplestClass, s0.SimplestClass_ = s0.tapl_typing.create_class(cls=SimplestClass_, init_args=[], methods=[])

def accept(param):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, param=param)
    pass
    return s1.tapl_typing.get_return_type(s1)
s0.accept = s0.tapl_typing.create_function([s0.SimplestClass], accept(s0.SimplestClass))
s0.accept(s0.SimplestClass_())

class Circle_:

    def __init__(self, radius):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return s1.tapl_typing.get_return_type(s1)

    def area(self):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self)
        s1.area = s1.tapl_typing.create_function([], s1.Float)
        s1.tapl_typing.set_return_type(s1, s1.Float)
        s1.tapl_typing.add_return_type(s1, s1.Float * s1.self.radius * s1.self.radius)
        return s1.tapl_typing.get_return_type(s1)

    def set_radius(self, radius):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return s1.tapl_typing.get_return_type(s1)

    def is_bigger_than(self, radius):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, radius=radius)
        s1.tapl_typing.add_return_type(s1, s1.self.radius > s1.radius)
        return s1.tapl_typing.get_return_type(s1)
s0.Circle, s0.Circle_ = s0.tapl_typing.create_class(cls=Circle_, init_args=[s0.Float], methods=[('area', []), ('set_radius', [s0.Float]), ('is_bigger_than', [s0.Float])])

def print_area(circle):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, circle=circle)
    s1.tapl_dev.print(s1.circle.area())
    s1.tapl_dev.print(s1.circle.is_bigger_than(s1.Float))
    return s1.tapl_typing.get_return_type(s1)
s0.print_area = s0.tapl_typing.create_function([s0.Circle], print_area(s0.Circle))
s0.print_area(s0.Circle_(s0.Float))
