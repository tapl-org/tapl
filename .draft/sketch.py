def id(a: int) -> int:
    return a


with scope.choices('if'):
   with scope.case('true'):
      print('hello')
   with scope.case('false'):
      print('world')

scope

if 1 == 2:
  a = 34
  hello(a)
else:
  b = '35'
  hello_str(b)


Int == Int
with ctx.conditional_blocks():  # if
    with ctx.block():  # true
        scope.store('a', Int)
        hello(scope.load('a'))
    with scope.block():  # false
        scope.store('b', '35')
        hello_str(scope.load('b'))

with scope.conditional_block():  # true
    scope.store('a', Int)
    hello(scope.load('a'))
with scope.conditional_block():  # false
    scope.store('b', '35')
    hello_str(scope.load('b'))
scope.apply_conditional_blocks()


with scope.conditional_blocks():
   scope.new_block()
   scope.store('a', Int)
   hello(scope.load('a'))
   scope.new_block()
   scope.store('b', '35')
   hello_str(scope.load('b'))