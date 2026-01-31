from tapl_lang.lib import kinds
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl_typing.create_scope(parent__sa=predef_scope__sa)

class Vector(kinds.BaseType):
    def __init__(self, len, element_type):
        self._len = len
        self._element_type = element_type
    
    def __repr__(self):
        return f"Vector(len={self._len}, element_type={self._element_type})"
    
    def __len__(self):
        return s0.Int

    def append(self, value):
        if not kinds.check_type_equality(value, self._element_type):
            raise TypeError(f'Element type mismatch: expected {self._element_type}, got {value}.')
        return Vector(self._len + 1, self._element_type)

    def concat(self, other):
        if not isinstance(other, Vector):
            raise TypeError(f'Expected Vector type for concat, got {other}.')
        if not kinds.check_type_equality(other._element_type, self._element_type):
            raise TypeError(f'Element type mismatch: expected {self._element_type}, got {other._element_type}.')
        return Vector(self._len + other._len, self._element_type)

s0.Vector = Vector
s0.Vector_ = kinds.create_function([], )