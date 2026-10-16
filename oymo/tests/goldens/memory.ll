; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"bump"(i32 %"n")
{
entry:
  %"p" = alloca i32
  store i32 %"n", ptr %"p"
  %"v" = load i32, ptr %"p"
  %"w" = add i32 %"v", 1
  ret i32 %"w"
}

define i32 @"sum"(i32 %"n")
{
entry:
  %"acc.1" = alloca i32
  store i32 0, ptr %"acc.1"
  br label %"loop"
loop:
  %"acc" = phi  ptr [%"acc.1", %"entry"], [%"acc", %"loop"]
  %"i" = phi  i32 [%"n", %"entry"], [%"j", %"loop"]
  %"old" = load i32, ptr %"acc"
  %"new" = add i32 %"old", %"i"
  store i32 %"new", ptr %"acc"
  %"j" = sub i32 %"i", 1
  %"done" = icmp eq i32 %"j", 0
  br i1 %"done", label %"exit", label %"loop"
exit:
  %"r" = load i32, ptr %"acc"
  ret i32 %"r"
}
