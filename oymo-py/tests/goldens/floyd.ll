; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"floyd"(ptr %"p.d", i32 %"p.n")
{
r.entry:
  br label %"r.k"
r.k:
  %"k" = phi  i32 [0, %"r.entry"], [%"k1", %"rk.knext"]
  %"kc" = icmp slt i32 %"k", %"p.n"
  %"kn" = mul i32 %"k", %"p.n"
  br i1 %"kc", label %"rk.i", label %"r.done"
rk.i:
  %"i" = phi  i32 [0, %"r.k"], [%"i1", %"ri.inext"]
  %"ic" = icmp slt i32 %"i", %"p.n"
  %"ni" = mul i32 %"i", %"p.n"
  br i1 %"ic", label %"ri.j", label %"rk.knext"
ri.j:
  %"j" = phi  i32 [0, %"rk.i"], [%"j1", %"rj.jnext"]
  %"jc" = icmp slt i32 %"j", %"p.n"
  br i1 %"jc", label %"rj.relax", label %"ri.inext"
rj.relax:
  %"ik" = add i32 %"ni", %"k"
  %"kj" = add i32 %"kn", %"j"
  %"ij" = add i32 %"ni", %"j"
  %"pik" = getelementptr i32, ptr %"p.d", i32 %"ik"
  %"pkj" = getelementptr i32, ptr %"p.d", i32 %"kj"
  %"pij" = getelementptr i32, ptr %"p.d", i32 %"ij"
  %"dik" = load i32, ptr %"pik"
  %"dkj" = load i32, ptr %"pkj"
  %"dij" = load i32, ptr %"pij"
  %"s" = add i32 %"dik", %"dkj"
  %"lt" = icmp slt i32 %"s", %"dij"
  br i1 %"lt", label %"rs.store", label %"rj.jnext"
rs.store:
  store i32 %"s", ptr %"pij"
  br label %"rj.jnext"
rj.jnext:
  %"j1" = add i32 %"j", 1
  br label %"ri.j"
ri.inext:
  %"i1" = add i32 %"i", 1
  br label %"rk.i"
rk.knext:
  %"k1" = add i32 %"k", 1
  br label %"r.k"
r.done:
  ret i32 0
}

define i32 @"main"()
{
r.entry:
  %"a" = alloca [9 x i32]
  %"q0" = getelementptr i32, ptr %"a", i32 0
  %"q1" = getelementptr i32, ptr %"a", i32 1
  %"q2" = getelementptr i32, ptr %"a", i32 2
  %"q3" = getelementptr i32, ptr %"a", i32 3
  %"q4" = getelementptr i32, ptr %"a", i32 4
  %"q5" = getelementptr i32, ptr %"a", i32 5
  %"q6" = getelementptr i32, ptr %"a", i32 6
  %"q7" = getelementptr i32, ptr %"a", i32 7
  %"q8" = getelementptr i32, ptr %"a", i32 8
  store i32 0, ptr %"q0"
  store i32 4, ptr %"q1"
  store i32 11, ptr %"q2"
  store i32 1000, ptr %"q3"
  store i32 0, ptr %"q4"
  store i32 3, ptr %"q5"
  store i32 1000, ptr %"q6"
  store i32 1000, ptr %"q7"
  store i32 0, ptr %"q8"
  %"z" = call i32 @"floyd"(ptr %"a", i32 3)
  %"v" = load i32, ptr %"q2"
  ret i32 %"v"
}
