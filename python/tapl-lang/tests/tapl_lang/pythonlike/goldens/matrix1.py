from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.tapl_typing.import_module(s0, ['examples.matrix'])
s0.matrix = s0.examples.matrix
s0.matrix.accept_matrix_2_3(s0.matrix.Matrix(2, 3)())
s0.tapl.print(s0.tapl.to_string(s0.matrix.accept_matrix_2_3))
s0.tapl.print(s0.tapl.to_string(s0.matrix.sum(2, 2)))
s0.matrix_2_2 = s0.matrix.Matrix(2, 2)()
s0.matrix_2_2.values = s0.tapl_typing.create_typed_list(s0.tapl_typing.create_typed_list(s0.Int, s0.Int), s0.tapl_typing.create_typed_list(s0.Int, s0.Int))
s0.matrix_2_3 = s0.matrix.Matrix(2, 3)()
s0.matrix_2_3.values = s0.tapl_typing.create_typed_list(s0.tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int), s0.tapl_typing.create_typed_list(s0.Int, s0.Int, s0.Int))
s0.tapl.print(s0.matrix.sum(2, 2)(s0.matrix_2_2, s0.matrix_2_2))
s0.tapl.print(s0.matrix.multiply(2, 2, 3)(s0.matrix_2_2, s0.matrix_2_3))
s0.tapl.print(s0.Str)
