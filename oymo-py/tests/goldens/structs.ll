; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"second"(i32 %"p.a", i8 %"p.b")
{
r.entry:
  %"s1" = insertvalue {i8, i32} {i8 0, i32 0}, i8 %"p.b", 0
  %"s2" = insertvalue {i8, i32} %"s1", i32 %"p.a", 1
  %"y" = extractvalue {i8, i32} %"s2", 1
  ret i32 %"y"
}

define i32 @"main"()
{
r.entry:
  %"y" = call i32 @"second"(i32 7, i8 1)
  ret i32 %"y"
}
