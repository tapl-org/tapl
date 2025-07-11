# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass
from typing import cast

from tapl_lang.core import parser, syntax
from tapl_lang.core.parser import Cursor
from tapl_lang.pythonlike import expr, stmt
from tapl_lang.pythonlike import rule_names as rn

# https://docs.python.org/3/reference/grammar.html


def get_grammar() -> parser.Grammar:
    rules: parser.GrammarRuleMap = {}
    grammar: parser.Grammar = parser.Grammar(rule_map=rules, start_rule=rn.START)

    def add(name: str, ordered_parse_functions: list[parser.ParseFunction | str]) -> None:
        if name in rules:
            raise ValueError(f'Rule {name} is already defined.')
        if ordered_parse_functions:
            rules[name] = [parser.route(fn) if isinstance(fn, str) else fn for fn in ordered_parse_functions]

    add('parameter', [_rule_parameter_with_type, _rule_parameter_no_type])

    # STARTING RULES
    # ==============
    add(rn.START, [_parse_start])

    # HELPER RULES
    # ============
    add(rn.TOKEN, [_parse_token])

    # GENERAL STATEMENTS
    # ==================
    add(rn.STATEMENTS, [])
    add(rn.STATEMENT, [rn.COMPOUND_STMT, rn.SIMPLE_STMTS])
    add(rn.SINGLE_COMPOUND_STMT, [])
    add(rn.STATEMENT_NEWLINE, [])
    add(rn.SIMPLE_STMTS, [rn.SIMPLE_STMT])
    add(rn.SIMPLE_STMT, [rn.ASSIGNMENT, _parse_statement__star_expressions, rn.RETURN_STMT, rn.PASS_STMT])
    add(rn.COMPOUND_STMT, [rn.FUNCTION_DEF, rn.IF_STMT, rn.CLASS_DEF])

    # SIMPLE STATEMENTS
    # =================
    add(rn.ASSIGNMENT, [_parse_assignment])
    add(rn.ANNOTATED_RHS, [rn.STAR_EXPRESSIONS])
    add(rn.AUGASSIGN, [])
    add(rn.RETURN_STMT, [_parse_return])
    add(rn.PASS_STMT, [_parse_pass])
    add(rn.BREAK_STMT, [])
    add(rn.CONTINUE_STMT, [])
    add(rn.GLOBAL_STMT, [])
    add(rn.NONLOCAL_STMT, [])
    add(rn.DEL_STMT, [])
    add(rn.YIELD_STMT, [])
    add(rn.ASSERT_STMT, [])
    add(rn.IMPORT_STMT, [])

    # Import statements
    # -----------------
    add(rn.IMPORT_NAME, [])
    add(rn.IMPORT_FROM, [])
    add(rn.IMPORT_FROM_TARGETS, [])
    add(rn.IMPORT_FROM_AS_NAMES, [])
    add(rn.IMPORT_FROM_AS_NAME, [])
    add(rn.DOTTED_AS_NAMES, [])
    add(rn.DOTTED_AS_NAME, [])
    add(rn.DOTTED_NAME, [])

    # COMPOUND STATEMENTS
    # ===================

    # Common elements
    # ---------------
    add(rn.BLOCK, [])
    add(rn.DECORATORS, [])

    # Class definitions
    # -----------------
    add(rn.CLASS_DEF, [_parse_class_def])
    add(rn.CLASS_DEF_RAW, [])

    # Function definitions
    # --------------------
    add(rn.FUNCTION_DEF, [_parse_function_def])
    add(rn.FUNCTION_DEF_RAW, [])

    # Function parameters
    # -------------------
    add(rn.PARAMS, [])
    add(rn.PARAMETERS, [])
    add(rn.SLASH_NO_DEFAULT, [])
    add(rn.SLASH_WITH_DEFAULT, [])
    add(rn.STAR_ETC, [])
    add(rn.KWDS, [])
    add(rn.PARAM_NO_DEFAULT, [])
    add(rn.PARAM_NO_DEFAULT_STAR_ANNOTATION, [])
    add(rn.PARAM_WITH_DEFAULT, [])
    add(rn.PARAM_MAYBE_DEFAULT, [])
    add(rn.PARAM, [])
    add(rn.PARAM_STAR_ANNOTATION, [])
    add(rn.ANNOTATION, [])
    add(rn.STAR_ANNOTATION, [])
    add(rn.DEFAULT, [])

    # If statement
    # ------------
    add(rn.IF_STMT, [_parse_if_stmt, rn.ELSE_BLOCK])
    add(rn.ELIF_STMT, [])
    add(rn.ELSE_BLOCK, [_parse_else_stmt])

    # While statement
    # ---------------
    add(rn.WHILE_STMT, [])

    # For statement
    # -------------
    add(rn.FOR_STMT, [])

    # With statement
    # --------------
    add(rn.WITH_STMT, [])
    add(rn.WITH_ITEM, [])

    # Try statement
    # -------------
    add(rn.TRY_STMT, [])

    # Except statement
    # ----------------
    add(rn.EXCEPT_BLOCK, [])
    add(rn.EXCEPT_STAR_BLOCK, [])
    add(rn.FINALLY_BLOCK, [])

    # Match statement
    # ---------------
    add(rn.MATCH_STMT, [])
    add(rn.SUBJECT_EXPR, [])
    add(rn.CASE_BLOCK, [])
    add(rn.GUARD, [])
    add(rn.PATTERNS, [])
    add(rn.PATTERN, [])
    add(rn.AS_PATTERN, [])
    add(rn.OR_PATTERN, [])
    add(rn.CLOSED_PATTERN, [])
    add(rn.LITERAL_PATTERN, [])
    add(rn.LITERAL_EXPR, [])
    add(rn.COMPLEX_NUMBER, [])
    add(rn.SIGNED_NUMBER, [])
    add(rn.SIGNED_REAL_NUMBER, [])
    add(rn.REAL_NUMBER, [])
    add(rn.IMAGINARY_NUMBER, [])
    add(rn.CAPTURE_PATTERN, [])
    add(rn.PATTERN_CAPTURE_TARGET, [])
    add(rn.WILDCARD_PATTERN, [])
    add(rn.VALUE_PATTERN, [])
    add(rn.ATTR, [])
    add(rn.NAME_OR_ATTR, [])
    add(rn.GROUP_PATTERN, [])
    add(rn.SEQUENCE_PATTERN, [])
    add(rn.OPEN_SEQUENCE_PATTERN, [])
    add(rn.MAYBE_SEQUENCE_PATTERN, [])
    add(rn.MAYBE_STAR_PATTERN, [])
    add(rn.STAR_PATTERN, [])
    add(rn.MAPPING_PATTERN, [])
    add(rn.ITEMS_PATTERN, [])
    add(rn.KEY_VALUE_PATTERN, [])
    add(rn.DOUBLE_STAR_PATTERN, [])
    add(rn.CLASS_PATTERN, [])
    add(rn.POSITIONAL_PATTERNS, [])
    add(rn.KEYWORD_PATTERNS, [])
    add(rn.KEYWORD_PATTERN, [])

    # Type statement
    # ---------------
    add(rn.TYPE_ALIAS, [])

    # Type parameter declaration
    # --------------------------
    add(rn.TYPE_PARAMS, [])
    add(rn.TYPE_PARAM_SEQ, [])
    add(rn.TYPE_PARAM, [])
    add(rn.TYPE_PARAM_BOUND, [])
    add(rn.TYPE_PARAM_DEFAULT, [])
    add(rn.TYPE_PARAM_STARRED_DEFAULT, [])

    # EXPRESSIONS
    # -----------
    add(rn.EXPRESSIONS, [])
    add(rn.EXPRESSION, [rn.DISJUNCTION])
    add(rn.YIELD_EXPR, [])
    add(rn.STAR_EXPRESSIONS, [rn.STAR_EXPRESSION])
    add(rn.STAR_EXPRESSION, [rn.EXPRESSION])
    add(rn.STAR_NAMED_EXPRESSIONS, [])
    add(rn.STAR_NAMED_EXPRESSION, [])
    add(rn.ASSIGNMENT_EXPRESSION, [])
    add(rn.NAMED_EXPRESSION, [])
    add(rn.DISJUNCTION, [_parse_disjunction__or, rn.CONJUNCTION])
    add(rn.CONJUNCTION, [_parse_conjunction__and, rn.INVERSION])
    add(rn.INVERSION, [_parse_inversion__not, rn.COMPARISON])

    # Comparison operators
    # --------------------
    add(rn.COMPARISON, [_parse_comparison, rn.SUM])  # TODO: Implement using BITWISE_OR rule instead of SUM
    add(rn.COMPARE_OP_BITWISE_OR_PAIR, [])
    add(rn.EQ_BITWISE_OR, [])
    add(rn.NOTEQ_BITWISE_OR, [])
    add(rn.LTE_BITWISE_OR, [])
    add(rn.LT_BITWISE_OR, [])
    add(rn.GTE_BITWISE_OR, [])
    add(rn.GT_BITWISE_OR, [])
    add(rn.NOTIN_BITWISE_OR, [])
    add(rn.IN_BITWISE_OR, [])
    add(rn.ISNOT_BITWISE_OR, [])
    add(rn.IS_BITWISE_OR, [])

    # Bitwise operators
    # -----------------
    add(rn.BITWISE_OR, [])
    add(rn.BITWISE_XOR, [])
    add(rn.BITWISE_AND, [])
    add(rn.SHIFT_EXPR, [])

    # Arithmetic operators
    # --------------------
    add(rn.SUM, [_parse_sum__binary, rn.TERM])
    add(rn.TERM, [_parse_term__binary, _parse_invalid_factor, rn.FACTOR])
    add(rn.FACTOR, [_parse_factor__unary, rn.PRIMARY])
    add(rn.POWER, [])

    # Primary elements
    # ----------------
    # Primary elements are things like "obj.something.something", "obj[something]", "obj(something)", "obj" ...
    add(rn.AWAIT_PRIMARY, [])
    add(rn.PRIMARY, [_parse_primary__attribute, _parse_primary__call, rn.ATOM])
    add(rn.SLICES, [])
    add(rn.SLICE, [])
    add(rn.ATOM, [_parse_atom__name_load, _parse_atom__bool, _parse_atom__string, _parse_atom__number])
    add(rn.GROUP, [])

    # Lambda functions
    # ----------------
    add(rn.LAMBDEF, [])
    add(rn.LAMBDA_PARAMS, [])
    add(rn.LAMBDA_PARAMETERS, [])
    add(rn.LAMBDA_SLASH_NO_DEFAULT, [])
    add(rn.LAMBDA_SLASH_WITH_DEFAULT, [])
    add(rn.LAMBDA_STAR_ETC, [])
    add(rn.LAMBDA_KWDS, [])
    add(rn.LAMBDA_PARAM_NO_DEFAULT, [])
    add(rn.LAMBDA_PARAM_WITH_DEFAULT, [])
    add(rn.LAMBDA_PARAM_MAYBE_DEFAULT, [])

    # LITERALS
    # ========
    add(rn.FSTRING_MIDDLE, [])
    add(rn.FSTRING_REPLACEMENT_FIELD, [])
    add(rn.FSTRING_CONVERSION, [])
    add(rn.FSTRING_FULL_FORMAT_SPEC, [])
    add(rn.FSTRING_FORMAT_SPEC, [])
    add(rn.FSTRING, [])
    add(rn.TSTRING_FORMAT_SPEC_REPLACEMENT_FIELD, [])
    add(rn.TSTRING_FORMAT_SPEC, [])
    add(rn.TSTRING_FULL_FORMAT_SPEC, [])
    add(rn.TSTRING_REPLACEMENT_FIELD, [])
    add(rn.TSTRING_MIDDLE, [])
    add(rn.TSTRING, [])
    add(rn.STRING, [])
    add(rn.STRINGS, [])
    add(rn.LIST, [])
    add(rn.TUPLE, [])
    add(rn.SET, [])
    # Dicts
    # -----
    add(rn.DICT, [])
    add(rn.DOUBLE_STARRED_KVPAIRS, [])
    add(rn.DOUBLE_STARRED_KVPAIR, [])
    add(rn.KVPAIR, [])

    # Comprehensions & Generators
    # ---------------------------
    add(rn.FOR_IF_CLAUSES, [])
    add(rn.FOR_IF_CLAUSE, [])
    add(rn.LISTCOMP, [])
    add(rn.SETCOMP, [])
    add(rn.GENEXP, [])
    add(rn.DICTCOMP, [])

    # FUNCTION CALL ARGUMENTS
    # =======================
    add(rn.ARGUMENTS, [])
    add(rn.ARGS, [])
    add(rn.KWARGS, [])
    add(rn.STARRED_EXPRESSION, [])
    add(rn.KWARG_OR_STARRED, [])
    add(rn.KWARG_OR_DOUBLE_STARRED, [])

    # ASSIGNMENT TARGETS
    # ==================

    # Generic targets
    # ---------------
    add(rn.STAR_TARGETS, [_parse_star_targets__single])
    add(rn.STAR_TARGETS_LIST_SEQ, [])
    add(rn.STAR_TARGETS_TUPLE_SEQ, [])
    add(rn.STAR_TARGET, [rn.TARGET_WITH_STAR_ATOM])
    add(rn.TARGET_WITH_STAR_ATOM, [_parse_target_with_star_atom__attribute, rn.STAR_ATOM])
    add(rn.STAR_ATOM, [_parse_star_atom__name_store])
    add(rn.SINGLE_TARGET, [])
    add(rn.SINGLE_SUBSCRIPT_ATTRIBUTE_TARGET, [])
    add(rn.T_PRIMARY, [_parse_t_primary__attribute, _parse_t_primary__atom])
    add(rn.T_LOOKAHEAD, [_parse_t_lookahead])

    # Targets for del statements
    # --------------------------
    add(rn.DEL_TARGETS, [])
    add(rn.DEL_TARGET, [])
    add(rn.DEL_T_ATOM, [])

    # TYPING ELEMENTS
    # ---------------
    add(rn.TYPE_EXPRESSIONS, [])
    add(rn.FUNC_TYPE_COMMENT, [])

    # INVALID RULES
    # =============
    add(rn.INVALID_ARGUMENTS, [])
    add(rn.EXPRESSION_WITHOUT_INVALID, [])
    add(rn.INVALID_LEGACY_EXPRESSION, [])
    add(rn.INVALID_TYPE_PARAM, [])
    add(rn.INVALID_EXPRESSION, [])
    add(rn.INVALID_NAMED_EXPRESSION, [])
    add(rn.INVALID_ASSIGNMENT, [])
    add(rn.INVALID_ANN_ASSIGN_TARGET, [])
    add(rn.INVALID_RAISE_STMT, [])
    add(rn.INVALID_DEL_STMT, [])
    add(rn.INVALID_BLOCK, [])
    add(rn.INVALID_COMPREHENSION, [])
    add(rn.INVALID_DICT_COMPREHENSION, [])
    add(rn.INVALID_PARAMETERS, [])
    add(rn.INVALID_DEFAULT, [])
    add(rn.INVALID_STAR_ETC, [])
    add(rn.INVALID_KWDS, [])
    add(rn.INVALID_PARAMETERS_HELPER, [])
    add(rn.INVALID_LAMBDA_PARAMETERS, [])
    add(rn.INVALID_LAMBDA_PARAMETERS_HELPER, [])
    add(rn.INVALID_LAMBDA_STAR_ETC, [])
    add(rn.INVALID_LAMBDA_KWDS, [])
    add(rn.INVALID_DOUBLE_TYPE_COMMENTS, [])
    add(rn.INVALID_WITH_ITEM, [])
    add(rn.INVALID_FOR_IF_CLAUSE, [])
    add(rn.INVALID_FOR_TARGET, [])
    add(rn.INVALID_GROUP, [])
    add(rn.INVALID_IMPORT, [])
    add(rn.INVALID_DOTTED_AS_NAME, [])
    add(rn.INVALID_IMPORT_FROM_AS_NAME, [])
    add(rn.INVALID_IMPORT_FROM_TARGETS, [])
    add(rn.INVALID_WITH_STMT, [])
    add(rn.INVALID_WITH_STMT_INDENT, [])
    add(rn.INVALID_TRY_STMT, [])
    add(rn.INVALID_EXCEPT_STMT, [])
    add(rn.INVALID_EXCEPT_STAR_STMT, [])
    add(rn.INVALID_FINALLY_STMT, [])
    add(rn.INVALID_EXCEPT_STMT_INDENT, [])
    add(rn.INVALID_EXCEPT_STAR_STMT_INDENT, [])
    add(rn.INVALID_MATCH_STMT, [])
    add(rn.INVALID_CASE_BLOCK, [])
    add(rn.INVALID_AS_PATTERN, [])
    add(rn.INVALID_CLASS_PATTERN, [])
    add(rn.INVALID_CLASS_ARGUMENT_PATTERN, [])
    add(rn.INVALID_IF_STMT, [])
    add(rn.INVALID_ELIF_STMT, [])
    add(rn.INVALID_ELSE_STMT, [])
    add(rn.INVALID_WHILE_STMT, [])
    add(rn.INVALID_FOR_STMT, [])
    add(rn.INVALID_DEF_RAW, [])
    add(rn.INVALID_CLASS_DEF_RAW, [])
    add(rn.INVALID_DOUBLE_STARRED_KVPAIRS, [])
    add(rn.INVALID_KVPAIR, [])
    add(rn.INVALID_STARRED_EXPRESSION_UNPACKING, [])
    add(rn.INVALID_STARRED_EXPRESSION, [])
    add(rn.INVALID_FSTRING_REPLACEMENT_FIELD, [])
    add(rn.INVALID_FSTRING_CONVERSION_CHARACTER, [])
    add(rn.INVALID_TSTRING_REPLACEMENT_FIELD, [])
    add(rn.INVALID_TSTRING_CONVERSION_CHARACTER, [])
    add(rn.INVALID_ARITHMETIC, [])
    add(rn.INVALID_FACTOR, [])
    add(rn.INVALID_TYPE_PARAMS, [])

    return grammar


