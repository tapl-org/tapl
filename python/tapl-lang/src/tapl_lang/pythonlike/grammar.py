# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.core.parser import GrammarRuleMap, ParseFunction, route

RULES: GrammarRuleMap = {}


def define(rule_key: str, ordered_functions: list[ParseFunction | str]) -> str:
    if not rule_key:
        raise ValueError('Rule name cannot be empty.')
    if rule_key.lower() != rule_key:
        raise ValueError('Rule name must be in lowercase.')
    rule_name = f'pythonlike.{rule_key}'
    if rule_name in RULES:
        raise ValueError(f'Rule {rule_name} is already defined.')
    RULES[rule_name] = [route(fn) if isinstance(fn, str) else fn for fn in ordered_functions]
    return rule_name


# GENERAL STATEMENTS
# ==================
STATEMENTS = define('statements', [])
STATEMENT = define('statement', [])
SINGLE_COMPOUND_STMT = define('single_compound_stmt', [])
STATEMENT_NEWLINE = define('statement_newline', [])
SIMPLE_STMTS = define('simple_stmts', [])
SIMPLE_STMT = define('simple_stmt', [])
COMPOUND_STMT = define('compound_stmt', [])

# SIMPLE STATEMENTS
# =================
ASSIGNMENT = define('assignment', [])
ANNOTATED_RHS = define('annotated_rhs', [])
AUGASSIGN = define('augassign', [])
RETURN_STMT = define('return_stmt', [])
PASS_STMT = define('pass_stmt', [])
BREAK_STMT = define('break_stmt', [])
CONTINUE_STMT = define('continue_stmt', [])
GLOBAL_STMT = define('global_stmt', [])
NONLOCAL_STMT = define('nonlocal_stmt', [])
DEL_STMT = define('del_stmt', [])
YIELD_STMT = define('yield_stmt', [])
ASSERT_STMT = define('assert_stmt', [])
IMPORT_STMT = define('import_stmt', [])

# Import statements
# -----------------
IMPORT_NAME = define('import_name', [])
IMPORT_FROM = define('import_from', [])
IMPORT_FROM_TARGETS = define('import_from_targets', [])
IMPORT_FROM_AS_NAMES = define('import_from_as_names', [])
IMPORT_FROM_AS_NAME = define('import_from_as_name', [])
DOTTED_AS_NAMES = define('dotted_as_names', [])
DOTTED_AS_NAME = define('dotted_as_name', [])
DOTTED_NAME = define('dotted_name', [])

# COMPOUND STATEMENTS
# ===================

# Common elements
# ---------------
BLOCK = define('block', [])
DECORATORS = define('decorators', [])

# Class definitions
# -----------------
CLASS_DEF = define('class_def', [])
CLASS_DEF_RAW = define('class_def_raw', [])

# Function definitions
# --------------------
FUNCTION_DEF = define('function_def', [])
FUNCTION_DEF_RAW = define('function_def_raw', [])

# Function parameters
# -------------------
PARAMS = define('params', [])
PARAMETERS = define('parameters', [])
SLASH_NO_DEFAULT = define('slash_no_default', [])
SLASH_WITH_DEFAULT = define('slash_with_default', [])
STAR_ETC = define('star_etc', [])
KWDS = define('kwds', [])
PARAM_NO_DEFAULT = define('param_no_default', [])
PARAM_NO_DEFAULT_STAR_ANNOTATION = define('param_no_default_star_annotation', [])
PARAM_WITH_DEFAULT = define('param_with_default', [])
PARAM_MAYBE_DEFAULT = define('param_maybe_default', [])
PARAM = define('param', [])
PARAM_STAR_ANNOTATION = define('param_star_annotation', [])
ANNOTATION = define('annotation', [])
STAR_ANNOTATION = define('star_annotation', [])
DEFAULT = define('default', [])

# If statement
# ------------
IF_STMT = define('if_stmt', [])
ELIF_STMT = define('elif_stmt', [])
ELSE_BLOCK = define('else_block', [])

# While statement
# ---------------
WHILE_STMT = define('while_stmt', [])

# For statement
# -------------
FOR_STMT = define('for_stmt', [])

# With statement
# --------------
WITH_STMT = define('with_stmt', [])
WITH_ITEM = define('with_item', [])

# Try statement
# -------------
TRY_STMT = define('try_stmt', [])


# Except statement
# ----------------
EXCEPT_BLOCK = define('except_block', [])
EXCEPT_STAR_BLOCK = define('except_star_block', [])
FINALLY_BLOCK = define('finally_block', [])

