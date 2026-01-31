
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
    
# TODO: create a variable by specifying the value and type layer separately. This helps to lift the function to type layer.
# TODO: keep a journal of type operations subtype checks so any one can add extra rules if needed. Especially if earlier checks returns None.