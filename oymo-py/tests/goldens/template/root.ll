; ModuleID = ""

define internal i32 @"max32"(i32 %"p.a", i32 %"p.b")
{
r.0:
  %"c" = icmp sgt i32 %"p.a", %"p.b"
  br i1 %"c", label %"q.first", label %"q.second"
q.first:
  ret i32 %"p.a"
q.second:
  ret i32 %"p.b"
}

define i32 @"main"()
{
r.0:
  %"m" = call i32 @"max32"(i32 3, i32 9)
  ret i32 %"m"
}
