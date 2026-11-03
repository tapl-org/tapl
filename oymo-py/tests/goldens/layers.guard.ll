; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"main"(i32 %"p.a")
{
r.entry:
  %"y" = sub i32 %"p.a", %"p.a"
  ret i32 %"y"
}
