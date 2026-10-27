; ModuleID = ""
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

define i32 @"floyd"(ptr %"d", i32 %"n")
{
entry:
  br label %"kloop"
kloop:
  %"d.1" = phi  ptr [%"d", %"entry"], [%"d.2", %"knext"]
  %"n.1" = phi  i32 [%"n", %"entry"], [%"n.2", %"knext"]
  %"k" = phi  i32 [0, %"entry"], [%"k1", %"knext"]
  %"kc" = icmp slt i32 %"k", %"n.1"
  %"kn.3" = mul i32 %"k", %"n.1"
  br i1 %"kc", label %"iloop", label %"done"
iloop:
  %"d.2" = phi  ptr [%"d.1", %"kloop"], [%"d.3", %"inext"]
  %"n.2" = phi  i32 [%"n.1", %"kloop"], [%"n.3", %"inext"]
  %"k.1" = phi  i32 [%"k", %"kloop"], [%"k.2", %"inext"]
  %"kn" = phi  i32 [%"kn.3", %"kloop"], [%"kn.1", %"inext"]
  %"i" = phi  i32 [0, %"kloop"], [%"i1", %"inext"]
  %"ic" = icmp slt i32 %"i", %"n.2"
  %"ni.2" = mul i32 %"i", %"n.2"
  br i1 %"ic", label %"jloop", label %"knext"
jloop:
  %"d.3" = phi  ptr [%"d.2", %"iloop"], [%"d.4", %"jnext"]
  %"n.3" = phi  i32 [%"n.2", %"iloop"], [%"n.4", %"jnext"]
  %"k.2" = phi  i32 [%"k.1", %"iloop"], [%"k.3", %"jnext"]
  %"kn.1" = phi  i32 [%"kn", %"iloop"], [%"kn.2", %"jnext"]
  %"i.1" = phi  i32 [%"i", %"iloop"], [%"i.2", %"jnext"]
  %"ni" = phi  i32 [%"ni.2", %"iloop"], [%"ni.1", %"jnext"]
  %"j" = phi  i32 [0, %"iloop"], [%"j1", %"jnext"]
  %"jc" = icmp slt i32 %"j", %"n.3"
  br i1 %"jc", label %"relax", label %"inext"
relax:
  %"ik" = add i32 %"ni", %"k.2"
  %"kj" = add i32 %"kn.1", %"j"
  %"ij" = add i32 %"ni", %"j"
  %"pik" = getelementptr i32, ptr %"d.3", i32 %"ik"
  %"pkj" = getelementptr i32, ptr %"d.3", i32 %"kj"
  %"pij" = getelementptr i32, ptr %"d.3", i32 %"ij"
  %"dik" = load i32, ptr %"pik"
  %"dkj" = load i32, ptr %"pkj"
  %"dij" = load i32, ptr %"pij"
  %"s" = add i32 %"dik", %"dkj"
  %"lt" = icmp slt i32 %"s", %"dij"
  br i1 %"lt", label %"update", label %"jnext"
update:
  store i32 %"s", ptr %"pij"
  br label %"jnext"
jnext:
  %"d.4" = phi  ptr [%"d.3", %"relax"], [%"d.3", %"update"]
  %"n.4" = phi  i32 [%"n.3", %"relax"], [%"n.3", %"update"]
  %"k.3" = phi  i32 [%"k.2", %"relax"], [%"k.2", %"update"]
  %"kn.2" = phi  i32 [%"kn.1", %"relax"], [%"kn.1", %"update"]
  %"i.2" = phi  i32 [%"i.1", %"relax"], [%"i.1", %"update"]
  %"ni.1" = phi  i32 [%"ni", %"relax"], [%"ni", %"update"]
  %"j.1" = phi  i32 [%"j", %"relax"], [%"j", %"update"]
  %"j1" = add i32 %"j.1", 1
  br label %"jloop"
inext:
  %"i1" = add i32 %"i.1", 1
  br label %"iloop"
knext:
  %"k1" = add i32 %"k.1", 1
  br label %"kloop"
done:
  ret i32 0
}

define i32 @"main"()
{
entry:
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
  %"r" = load i32, ptr %"q2"
  ret i32 %"r"
}
