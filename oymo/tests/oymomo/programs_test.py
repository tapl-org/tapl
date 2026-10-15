# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Whole programs run by reduction alone: no BANF, no LLVM. Each one reduces to a byte array."""

from oymo.oymomo import banf_shape, reduction
from oymo.oymomo.grammar import parse


def run(source):
    return banf_shape.reduce_until_top_stable(reduction.resolve(parse(source)))


def test_fibonacci():
    # fib 0 = 0, fib 1 = 1, fib n = fib (n - 1) + fib (n - 2): 0, 1, 1, 2, 3, 5, 8.
    source = """
        let fib = $fix (fib -> n ->
            if 'icmp_ult' {'i32', n, [02000000]} then n
            else 'add' {'i32', fib ('sub' {'i32', n, [01000000]}), fib ('sub' {'i32', n, [02000000]})})
        in fib [06000000]
    """
    assert run(source) == parse("[08000000]~'i32'")


def test_collatz_steps():
    # 7 22 11 34 17 52 26 13 40 20 10 5 16 8 4 2 1: 16 steps.
    source = """
        let collatz = $fix (collatz -> n ->
            if 'icmp_eq' {'i32', n, [01000000]} then [00000000]
            else 'add' {'i32', [01000000], collatz (
                if 'and' {'i32', n, [01000000]}
                then 'add' {'i32', 'mul' {'i32', n, [03000000]}, [01000000]}
                else 'udiv' {'i32', n, [02000000]})})
        in collatz [07000000]
    """
    assert run(source) == parse("[10000000]~'i32'")
