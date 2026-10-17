; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"main"()
{
entry:
  br label %"loop"
loop:
  %"acc" = phi  i32 [1, %"entry"], [%"next", %"loop"]
  %"n" = phi  i32 [5, %"entry"], [%"m", %"loop"]
  %"next" = mul i32 %"acc", %"n"
  %"m" = sub i32 %"n", 1
  %"done" = icmp eq i32 %"m", 0
  br i1 %"done", label %"exit", label %"loop"
exit:
  ret i32 %"next"
}
