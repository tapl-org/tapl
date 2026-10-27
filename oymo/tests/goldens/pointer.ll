; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"fill"(ptr %"p", i64 %"n")

define i32 @"main"()
{
r.entry:
  %"q" = alloca {i32, i64}
  %"y" = getelementptr {i32, i64}, ptr %"q", i64 0, i32 1
  %"s" = call i32 @"fill"(ptr %"y", i64 8)
  ret i32 %"s"
}
