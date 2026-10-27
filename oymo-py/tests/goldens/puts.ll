; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"puts"(ptr %"s")

@"msg" = constant [3 x i8] c"hi\00"
define i32 @"main"(i32 %"p.argc")
{
r.entry:
  %"c" = icmp sgt i32 %"p.argc", 1
  br i1 %"c", label %"q.say", label %"r.done"
q.say:
  %"u" = call i32 @"puts"(ptr @"msg")
  br label %"r.done"
r.done:
  ret i32 0
}
