; ModuleID = ""

define i32 @"main"()
{
r.entry:
  br label %"r.even"
r.even:
  %"n" = phi  i32 [10, %"r.entry"], [%"m1", %"q1.next"]
  %"z" = icmp eq i32 %"n", 0
  br i1 %"z", label %"r.yes", label %"q.next"
q.next:
  %"m" = sub i32 %"n", 1
  br label %"r.odd"
r.odd:
  %"n1" = phi  i32 [%"m", %"q.next"]
  %"z1" = icmp eq i32 %"n1", 0
  br i1 %"z1", label %"r.no", label %"q1.next"
q1.next:
  %"m1" = sub i32 %"n1", 1
  br label %"r.even"
r.yes:
  ret i32 1
r.no:
  ret i32 0
}
