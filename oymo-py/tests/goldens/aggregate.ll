; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"sum"()
{
r.entry:
  %"a" = alloca [3 x i32]
  %"p0" = getelementptr [3 x i32], ptr %"a", i64 0, i64 0
  %"p1" = getelementptr [3 x i32], ptr %"a", i64 0, i64 1
  %"p2" = getelementptr [3 x i32], ptr %"a", i64 0, i64 2
  store i32 10, ptr %"p0"
  store i32 20, ptr %"p1"
  store i32 12, ptr %"p2"
  br label %"q.loop"
q.loop:
  %"i" = phi  i64 [0, %"r.entry"], [%"j", %"q.loop"]
  %"total" = phi  i32 [0, %"r.entry"], [%"s", %"q.loop"]
  %"e" = getelementptr [3 x i32], ptr %"a", i64 0, i64 %"i"
  %"x" = load i32, ptr %"e"
  %"s" = add i32 %"total", %"x"
  %"j" = add i64 %"i", 1
  %"done" = icmp eq i64 %"j", 3
  br i1 %"done", label %"r.exit", label %"q.loop"
r.exit:
  %"total1" = phi  i32 [%"s", %"q.loop"]
  ret i32 %"total1"
}
