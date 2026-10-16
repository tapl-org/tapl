; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"putchar"(i32 %"c")

define i32 @"hi"()
{
entry:
  %"q" = call i32 @"putchar"(i32 104)
  %"r" = call i32 @"putchar"(i32 105)
  ret i32 %"r"
}

define i32 @"count"()
{
entry:
  br label %"loop"
loop:
  %"i" = phi  i32 [0, %"entry"], [%"j", %"loop"]
  %"p" = call i32 @"putchar"(i32 42)
  %"j" = add i32 %"i", 1
  %"done" = icmp eq i32 %"j", 3
  br i1 %"done", label %"exit", label %"loop"
exit:
  ret i32 %"j"
}
