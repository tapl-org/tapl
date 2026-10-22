; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"main"(i32 %"n")
{
entry:
  %"x" = mul i32 %"n", 2
  %"y" = add i32 %"x", 1
  ret i32 %"y"
}
