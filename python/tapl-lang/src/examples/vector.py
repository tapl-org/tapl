
class Vector_:

    def __init__(self):
        self._elements = []
    
    def __repr__(self):
        return f"Vector({self._elements})"
    
    def __len__(self):
        return len(self._elements)
    
    def append(self, value):
        new_vector = Vector_()
        new_vector._elements = self._elements + [value]
        return new_vector
    
    def concat(self, other):
        new_vector = Vector_()
        new_vector._elements = self._elements + other._elements
        return new_vector