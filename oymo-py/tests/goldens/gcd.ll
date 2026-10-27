; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"gcd"(i32 %"p.a", i32 %"p.b")
{
r.entry:
  br label %"r.loop"
r.loop:
  %"a" = phi  i32 [%"p.a", %"r.entry"], [%"b", %"q.step"]
  %"b" = phi  i32 [%"p.b", %"r.entry"], [%"c", %"q.step"]
  %"z" = icmp eq i32 %"b", 0
  br i1 %"z", label %"r.done", label %"q.step"
q.step:
  %"c" = urem i32 %"a", %"b"
  br label %"r.loop"
r.done:
  %"c1" = phi  i32 [%"a", %"r.loop"]
  ret i32 %"c1"
}

define i32 @"main"()
{
r.entry:
  %"y" = call i32 @"gcd"(i32 48, i32 18)
  ret i32 %"y"
}
