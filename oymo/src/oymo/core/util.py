# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from oymo.core import syntax


def gather_errors(term: syntax.Term) -> list[syntax.ErrorTerm]:
    error_bucket: list[syntax.ErrorTerm] = []

    def gather_errors_recursive(t: syntax.Term) -> None:
        if isinstance(t, syntax.ErrorTerm):
            error_bucket.append(t)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket
