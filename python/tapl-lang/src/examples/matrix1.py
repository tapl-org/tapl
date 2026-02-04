from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

def Matrix(rows, cols):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, rows=rows, cols=cols)

    class Matrix_:
        class_name = 'Matrix({},{})'.format(s1.rows, s1.cols)

        def __init__(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.self.rows = s2.rows
            s2.self.cols = s2.cols
            s2.self.num_rows = s2.Int
            s2.self.num_cols = s2.Int
            s2.self.values = s2.List(s2.Int)
            s2.self.values = s2.tapl_typing.create_typed_list()
            s2.v = s2.Int
            with s2.tapl_typing.scope_forker(s2) as f2:
                s3 = s2.tapl_typing.fork_scope(f2)
                s3.i = s3.range(s3.self.num_rows).__iter__().__next__()
                s3.columns = s3.tapl_typing.create_typed_list()
                with s3.tapl_typing.scope_forker(s3) as f3:
                    s4 = s3.tapl_typing.fork_scope(f3)
                    s4.j = s4.range(s4.self.num_cols).__iter__().__next__()
                    s4.columns.append(s4.v)
                    s4.v = s4.v + s4.Int
                    s4 = s3.tapl_typing.fork_scope(f3)
                s3.self.values.append(s3.columns)
                s3 = s2.tapl_typing.fork_scope(f2)
            return s2.tapl_typing.get_return_type(s2)

        def __repr__(self):
            s2 = s1.tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.tapl_typing.add_return_type(s2, s2.str(s2.self.values))
            return s2.tapl_typing.get_return_type(s2)
    s1.Matrix_ = s1.tapl_typing.create_class(cls=Matrix_, init_args=[], methods=[('__repr__', [])])
    s1.tapl_typing.add_return_type(s1, s1.Matrix_)
    return s1.tapl_typing.get_return_type(s1)
s0.Matrix = Matrix

def accept_matrix_3_2(matrix):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, matrix=matrix)
    s1.tapl_dev.print(s1.matrix)
    s1.tapl_dev.print(s1.matrix.values)
    return s1.tapl_typing.get_return_type(s1)
s0.accept_matrix_3_2 = s0.tapl_typing.create_function([s0.Matrix(3, 2).result__sa], accept_matrix_3_2(s0.Matrix(3, 2).result__sa))
s0.accept_matrix_3_2(s0.Matrix(3, 2)())
s0.tapl_dev.print(s0.tapl_dev.to_string(s0.accept_matrix_3_2))
s0.tapl_dev.print('Done')