from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def Matrix(rows, cols):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, rows=rows, cols=cols)

    class Class:

        def __init__(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.self.rows = s2.rows
            s2.self.cols = s2.cols
            s2.self.values = s2.Int
            return s2.tapl_typing.get_return_type(s2)

        def text(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.tapl_typing.add_return_type(s2, 'Matrix({},{})!'.format(s2.self.rows, s2.self.cols))
            return s2.tapl_typing.get_return_type(s2)
    s1.Class = s1.tapl_typing.create_class(cls=Class, init_args=[], methods=[('text', [])])
    s1.tapl_typing.add_return_type(s1, s1.Class)
    return s1.tapl_typing.get_return_type(s1)
s0.Matrix = Matrix

def accept_matrix_3_5(matrix):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, matrix=matrix)
    s1.tapl_dev.print(s1.matrix.text())
    return s1.tapl_typing.get_return_type(s1)
s0.accept_matrix_3_5 = s0.tapl_typing.create_function([s0.Matrix(s0.Int, s0.Int).result__sa], accept_matrix_3_5(s0.Matrix(s0.Int, s0.Int).result__sa))
s0.tapl_dev.print(s0.accept_matrix_3_5)
s0.tapl_dev.print(s0.Str)