; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

@"answer" = constant i32 42
@"counter" = global i32 41
define i32 @"main"()
{
entry:
  %"a" = load i32, ptr @"answer"
  %"c" = load i32, ptr @"counter"
  %"d" = add i32 %"c", %"a"
  store i32 %"d", ptr @"counter"
  %"e" = load i32, ptr @"counter"
  ret i32 %"e"
}
