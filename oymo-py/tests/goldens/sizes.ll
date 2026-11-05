; ModuleID = ""

define i32 @"main"()
{
r.0:
  %"s" = add i64 ptrtoint (ptr getelementptr ({i32, ptr}, ptr null, i32 1) to i64), ptrtoint (ptr getelementptr ({i32, ptr}, ptr null, i32 0, i32 1) to i64)
  %"t" = add i64 %"s", ptrtoint (ptr getelementptr ({i1, ptr}, ptr null, i32 0, i32 1) to i64)
  %"u" = trunc i64 %"t" to i32
  ret i32 %"u"
}
