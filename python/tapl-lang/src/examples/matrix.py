from tapl_lang.pythonlike.predef import *

def Matrix(rows, cols):

    class Matrix_:
        class_name = 'Matrix({},{})'.format(rows, cols)

        def __init__(self):
            self.rows = rows
            self.cols = cols
            self.num_rows = rows
            self.num_cols = cols
            self.values = []
            v = 1
            for i in range(self.num_rows):
                columns = []
                for j in range(self.num_cols):
                    columns.append(v)
                    v = v + 1
                self.values.append(columns)

        def __repr__(self):
            return str(self.values)
    return Matrix_

def accept_matrix_3_2(matrix):
    tapl_dev.print(matrix)
    tapl_dev.print(matrix.values)
accept_matrix_3_2(Matrix(3, 2)())
tapl_dev.print(tapl_dev.to_string(accept_matrix_3_2))
tapl_dev.print('Done')