# Match statement
# ---------------
MATCH_STMT = define('match_stmt', [])
SUBJECT_EXPR = define('subject_expr', [])
CASE_BLOCK = define('case_block', [])
GUARD = define('guard', [])
PATTERNS = define('patterns', [])
PATTERN = define('pattern', [])
AS_PATTERN = define('as_pattern', [])
OR_PATTERN = define('or_pattern', [])
CLOSED_PATTERN = define('closed_pattern', [])
LITERAL_PATTERN = define('literal_pattern', [])
LITERAL_EXPR = define('literal_expr', [])
COMPLEX_NUMBER = define('complex_number', [])
SIGNED_NUMBER = define('signed_number', [])
SIGNED_REAL_NUMBER = define('signed_real_number', [])
REAL_NUMBER = define('real_number', [])
IMAGINARY_NUMBER = define('imaginary_number', [])
CAPTURE_PATTERN = define('capture_pattern', [])
PATTERN_CAPTURE_TARGET = define('pattern_capture_target', [])
WILDCARD_PATTERN = define('wildcard_pattern', [])
VALUE_PATTERN = define('value_pattern', [])
ATTR = define('attr', [])
NAME_OR_ATTR = define('name_or_attr', [])
GROUP_PATTERN = define('group_pattern', [])
SEQUENCE_PATTERN = define('sequence_pattern', [])
OPEN_SEQUENCE_PATTERN = define('open_sequence_pattern', [])
MAYBE_SEQUENCE_PATTERN = define('maybe_sequence_pattern', [])
MAYBE_STAR_PATTERN = define('maybe_star_pattern', [])
STAR_PATTERN = define('star_pattern', [])
MAPPING_PATTERN = define('mapping_pattern', [])
ITEMS_PATTERN = define('items_pattern', [])
KEY_VALUE_PATTERN = define('key_value_pattern', [])
DOUBLE_STAR_PATTERN = define('double_star_pattern', [])
CLASS_PATTERN = define('class_pattern', [])
POSITIONAL_PATTERNS = define('positional_patterns', [])
KEYWORD_PATTERNS = define('keyword_patterns', [])
KEYWORD_PATTERN = define('keyword_pattern', [])

# Type statement
# ---------------
TYPE_ALIAS = define('type_alias', [])

# Type parameter declaration
# --------------------------
TYPE_PARAMS = define('type_params', [])
TYPE_PARAM_SEQ = define('type_param_seq', [])
TYPE_PARAM = define('type_param', [])
TYPE_PARAM_BOUND = define('type_param_bound', [])
TYPE_PARAM_DEFAULT = define('type_param_default', [])
TYPE_PARAM_STARRED_DEFAULT = define('type_param_starred_default', [])

# EXPRESSIONS
# -----------
EXPRESSIONS = define('expressions', [])
EXPRESSION = define('expression', [])
YIELD_EXPR = define('yield_expr', [])
STAR_EXPRESSIONS = define('star_expressions', [])
STAR_EXPRESSION = define('star_expression', [])
STAR_NAMED_EXPRESSIONS = define('star_named_expressions', [])
STAR_NAMED_EXPRESSION = define('star_named_expression', [])
ASSIGNMENT_EXPRESSION = define('assignment_expression', [])
NAMED_EXPRESSION = define('named_expression', [])
DISJUNCTION = define('disjunction', [])
CONJUNCTION = define('conjunction', [])
INVERSION = define('inversion', [])

# Comparison operators
# --------------------
COMPARISON = define('comparison', [])
COMPARE_OP_BITWISE_OR_PAIR = define('compare_op_bitwise_or_pair', [])
EQ_BITWISE_OR = define('eq_bitwise_or', [])
NOTEQ_BITWISE_OR = define('noteq_bitwise_or', [])
LTE_BITWISE_OR = define('lte_bitwise_or', [])
LT_BITWISE_OR = define('lt_bitwise_or', [])
GTE_BITWISE_OR = define('gte_bitwise_or', [])
GT_BITWISE_OR = define('gt_bitwise_or', [])
NOTIN_BITWISE_OR = define('notin_bitwise_or', [])
IN_BITWISE_OR = define('in_bitwise_or', [])
ISNOT_BITWISE_OR = define('isnot_bitwise_or', [])
IS_BITWISE_OR = define('is_bitwise_or', [])

# Bitwise operators
# -----------------
BITWISE_OR = define('bitwise_or', [])
BITWISE_XOR = define('bitwise_xor', [])
BITWISE_AND = define('bitwise_and', [])
SHIFT_EXPR = define('shift_expr', [])

# Arithmetic operators
# --------------------
SUM = define('sum', [])
TERM = define('term', [])
FACTOR = define('factor', [])
POWER = define('power', [])

