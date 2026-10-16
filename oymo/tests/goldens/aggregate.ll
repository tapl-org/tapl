; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"sum"()
{
entry:
  %"a.1" = alloca [3 x i32]
  %"p0" = getelementptr [3 x i32], ptr %"a.1", i64 0, i64 0
  %"p1" = getelementptr [3 x i32], ptr %"a.1", i64 0, i64 1
  %"p2" = getelementptr [3 x i32], ptr %"a.1", i64 0, i64 2
  store i32 10, ptr %"p0"
  store i32 20, ptr %"p1"
  store i32 12, ptr %"p2"
  br label %"loop"
loop:
  %"a" = phi  ptr [%"a.1", %"entry"], [%"a", %"loop"]
  %"i" = phi  i64 [0, %"entry"], [%"j", %"loop"]
  %"total" = phi  i32 [0, %"entry"], [%"t", %"loop"]
  %"p" = getelementptr [3 x i32], ptr %"a", i64 0, i64 %"i"
  %"x" = load i32, ptr %"p"
  %"t" = add i32 %"total", %"x"
  %"j" = add i64 %"i", 1
  %"done" = icmp eq i64 %"j", 3
  br i1 %"done", label %"exit", label %"loop"
exit:
  ret i32 %"t"
}
