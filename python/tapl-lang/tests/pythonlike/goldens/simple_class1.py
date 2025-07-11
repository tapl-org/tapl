from tapl_lang.pythonlike import predef1 as predef
s0 = predef.Scope(predef.predef_scope)

class SimplestClass:
    pass
s0.SimplestClass = predef.Scope(label__tapl='SimplestClass')
s0.SimplestClass_ = predef.Scope(label__tapl='SimplestClass_')
s0.SimplestClass.__call__ = predef.FunctionType([s0.SimplestClass], s0.SimplestClass_)

def accept(param):
    s1 = predef.Scope(s0, param=param)
    pass
    return predef.get_return_type(s1)
s0.accept = predef.FunctionType([s0.SimplestClass_], accept(s0.SimplestClass_))
s0.accept(s0.SimplestClass())

class Circle:

    def __init__(self, radius):
        s1 = predef.Scope(s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return predef.get_return_type(s1)

    def area(self):
        s1 = predef.Scope(s0, self=self)
        predef.add_return_type(s1, s1.Float * s1.self.radius * s1.self.radius)
        return predef.get_return_type(s1)
s0.Circle = predef.Scope(label__tapl='Circle')
s0.Circle_ = predef.Scope(label__tapl='Circle_')
s0.Circle.__init__ = predef.FunctionType([s0.Circle_, s0.Float], Circle.__init__(s0.Circle_, s0.Float))
s0.Circle_.__init__ = predef.FunctionType([s0.Float], s0.Circle.__init__.result)
s0.Circle.area = predef.FunctionType([s0.Circle_], Circle.area(s0.Circle_))
s0.Circle_.area = predef.FunctionType([], s0.Circle.area.result)
s0.Circle.__call__ = predef.FunctionType([s0.Circle, s0.Float], s0.Circle_)

def print_area(circle):
    s1 = predef.Scope(s0, circle=circle)
    s1.print__tapl(s1.circle.area())
    return predef.get_return_type(s1)
s0.print_area = predef.FunctionType([s0.Circle_], print_area(s0.Circle_))
s0.print_area(s0.Circle(s0.Float))