# Primary elements
# ----------------
AWAIT_PRIMARY = define('await_primary', [])
PRIMARY = define('primary', [])
SLICES = define('slices', [])
SLICE = define('slice', [])
ATOM = define('atom', [])
GROUP = define('group', [])

# Lambda functions
# ----------------
LAMBDEF = define('lambdef', [])
LAMBDA_PARAMS = define('lambda_params', [])
LAMBDA_PARAMETERS = define('lambda_parameters', [])
LAMBDA_SLASH_NO_DEFAULT = define('lambda_slash_no_default', [])
LAMBDA_SLASH_WITH_DEFAULT = define('lambda_slash_with_default', [])
LAMBDA_STAR_ETC = define('lambda_star_etc', [])
LAMBDA_KWDS = define('lambda_kwds', [])
LAMBDA_PARAM_NO_DEFAULT = define('lambda_param_no_default', [])
LAMBDA_PARAM_WITH_DEFAULT = define('lambda_param_with_default', [])
LAMBDA_PARAM_MAYBE_DEFAULT = define('lambda_param_maybe_default', [])

# LITERALS
# ========
FSTRING_MIDDLE = define('fstring_middle', [])
FSTRING_REPLACEMENT_FIELD = define('fstring_replacement_field', [])
FSTRING_CONVERSION = define('fstring_conversion', [])
FSTRING_FULL_FORMAT_SPEC = define('fstring_full_format_spec', [])
FSTRING_FORMAT_SPEC = define('fstring_format_spec', [])
FSTRING = define('fstring', [])
TSTRING_FORMAT_SPEC_REPLACEMENT_FIELD = define('tstring_format_spec_replacement_field', [])
TSTRING_FORMAT_SPEC = define('tstring_format_spec', [])
TSTRING_FULL_FORMAT_SPEC = define('tstring_full_format_spec', [])
TSTRING_REPLACEMENT_FIELD = define('tstring_replacement_field', [])
TSTRING_MIDDLE = define('tstring_middle', [])
TSTRING = define('tstring', [])
STRING = define('string', [])
STRINGS = define('strings', [])
LIST = define('list', [])
TUPLE = define('tuple', [])
SET = define('set', [])
# Dicts
# -----
DICT = define('dict', [])
DOUBLE_STARRED_KVPAIRS = define('double_starred_kvpairs', [])
DOUBLE_STARRED_KVPAIR = define('double_starred_kvpair', [])
KVPAIR = define('kvpair', [])

# Comprehensions & Generators
# ---------------------------
FOR_IF_CLAUSES = define('for_if_clauses', [])
FOR_IF_CLAUSE = define('for_if_clause', [])
LISTCOMP = define('listcomp', [])
SETCOMP = define('setcomp', [])
GENEXP = define('genexp', [])
DICTCOMP = define('dictcomp', [])

# FUNCTION CALL ARGUMENTS
# =======================
ARGUMENTS = define('arguments', [])
ARGS = define('args', [])
KWARGS = define('kwargs', [])
STARRED_EXPRESSION = define('starred_expression', [])
KWARG_OR_STARRED = define('kwarg_or_starred', [])
KWARG_OR_DOUBLE_STARRED = define('kwarg_or_double_starred', [])

# ASSIGNMENT TARGETS
# ==================

# Generic targets
# ---------------
STAR_TARGETS = define('star_targets', [])
STAR_TARGETS_LIST_SEQ = define('star_targets_list_seq', [])
STAR_TARGETS_TUPLE_SEQ = define('star_targets_tuple_seq', [])
STAR_TARGET = define('star_target', [])
TARGET_WITH_STAR_ATOM = define('target_with_star_atom', [])
STAR_ATOM = define('star_atom', [])
SINGLE_TARGET = define('single_target', [])
SINGLE_SUBSCRIPT_ATTRIBUTE_TARGET = define('single_subscript_attribute_target', [])
T_PRIMARY = define('t_primary', [])
T_LOOKAHEAD = define('t_lookahead', [])

# Targets for del statements
# --------------------------
DEL_TARGETS = define('del_targets', [])
DEL_TARGET = define('del_target', [])
DEL_T_ATOM = define('del_t_atom', [])

# TYPING ELEMENTS
# ---------------
TYPE_EXPRESSIONS = define('type_expressions', [])
FUNC_TYPE_COMMENT = define('func_type_comment', [])

