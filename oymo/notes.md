
## Type vs Machine representation terminology

Type = semantic/program meaning
Form = logical structure/arrangement of components
Layout = physical memory representation

a TYPE may have multiple FORMs, and a FORM may have multiple LAYOUTs.

For examples
```
Bool
  type: Bool
  form: i1
  LLVM layout: i1

Int32
  type: Int
  form: i32
  LLVM layout: i32

Point
  type: Point(x: Int, y: Int)
  form: (x:Int, y:Int)
  LLVM layout: { i32, i32 }
```