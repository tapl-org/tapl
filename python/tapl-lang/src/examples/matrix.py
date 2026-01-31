from tapl_lang.pythonlike.predef import *

def create_matrix(rows, cols):

    class Matrix:

        def __init__(self):
            self.rows = rows
            self.cols = cols
            self.values = 0

        def text(self):
            return 'dd'
    return Matrix
tapl_dev.print(create_matrix(3, 2)().text())