# INVALID RULES
# =============
INVALID_ARGUMENTS = define('invalid_arguments', [])
EXPRESSION_WITHOUT_INVALID = define('expression_without_invalid', [])
INVALID_LEGACY_EXPRESSION = define('invalid_legacy_expression', [])
INVALID_TYPE_PARAM = define('invalid_type_param', [])
INVALID_EXPRESSION = define('invalid_expression', [])
INVALID_NAMED_EXPRESSION = define('invalid_named_expression', [])
INVALID_ASSIGNMENT = define('invalid_assignment', [])
INVALID_ANN_ASSIGN_TARGET = define('invalid_ann_assign_target', [])
INVALID_RAISE_STMT = define('invalid_raise_stmt', [])
INVALID_DEL_STMT = define('invalid_del_stmt', [])
INVALID_BLOCK = define('invalid_block', [])
INVALID_COMPREHENSION = define('invalid_comprehension', [])
INVALID_DICT_COMPREHENSION = define('invalid_dict_comprehension', [])
INVALID_PARAMETERS = define('invalid_parameters', [])
INVALID_DEFAULT = define('invalid_default', [])
INVALID_STAR_ETC = define('invalid_star_etc', [])
INVALID_KWDS = define('invalid_kwds', [])
INVALID_PARAMETERS_HELPER = define('invalid_parameters_helper', [])
INVALID_LAMBDA_PARAMETERS = define('invalid_lambda_parameters', [])
INVALID_LAMBDA_PARAMETERS_HELPER = define('invalid_lambda_parameters_helper', [])
INVALID_LAMBDA_STAR_ETC = define('invalid_lambda_star_etc', [])
INVALID_LAMBDA_KWDS = define('invalid_lambda_kwds', [])
INVALID_DOUBLE_TYPE_COMMENTS = define('invalid_double_type_comments', [])
INVALID_WITH_ITEM = define('invalid_with_item', [])
INVALID_FOR_IF_CLAUSE = define('invalid_for_if_clause', [])
INVALID_FOR_TARGET = define('invalid_for_target', [])
INVALID_GROUP = define('invalid_group', [])
INVALID_IMPORT = define('invalid_import', [])
INVALID_DOTTED_AS_NAME = define('invalid_dotted_as_name', [])
INVALID_IMPORT_FROM_AS_NAME = define('invalid_import_from_as_name', [])
INVALID_IMPORT_FROM_TARGETS = define('invalid_import_from_targets', [])
INVALID_WITH_STMT = define('invalid_with_stmt', [])
INVALID_WITH_STMT_INDENT = define('invalid_with_stmt_indent', [])
INVALID_TRY_STMT = define('invalid_try_stmt', [])
INVALID_EXCEPT_STMT = define('invalid_except_stmt', [])
INVALID_EXCEPT_STAR_STMT = define('invalid_except_star_stmt', [])
INVALID_FINALLY_STMT = define('invalid_finally_stmt', [])
INVALID_EXCEPT_STMT_INDENT = define('invalid_except_stmt_indent', [])
INVALID_EXCEPT_STAR_STMT_INDENT = define('invalid_except_star_stmt_indent', [])
INVALID_MATCH_STMT = define('invalid_match_stmt', [])
INVALID_CASE_BLOCK = define('invalid_case_block', [])
INVALID_AS_PATTERN = define('invalid_as_pattern', [])
INVALID_CLASS_PATTERN = define('invalid_class_pattern', [])
INVALID_CLASS_ARGUMENT_PATTERN = define('invalid_class_argument_pattern', [])
INVALID_IF_STMT = define('invalid_if_stmt', [])
INVALID_ELIF_STMT = define('invalid_elif_stmt', [])
INVALID_ELSE_STMT = define('invalid_else_stmt', [])
INVALID_WHILE_STMT = define('invalid_while_stmt', [])
INVALID_FOR_STMT = define('invalid_for_stmt', [])
INVALID_DEF_RAW = define('invalid_def_raw', [])
INVALID_CLASS_DEF_RAW = define('invalid_class_def_raw', [])
INVALID_DOUBLE_STARRED_KVPAIRS = define('invalid_double_starred_kvpairs', [])
INVALID_KVPAIR = define('invalid_kvpair', [])
INVALID_STARRED_EXPRESSION_UNPACKING = define('invalid_starred_expression_unpacking', [])
INVALID_STARRED_EXPRESSION = define('invalid_starred_expression', [])
INVALID_FSTRING_REPLACEMENT_FIELD = define('invalid_fstring_replacement_field', [])
INVALID_FSTRING_CONVERSION_CHARACTER = define('invalid_fstring_conversion_character', [])
INVALID_TSTRING_REPLACEMENT_FIELD = define('invalid_tstring_replacement_field', [])
INVALID_TSTRING_CONVERSION_CHARACTER = define('invalid_tstring_conversion_character', [])
INVALID_ARITHMETIC = define('invalid_arithmetic', [])
INVALID_FACTOR = define('invalid_factor', [])
INVALID_TYPE_PARAMS = define('invalid_type_params', [])
