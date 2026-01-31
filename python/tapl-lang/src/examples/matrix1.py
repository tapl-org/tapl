from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def create_matrix(rows, cols):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, rows=rows, cols=cols)

    class Matrix:

        def __init__(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.self.rows = s2.rows
            s2.self.cols = s2.cols
            s2.self.values = s2.Int
            return s2.tapl_typing.get_return_type(s2)

        def text(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.tapl_typing.add_return_type(s2, self.rows)
            return s2.tapl_typing.get_return_type(s2)
    s1.Matrix = s1.tapl_typing.create_class(cls=Matrix, init_args=[], methods=[('text', [])])
    s1.tapl_typing.add_return_type(s1, s1.Matrix)
    return s1.tapl_typing.get_return_type(s1)
s0.create_matrix = create_matrix
s0.tapl_dev.print(s0.create_matrix(3, 2)().text())