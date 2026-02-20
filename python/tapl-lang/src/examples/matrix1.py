from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)

def Matrix(rows, cols):
    s1 = tapl_typing.create_scope(parent__sa=s0, rows=rows, cols=cols)

    class Matrix_:
        class_name = 'Matrix({},{})'.format(s1.rows, s1.cols)

        def __init__(self):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self)
            s2.self.rows = s2.rows
            s2.self.cols = s2.cols
            s2.self.num_rows = s2.Int
            s2.self.num_cols = s2.Int
            s2.self.values = s2.List(s2.List(s2.Int))
            with tapl_typing.scope_forker(s2) as f2:
                s3 = tapl_typing.fork_scope(f2)
                s3.i = s3.range(s3.self.num_rows).__iter__().__next__()
                s3.columns = s3.List(s3.Int)
                with tapl_typing.scope_forker(s3) as f3:
                    s4 = tapl_typing.fork_scope(f3)
                    s4.j = s4.range(s4.self.num_cols).__iter__().__next__()
                    s4.columns.append(s4.Int)
                    s4 = tapl_typing.fork_scope(f3)
                s3.self.values.append(s3.columns)
                s3 = tapl_typing.fork_scope(f2)
            return tapl_typing.get_return_type(s2)

        def __repr__(self):
            s2 = tapl_typing.create_scope(parent__sa=s1, self=self)
            tapl_typing.add_return_type(s2, s2.str(s2.self.values))
            return tapl_typing.get_return_type(s2)
    s1.Matrix_ = tapl_typing.create_class(cls=Matrix_, init_args=[], methods=[('__repr__', [])])
    tapl_typing.add_return_type(s1, s1.Matrix_)
    return tapl_typing.get_return_type(s1)
s0.Matrix = Matrix

def accept_matrix_2_3(matrix):
    s1 = tapl_typing.create_scope(parent__sa=s0, matrix=matrix)
    pass
    return tapl_typing.get_return_type(s1)
s0.accept_matrix_2_3 = tapl_typing.create_function([s0.Matrix(2, 3).result__sa], accept_matrix_2_3(s0.Matrix(2, 3).result__sa))

def sum(rows, cols):
    s1 = tapl_typing.create_scope(parent__sa=s0, rows=rows, cols=cols)

    def sum_(a, b):
        s2 = tapl_typing.create_scope(parent__sa=s1, a=a, b=b)
        s2.result = s2.Matrix(s2.rows, s2.cols)()
        with tapl_typing.scope_forker(s2) as f2:
            s3 = tapl_typing.fork_scope(f2)
            s3.i = s3.range(s3.result.num_rows).__iter__().__next__()
            with tapl_typing.scope_forker(s3) as f3:
                s4 = tapl_typing.fork_scope(f3)
                s4.j = s4.range(s4.result.num_cols).__iter__().__next__()
                s4.result.values[s4.i][s4.j] = s4.a.values[s4.i][s4.j] + s4.b.values[s4.i][s4.j]
                s4 = tapl_typing.fork_scope(f3)
            s3 = tapl_typing.fork_scope(f2)
        tapl_typing.add_return_type(s2, s2.result)
        return tapl_typing.get_return_type(s2)
    s1.sum_ = tapl_typing.create_function([s1.Matrix(s1.rows, s1.cols).result__sa, s1.Matrix(s1.rows, s1.cols).result__sa], sum_(s1.Matrix(s1.rows, s1.cols).result__sa, s1.Matrix(s1.rows, s1.cols).result__sa))
    tapl_typing.add_return_type(s1, s1.sum_)
    return tapl_typing.get_return_type(s1)
s0.sum = sum

def multiply(m, n, p):
    s1 = tapl_typing.create_scope(parent__sa=s0, m=m, n=n, p=p)

    def multiply_(a, b):
        s2 = tapl_typing.create_scope(parent__sa=s1, a=a, b=b)
        s2.result = s2.Matrix(s2.m, s2.p)()
        with tapl_typing.scope_forker(s2) as f2:
            s3 = tapl_typing.fork_scope(f2)
            s3.i = s3.range(s3.a.num_rows).__iter__().__next__()
            with tapl_typing.scope_forker(s3) as f3:
                s4 = tapl_typing.fork_scope(f3)
                s4.j = s4.range(s4.b.num_cols).__iter__().__next__()
                with tapl_typing.scope_forker(s4) as f4:
                    s5 = tapl_typing.fork_scope(f4)
                    s5.k = s5.range(s5.a.num_cols).__iter__().__next__()
                    s5.result.values[s5.i][s5.j] = s5.result.values[s5.i][s5.j] + s5.a.values[s5.i][s5.k] * s5.b.values[s5.k][s5.j]
                    s5 = tapl_typing.fork_scope(f4)
                s4 = tapl_typing.fork_scope(f3)
            s3 = tapl_typing.fork_scope(f2)
        tapl_typing.add_return_type(s2, s2.result)
        return tapl_typing.get_return_type(s2)
    s1.multiply_ = tapl_typing.create_function([s1.Matrix(s1.m, s1.n).result__sa, s1.Matrix(s1.n, s1.p).result__sa], multiply_(s1.Matrix(s1.m, s1.n).result__sa, s1.Matrix(s1.n, s1.p).result__sa))
    tapl_typing.add_return_type(s1, s1.multiply_)
    return tapl_typing.get_return_type(s1)
s0.multiply = multiply

def main():
    s1 = tapl_typing.create_scope(parent__sa=s0)
    s1.matrix_2_2 = s1.Matrix(2, 2)()
    s1.matrix_2_2.values = tapl_typing.create_typed_list(tapl_typing.create_typed_list(s1.Int, s1.Int), tapl_typing.create_typed_list(s1.Int, s1.Int))
    s1.matrix_2_3 = s1.Matrix(2, 3)()
    s1.matrix_2_3.values = tapl_typing.create_typed_list(tapl_typing.create_typed_list(s1.Int, s1.Int, s1.Int), tapl_typing.create_typed_list(s1.Int, s1.Int, s1.Int))
    s1.accept_matrix_2_3(s1.matrix_2_3)
    s1.print(s1.sum(2, 2)(s1.matrix_2_2, s1.matrix_2_2))
    s1.print(s1.multiply(2, 2, 3)(s1.matrix_2_2, s1.matrix_2_3))
    return tapl_typing.get_return_type(s1)
s0.main = tapl_typing.create_function([], main())
with tapl_typing.scope_forker(s0) as f0:
    s1 = tapl_typing.fork_scope(f0)
    s1.__name__ == s1.Str
    s1.main()
    s1 = tapl_typing.fork_scope(f0)