@dataclass
class _TokenKeyword(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenKeyword({self.location}, {self.value})'


@dataclass
class _TokenName(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenName({self.location}, {self.value})'


@dataclass
class _TokenString(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenString({self.location}, {self.value})'


@dataclass
class _TokenInteger(syntax.Term):
    location: syntax.Location
    value: int

    def repr__tapl(self) -> str:
        return f'TokenInteger({self.location}, {self.value})'


@dataclass
class _TokenFloat(syntax.Term):
    location: syntax.Location
    value: float

    def repr__tapl(self) -> str:
        return f'TokenFloat({self.location}, {self.value})'


@dataclass
class _TokenPunct(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenPunct({self.location}, {self.value})'


@dataclass
class _TokenEndOfText(syntax.Term):
    location: syntax.Location

    def repr__tapl(self) -> str:
        return f'TokenEndOfText({self.location})'


# https://github.com/python/cpython/blob/main/Parser/token.c
_PUNCT_SET = {
    '!',
    '%',
    '&',
    '(',
    ')',
    '*',
    '+',
    ',',
    '-',
    '.',
    '/',
    ':',
    ';',
    '<',
    '=',
    '>',
    '@',
    '[',
    ']',
    '^',
    '{',
    '|',
    '}',
    '~',
    '!=',
    '%=',
    '&=',
    '**',
    '*=',
    '+=',
    '-=',
    '->',
    '//',
    '/=',
    ':=',
    '<<',
    '<=',
    '<>',
    '==',
    '>=',
    '>>',
    '@=',
    '^=',
    '|=',
    '**=',
    '...',
    '//=',
    '<<=',
    '>>=',
}

_KEYWORDS = {
    'and',
    'as',
    'assert',
    'async',
    'await',
    'break',
    'class',
    'continue',
    'def',
    'del',
    'elif',
    'else',
    'except',
    'False',
    'finally',
    'for',
    'from',
    'global',
    'if',
    'import',
    'in',
    'is',
    'lambda',
    'None',
    'nonlocal',
    'not',
    'or',
    'pass',
    'raise',
    'return',
    'True',
    'try',
    'while',
    'with',
    'yield',
}


def _skip_whitespaces(c: Cursor) -> None:
    while not c.is_end() and c.current_char().isspace():
        c.move_to_next()


def _parse_token(c: Cursor) -> syntax.Term:
    _skip_whitespaces(c)
    tracker = c.start_tracker()
    if c.is_end():
        return _TokenEndOfText(tracker.location)

    def scan_name(char: str) -> syntax.Term:
        result = char
        while not c.is_end() and (char := c.current_char()) and (char.isalnum() or char == '_'):
            result += char
            c.move_to_next()
        if result in _KEYWORDS:
            return _TokenKeyword(tracker.location, value=result)
        return _TokenName(tracker.location, value=result)

    def unterminated_string() -> syntax.Term:
        return syntax.ErrorTerm(
            message=f'unterminated string literal (detected at line {tracker.location.end.line}); perhaps you escaped the end quote?',
            location=tracker.location,
        )

    def scan_string() -> syntax.Term:
        result = ''
        if c.is_end():
            return unterminated_string()
        while (char := c.current_char()) != "'":
            result += char
            c.move_to_next()
            if c.is_end():
                return unterminated_string()
        c.move_to_next()  # consume quote
        return _TokenString(tracker.location, result)

    def scan_number(char: str) -> syntax.Term:
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        if not c.is_end() and c.current_char() == '.':
            number_str += '.'
            c.move_to_next()
            if c.is_end() or not c.current_char().isdigit():
                return syntax.ErrorTerm(
                    message='Invalid float literal',
                    location=tracker.location,
                )
            while not c.is_end() and (char := c.current_char()).isdigit():
                number_str += char
                c.move_to_next()
            return _TokenFloat(tracker.location, value=float(number_str))
        return _TokenInteger(tracker.location, value=int(number_str))

    def scan_punct(char: str) -> syntax.Term:
        k = c.clone()
        char2: str | None = None
        char3: str | None = None
        if not k.is_end():
            char2 = k.current_char()
            k.move_to_next()
        if not k.is_end():
            char3 = k.current_char()
            k.move_to_next()
        if char2 is not None:
            if char3 is not None and (temp := char + char2 + char3) in _PUNCT_SET:
                c.copy_from(k)
                return _TokenPunct(tracker.location, value=temp)
            if (temp := char + char2) in _PUNCT_SET:
                c.move_to_next()
                return _TokenPunct(tracker.location, value=temp)
        # single-character punctuation
        return _TokenPunct(tracker.location, value=char)

    char = c.current_char()
    c.move_to_next()
    if char.isalpha() or char == '_':
        return scan_name(char)
    if char == "'":
        return scan_string()
    if char.isdigit():
        return scan_number(char)
    if char in _PUNCT_SET:
        return scan_punct(char)
    # Error
    return tracker.fail()


def _consume_keyword(c: Cursor, keyword: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenKeyword) and term.value == keyword:
        return term
    return t.fail()


def _expect_keyword(c: Cursor, keyword: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenKeyword) and term.value == keyword:
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected "{keyword}", but found {term}', location=t.location)


def _consume_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenName):
        return term
    return t.fail()


def _expect_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenName):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected a name, but found {term}', location=t.location)


def _consume_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenPunct) and term.value in puncts:
        return term
    return t.fail()


def _expect_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, _TokenPunct) and term.value in puncts:
        return term
    puncts_text = ', '.join(f'"{p}"' for p in puncts)
    return t.captured_error or syntax.ErrorTerm(
        message=f'Expected {puncts_text}, but found {term}', location=t.location
    )


