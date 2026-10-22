; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"gcd"(i32 %"a", i32 %"b")
{
entry:
  br label %"loop"
loop:
  %"a.1" = phi  i32 [%"a", %"entry"], [%"b.1", %"step"]
  %"b.1" = phi  i32 [%"b", %"entry"], [%"r", %"step"]
  %"z" = icmp eq i32 %"b.1", 0
  br i1 %"z", label %"done", label %"step"
step:
  %"r" = urem i32 %"a.1", %"b.1"
  br label %"loop"
done:
  ret i32 %"a.1"
}

define i32 @"main"()
{
entry:
  %".2" = call i32 @"gcd"(i32 48, i32 18)
  ret i32 %".2"
}
