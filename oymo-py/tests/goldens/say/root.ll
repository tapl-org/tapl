; ModuleID = ""

declare i32 @"puts"(ptr %"s")

@"hello.msg" = internal constant [6 x i8] c"hello\00"
define internal i32 @"hello.say"()
{
r.0:
  %"u" = call i32 @"puts"(ptr @"hello.msg")
  ret i32 %"u"
}

@"bye.msg" = internal constant [4 x i8] c"bye\00"
define internal i32 @"bye.say"()
{
r.0:
  %"u" = call i32 @"puts"(ptr @"bye.msg")
  ret i32 %"u"
}

define i32 @"main"()
{
r.0:
  %"a" = call i32 @"hello.say"()
  %"b" = call i32 @"bye.say"()
  ret i32 0
}