def _expect_rule(c: Cursor, rule: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rule)):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected rule "{rule}"', location=t.location)


def _scan_arguments(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    args = []
    if t.validate(first_arg := c.consume_rule(rn.EXPRESSION)):
        args.append(first_arg)
        k = c.clone()
        while t.validate(_consume_punct(k, ',')) and t.validate(arg := _expect_rule(k, rn.EXPRESSION)):
            c.copy_from(k)
            args.append(arg)
    return t.captured_error or syntax.Block(terms=args)


def _parse_primary__attribute(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(value := c.consume_rule(rn.PRIMARY))
        and t.validate(_consume_punct(c, '.'))
        and t.validate(attr := _expect_name(c))
    ):
        return expr.Attribute(t.location, value=value, attr=cast(_TokenName, attr).value, ctx='load')
    return t.fail()


def _parse_primary__call(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(func := c.consume_rule(rn.PRIMARY))
        and t.validate(_consume_punct(c, '('))
        and t.validate(args := _scan_arguments(c))
        and t.validate(_expect_punct(c, ')'))
    ):
        return expr.Call(t.location, func, cast(syntax.Block, args).terms)
    return t.fail()


def _parse_atom__name_load(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule(rn.TOKEN)) and isinstance(token, _TokenName):
        return expr.Name(location=token.location, id=token.value, ctx='load')
    return t.fail()


def _parse_atom__bool(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule(rn.TOKEN)) and isinstance(token, _TokenKeyword):
        location = token.location
        if token.value in ('True', 'False'):
            value = token.value == 'True'
            return expr.BooleanLiteral(location, value=value)
        if token.value == 'None':
            return expr.NoneLiteral(location)
    return t.fail()


def _parse_atom__string(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule(rn.TOKEN)) and isinstance(token, _TokenString):
        return expr.StringLiteral(token.location, value=token.value)
    return t.fail()


def _parse_atom__number(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule(rn.TOKEN)):
        if isinstance(token, _TokenInteger):
            return expr.IntegerLiteral(token.location, value=token.value)
        if isinstance(token, _TokenFloat):
            return expr.FloatLiteral(token.location, value=token.value)
    return t.fail()


def _parse_factor__unary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(op := _consume_punct(c, '+', '-', '~')) and t.validate(factor := _expect_rule(c, rn.FACTOR)):
        return expr.UnaryOp(t.location, cast(_TokenPunct, op).value, factor)
    return t.fail()


def _parse_invalid_factor(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(_consume_punct(c, '+', '-', '~'))
        and t.validate(_consume_keyword(c, 'not'))
        and t.validate(c.consume_rule(rn.FACTOR))
    ):
        return syntax.ErrorTerm(message="'not' after an operator must be parenthesized", location=t.location)
    return t.fail()


def _parse_term__binary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule(rn.TERM))
        and t.validate(op := _consume_punct(c, '*', '/', '//', '%'))
        and t.validate(right := _expect_rule(c, rn.FACTOR))
    ):
        return expr.BinOp(t.location, left, cast(_TokenPunct, op).value, right)
    return t.fail()


