; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"bump"(i32 %"p.n")
{
r.entry:
  %"a" = alloca i32
  store i32 %"p.n", ptr %"a"
  %"v" = load i32, ptr %"a"
  %"w" = add i32 %"v", 1
  ret i32 %"w"
}

define i32 @"sum"(i32 %"p.n")
{
r.entry:
  %"acc" = alloca i32
  store i32 0, ptr %"acc"
  br label %"q.loop"
q.loop:
  %"i" = phi  i32 [%"p.n", %"r.entry"], [%"j", %"q.loop"]
  %"old" = load i32, ptr %"acc"
  %"new" = add i32 %"old", %"i"
  store i32 %"new", ptr %"acc"
  %"j" = sub i32 %"i", 1
  %"done" = icmp eq i32 %"j", 0
  br i1 %"done", label %"q.exit", label %"q.loop"
q.exit:
  %"v" = load i32, ptr %"acc"
  ret i32 %"v"
}
