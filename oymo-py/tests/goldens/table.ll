; ModuleID = ""

@"hello" = internal constant [6 x i8] c"hello\00"
@"bye" = internal constant [4 x i8] c"bye\00"
@"names" = internal constant [2 x ptr] [ptr @"hello", ptr @"bye"]
declare i32 @"puts"(ptr %"s")

define i32 @"main"()
{
r.entry:
  br label %"r.loop"
r.loop:
  %"i" = phi  i64 [0, %"r.entry"], [%"j", %"r.loop"]
  %"a" = getelementptr ptr, ptr @"names", i64 %"i"
  %"s" = load ptr, ptr %"a"
  %"u" = call i32 @"puts"(ptr %"s")
  %"j" = add i64 %"i", 1
  %"more" = icmp ult i64 %"j", 2
  br i1 %"more", label %"r.loop", label %"r.done"
r.done:
  ret i32 0
}
