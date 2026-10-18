# TODO

## Now
- can we use copy and discard instead of dup and drop. actually what are the better names?
- can we make drop takes multiple argument, actually we can do this when we add struct. so drop F (drop t G) becomes drop {F, t, G}
- wy we need a comma in struct. instead we can use whitespace.

## Someday / maybe

- `/* */` block comment syntax.
- `$fields_to_struct` argument must be
  `A = {more=[01], label=utf8, value=term, rest=A} | {more=[00]}`; no other labels allowed.
