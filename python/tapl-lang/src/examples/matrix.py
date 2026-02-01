from tapl_lang.pythonlike.predef import *

def Matrix(rows, cols):

    class Class:

        def __init__(self):
            self.rows = rows
            self.cols = cols
            self.values = 0

        def text(self):
            return self.values
    return Class

def accept_matrix_3_5(matrix):
    tapl_dev.print(matrix.text())
tapl_dev.print(accept_matrix_3_5)
tapl_dev.print('Done')