; ModuleID = ""

declare ptr @"malloc"(i64 %"n")

declare void @"free"(ptr %"p")

define internal void @"fill"(ptr %"p.slot", i32 %"p.x")
{
r.entry:
  %"z" = icmp eq i32 %"p.x", 0
  br i1 %"z", label %"r.skip", label %"r.write"
r.skip:
  ret void
r.write:
  store i32 %"p.x", ptr %"p.slot"
  ret void
}

define i32 @"main"()
{
r.0:
  %"buf" = call ptr @"malloc"(i64 4)
  call void @"fill"(ptr %"buf", i32 42)
  %"y" = load i32, ptr %"buf"
  call void @"free"(ptr %"buf")
  ret i32 %"y"
}