def _parse_sum__binary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule(rn.SUM))
        and t.validate(op := _consume_punct(c, '+', '-'))
        and t.validate(right := _expect_rule(c, rn.TERM))
    ):
        return expr.BinOp(t.location, left, cast(_TokenPunct, op).value, right)
    return t.fail()


def _scan_operator(c: Cursor) -> str | None:
    first = c.consume_rule(rn.TOKEN)
    if isinstance(first, _TokenPunct) and first.value in ('==', '!=', '<=', '<', '>=', '>', 'in'):
        return first.value
    if isinstance(first, _TokenKeyword):
        if first.value == 'not':
            second = c.consume_rule(rn.TOKEN)
            if isinstance(second, _TokenKeyword) and second.value == 'in':
                return 'not in'
            return None
        if first.value == 'is':
            second = c.consume_rule(rn.TOKEN)
            if isinstance(second, _TokenKeyword) and second.value == 'not':
                return 'is not'
            return 'is'
    return None


def _parse_comparison(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule(rn.SUM)):
        ops = []
        comparators = []
        k = c.clone()
        while (op := _scan_operator(k)) and t.validate(comparator := _expect_rule(k, rn.SUM)):
            c.copy_from(k)
            ops.append(op)
            comparators.append(comparator)
        if ops:
            return expr.Compare(t.location, left=left, ops=ops, comparators=comparators)
    return t.fail()


