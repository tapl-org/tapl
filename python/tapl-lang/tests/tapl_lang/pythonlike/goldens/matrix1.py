from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
tapl_typing.import_module(s0, ['tapl_dev'], 'tapl_lang.lib', 0)
tapl_typing.import_module(s0, ['examples.matrix'])
s0.matrix = s0.examples.matrix
s0.matrix.accept_matrix_2_3(s0.matrix.Matrix(2, 3)())
s0.tapl_dev.log(s0.tapl_dev.describe(s0.matrix.accept_matrix_2_3))
s0.tapl_dev.log(s0.tapl_dev.describe(s0.matrix.sum(2, 2)))
s0.matrix_2_2 = s0.matrix.Matrix(2, 2)()
s0.matrix_2_2.values = tapl_typing.create_typed_list(tapl_typing.create_typed_list(s0.Int, s0.Int), tapl_typing.create_typed_list(s0.Int, s0.Int))
s0.matrix_2_3 = s0.matrix.Matrix(2, 3)()
s0.matrix_2_3.values = tapl_typing.create_typed_list(tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int), tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int))
s0.tapl_dev.log(s0.matrix.sum(2, 2)(s0.matrix_2_2, s0.matrix_2_2))
s0.tapl_dev.log(s0.matrix.multiply(2, 2, 3)(s0.matrix_2_2, s0.matrix_2_3))
s0.tapl_dev.log(s0.Str)
