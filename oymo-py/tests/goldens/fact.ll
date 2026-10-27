; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"main"()
{
r.entry:
  br label %"r.loop"
r.loop:
  %"acc" = phi  i32 [1, %"r.entry"], [%"next", %"r.loop"]
  %"n" = phi  i32 [5, %"r.entry"], [%"k", %"r.loop"]
  %"next" = mul i32 %"acc", %"n"
  %"k" = sub i32 %"n", 1
  %"done" = icmp eq i32 %"k", 0
  br i1 %"done", label %"r.exit", label %"r.loop"
r.exit:
  %"acc1" = phi  i32 [%"next", %"r.loop"]
  ret i32 %"acc1"
}
