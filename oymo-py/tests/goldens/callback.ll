; ModuleID = ""

define internal i32 @"inc"(i32 %"p.n")
{
r.0:
  %"y" = add i32 %"p.n", 1
  ret i32 %"y"
}

define internal i32 @"dbl"(i32 %"p.n")
{
r.0:
  %"y" = mul i32 %"p.n", 2
  ret i32 %"y"
}

@"ops" = internal constant [2 x ptr] [ptr @"inc", ptr @"dbl"]
define internal i32 @"twice"(ptr %"p.f", i32 %"p.x")
{
r.0:
  %"a" = call i32 %"p.f"(i32 %"p.x")
  %"b" = call i32 %"p.f"(i32 %"a")
  ret i32 %"b"
}

define internal i32 @"apply_at"(i64 %"p.i", i32 %"p.v")
{
r.0:
  %"a" = getelementptr ptr, ptr @"ops", i64 %"p.i"
  %"f" = load ptr, ptr %"a"
  %"y" = call i32 %"f"(i32 %"p.v")
  ret i32 %"y"
}

define i32 @"main"()
{
r.entry:
  %"a" = call i32 @"twice"(ptr @"inc", i32 5)
  %"b" = call i32 @"apply_at"(i64 1, i32 5)
  %"s" = add i32 %"a", %"b"
  br label %"r.pick"
r.pick:
  %"h" = phi  ptr [@"inc", %"r.entry"]
  %"s1" = phi  i32 [%"s", %"r.entry"]
  %"c" = call i32 %"h"(i32 10)
  %"t" = add i32 %"s1", %"c"
  ret i32 %"t"
}