def _parse_inversion__not(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(_consume_keyword(c, 'not')) and t.validate(operand := _expect_rule(c, rn.COMPARISON)):
        return expr.BoolNot(location=t.location, operand=operand)
    return t.fail()


def _parse_conjunction__and(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule(rn.INVERSION)):
        values = [left]
        k = c.clone()
        while t.validate(_consume_keyword(k, 'and')) and t.validate(right := _expect_rule(k, rn.INVERSION)):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return expr.BoolOp(location=t.location, op='and', values=values)
    return t.fail()


def _parse_disjunction__or(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule(rn.CONJUNCTION)):
        values = [left]
        k = c.clone()
        while t.validate(_consume_keyword(k, 'or')) and t.validate(right := _expect_rule(k, rn.CONJUNCTION)):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return expr.BoolOp(location=t.location, op='or', values=values)
    return t.fail()


def _parse_assignment(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(name := c.consume_rule(rn.STAR_TARGETS))
        and t.validate(_consume_punct(c, '='))
        and t.validate(value := _expect_rule(c, rn.ANNOTATED_RHS))
        and not t.validate(_consume_punct(c.clone(), '='))
    ):
        return stmt.Assign(t.location, targets=[name], value=value)
    return t.fail()


def _parse_statement__star_expressions(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(value := c.consume_rule(rn.STAR_EXPRESSIONS)):
        if hasattr(value, 'location'):
            location = value.location
        else:
            location = t.location
        return stmt.Expr(location=location, value=value)
    return t.fail()


def _parse_return(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(_consume_keyword(c, 'return')):
        if t.validate(value := c.consume_rule(rn.EXPRESSION)):
            return stmt.Return(t.location, value=value)
        return t.captured_error or stmt.Return(t.location, value=expr.NoneLiteral(t.location))
    return t.fail()


def _rule_parameter_with_type(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(name := _consume_name(c))
        and t.validate(_consume_punct(c, ':'))
        and t.validate(param_type := _expect_rule(c, rn.EXPRESSION))
    ):
        param_name = cast(_TokenName, name).value
        return stmt.Parameter(t.location, name=param_name, type_=syntax.Layers([stmt.Absence(), param_type]))
    return t.fail()


def _rule_parameter_no_type(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(name := _consume_name(c)):
        param_name = cast(_TokenName, name).value
        return stmt.Parameter(t.location, name=param_name, type_=syntax.Layers([stmt.Absence(), stmt.Absence()]))
    return t.fail()


def _scan_parameters(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    params = []
    if t.validate(first_param := c.consume_rule('parameter')):
        params.append(first_param)
        k = c.clone()
        while t.validate(_consume_punct(k, ',')) and t.validate(param := _expect_rule(k, 'parameter')):
            c.copy_from(k)
            params.append(param)
    return t.captured_error or syntax.Block(terms=params)


def _parse_function_def(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(_consume_keyword(c, 'def'))
        and t.validate(func_name := _expect_name(c))
        and t.validate(_expect_punct(c, '('))
        and t.validate(params := _scan_parameters(c))
        and t.validate(_expect_punct(c, ')'))
        and t.validate(_expect_punct(c, ':'))
    ):
        name = cast(_TokenName, func_name).value
        return stmt.FunctionDef(
            location=t.location,
            name=name,
            parameters=cast(syntax.Block, params).terms,
            body=syntax.Block([], delayed=True),
        )
    return t.fail()


def _parse_if_stmt(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(_consume_keyword(c, 'if'))
        and t.validate(test := _expect_rule(c, rn.EXPRESSION))
        and t.validate(_expect_punct(c, ':'))
    ):
        return stmt.If(location=t.location, test=test, body=syntax.Block([], delayed=True), orelse=None)
    return t.fail()


def _parse_else_stmt(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(_consume_keyword(c, 'else')) and t.validate(_expect_punct(c, ':')):
        return stmt.Else(location=t.location, body=syntax.Block([], delayed=True))
    return t.fail()


def _parse_pass(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(_consume_keyword(c, 'pass')):
        return stmt.Pass(location=t.location)
    return t.fail()


def _parse_class_def(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(_consume_keyword(c, 'class'))
        and t.validate(class_name := _expect_name(c))
        and t.validate(_expect_punct(c, ':'))
    ):
        name = cast(_TokenName, class_name).value
        return stmt.ClassDef(location=t.location, name=name, bases=[], body=syntax.Block([], delayed=True))
    return t.fail()


def _parse_start(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(statement := _expect_rule(c, rn.STATEMENT)):
        _skip_whitespaces(c)
        return statement
    return t.fail()


def _parse_star_targets__single(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(target := c.consume_rule(rn.STAR_TARGET)) and not t.validate(_consume_punct(c.clone(), ',')):
        return target
    return t.fail()


def _parse_star_atom__name_store(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule(rn.TOKEN)) and isinstance(token, _TokenName):
        return expr.Name(location=token.location, id=token.value, ctx='store')
    return t.fail()


def _parse_target_with_star_atom__attribute(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(target := c.consume_rule(rn.T_PRIMARY))
        and t.validate(_consume_punct(c, '.'))
        and t.validate(name := _expect_name(c))
        and not t.validate(c.clone().consume_rule(rn.T_LOOKAHEAD))
    ):
        return expr.Attribute(t.location, value=target, attr=cast(_TokenName, name).value, ctx='store')
    return t.fail()


def _parse_t_primary__attribute(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(value := c.consume_rule(rn.T_PRIMARY))
        and t.validate(_consume_punct(c, '.'))
        and t.validate(name := _expect_name(c))
        and t.validate(c.clone().consume_rule(rn.T_LOOKAHEAD))
    ):
        return expr.Attribute(t.location, value=value, attr=cast(_TokenName, name).value, ctx='load')
    return t.fail()


def _parse_t_primary__atom(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(atom := c.consume_rule(rn.ATOM)) and t.validate(c.clone().consume_rule(rn.T_LOOKAHEAD)):
        return atom
    return t.fail()


def _parse_t_lookahead(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := _consume_punct(c, '(', '[', '.')):
        return term
    return t.fail()
