; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define internal i32 @"lexer.token"(i32 %"p.c")
{
r.0:
  %"k" = call i32 @"parser.kind"(i32 %"p.c")
  %"t" = add i32 %"k", 10
  ret i32 %"t"
}

define internal i32 @"lexer.error"(i32 %"p.c")
{
r.0:
  %"v" = call i32 @"lib.apply"(i32 %"p.c")
  ret i32 %"v"
}

define internal i32 @"parser.kind"(i32 %"p.c")
{
r.0:
  %"k" = and i32 %"p.c", 1
  ret i32 %"k"
}

define internal i32 @"parser.parse"(i32 %"p.c")
{
r.0:
  %"t" = call i32 @"lexer.token"(i32 %"p.c")
  %"e" = call i32 @"lexer.error"(i32 %"t")
  ret i32 %"e"
}

define internal i32 @"lib.step"(i32 %"p.n")
{
r.0:
  %"y" = add i32 %"p.n", 1
  ret i32 %"y"
}

define internal i32 @"lib.apply"(i32 %"p.n")
{
r.0:
  %"y" = call i32 @"lib.step"(i32 %"p.n")
  ret i32 %"y"
}

define internal i32 @"dbl.lib.step"(i32 %"p.n")
{
r.0:
  %"y" = mul i32 %"p.n", 2
  ret i32 %"y"
}

define internal i32 @"dbl.lib.apply"(i32 %"p.n")
{
r.0:
  %"y" = call i32 @"dbl.lib.step"(i32 %"p.n")
  ret i32 %"y"
}

define i32 @"main"()
{
r.0:
  %"a" = call i32 @"parser.parse"(i32 3)
  %"b" = call i32 @"dbl.lib.apply"(i32 %"a")
  ret i32 %"b"
}
