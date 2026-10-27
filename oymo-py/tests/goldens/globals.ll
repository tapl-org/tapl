; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

@"answer" = constant i32 42
@"counter" = global i32 41
@"msg" = constant [3 x i8] c"hi\00"
@"first" = constant ptr @"counter"
@"second" = constant ptr getelementptr (i8, ptr @"msg", i64 1)
@"nothing" = global ptr null
@"zeros" = global {i32, [2 x i64]} zeroinitializer
define i32 @"main"()
{
r.entry:
  %"a" = load i32, ptr @"answer"
  %"c" = load i32, ptr @"counter"
  %"d" = add i32 %"c", %"a"
  store i32 %"d", ptr @"counter"
  %"e" = load i32, ptr @"counter"
  ret i32 %"e"
}
