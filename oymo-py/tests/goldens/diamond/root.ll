; ModuleID = ""

define internal i32 @"d.twice"(i32 %"p.n")
{
r.0:
  %"y" = mul i32 %"p.n", 2
  ret i32 %"y"
}

define internal i32 @"b.f"(i32 %"p.n")
{
r.0:
  %"t" = call i32 @"d.twice"(i32 %"p.n")
  %"y" = add i32 %"t", 1
  ret i32 %"y"
}

define internal i32 @"c.h"(i32 %"p.n")
{
r.0:
  %"t" = call i32 @"d.twice"(i32 %"p.n")
  %"y" = add i32 %"t", 2
  ret i32 %"y"
}

define i32 @"main"()
{
r.0:
  %"x" = call i32 @"b.f"(i32 1)
  %"y" = call i32 @"c.h"(i32 1)
  %"z" = add i32 %"x", %"y"
  ret i32 %"z"
}
