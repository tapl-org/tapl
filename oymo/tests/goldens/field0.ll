; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"next"()

define i32 @"spin"()
{
r:
  br label %"r.entry"
r.entry:
  %"x" = call i32 @"next"()
  %"c" = icmp eq i32 %"x", 0
  br i1 %"c", label %"r.entry", label %"r.done"
r.done:
  ret i32 0
}

define i32 @"three"()
{
r.entry:
  %"a" = alloca i32
  store i32 0, ptr %"a"
  br label %"q.again"
q.again:
  %"v" = load i32, ptr %"a"
  %"w" = add i32 %"v", 1
  store i32 %"w", ptr %"a"
  %"c" = icmp ult i32 %"w", 3
  br i1 %"c", label %"q.again", label %"q.out"
q.out:
  %"v1" = load i32, ptr %"a"
  ret i32 %"v1"
}
