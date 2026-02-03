from tapl_lang.pythonlike.predef import *

def Matrix(rows, cols):

    class Matrix_:
        class_name = 'Matrix({},{})'.format(rows, cols)

        def __init__(self):
            self.rows = rows
            self.cols = cols
            self.values = 0

        def text(self):
            return self.values
    return Matrix_

def accept_matrix_3_5(matrix):
    pass
tapl_dev.print(tapl_dev.to_string(accept_matrix_3_5))
accept_matrix_3_5(Matrix(3, 5)())
tapl_dev.print('Done')