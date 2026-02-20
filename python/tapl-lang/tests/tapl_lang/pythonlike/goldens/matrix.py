from tapl_lang.lib import tapl_dev
import examples.matrix
matrix = examples.matrix
matrix.accept_matrix_2_3(matrix.Matrix(2, 3)())
tapl_dev.log(tapl_dev.describe(matrix.accept_matrix_2_3))
tapl_dev.log(tapl_dev.describe(matrix.add(2, 2)))
matrix_2_2 = matrix.Matrix(2, 2)()
matrix_2_2.values = [[1, 2], [3, 4]]
matrix_2_3 = matrix.Matrix(2, 3)()
matrix_2_3.values = [[1, 2, 3], [4, 5, 6]]
tapl_dev.log(matrix.add(2, 2)(matrix_2_2, matrix_2_2))
tapl_dev.log(matrix.multiply(2, 2, 3)(matrix_2_2, matrix_2_3))
tapl_dev.log('Done')
