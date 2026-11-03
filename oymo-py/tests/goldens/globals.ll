; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

@"answer" = internal constant i32 42
@"counter" = internal global i32 41
@"msg" = internal constant [3 x i8] c"hi\00"
@"nothing" = internal global ptr null
@"zeros" = internal global {i32, [2 x i64]} zeroinitializer
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
