; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"main"(i32 %"p.a")
{
r.entry:
  %"y" = add i32 %"p.a", 5
  ret i32 %"y"
}
