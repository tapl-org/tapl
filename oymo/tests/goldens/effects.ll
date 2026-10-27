; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"putchar"(i32 %"c")

define i32 @"hi"()
{
r.entry:
  %"x" = call i32 @"putchar"(i32 104)
  %"y" = call i32 @"putchar"(i32 105)
  ret i32 %"y"
}

define i32 @"count"()
{
r.entry:
  br label %"r.loop"
r.loop:
  %"i" = phi  i32 [0, %"r.entry"], [%"j", %"r.loop"]
  %"x" = call i32 @"putchar"(i32 42)
  %"j" = add i32 %"i", 1
  %"done" = icmp eq i32 %"j", 3
  br i1 %"done", label %"r.exit", label %"r.loop"
r.exit:
  %"n" = phi  i32 [%"j", %"r.loop"]
  ret i32 %"n"
}
