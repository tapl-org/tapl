# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


RULE_NAMES = set()


def declare(rule_key: str) -> str:
    if not rule_key:
        raise ValueError('Rule name cannot be empty.')
    if rule_key.lower() != rule_key:
        raise ValueError('Rule name must be in lowercase.')
    rule_name = f'pythonlike.{rule_key}'
    if rule_name in RULE_NAMES:
        raise ValueError(f'Rule {rule_name} is already defined.')
    RULE_NAMES.add(rule_name)
    return rule_name


# STARTING RULES
# ==============
START = declare('start')

# HELPER RULES
# ============
TOKEN = declare('token')

# GENERAL STATEMENTS
# ==================
STATEMENTS = declare('statements')
STATEMENT = declare('statement')
SINGLE_COMPOUND_STMT = declare('single_compound_stmt')
STATEMENT_NEWLINE = declare('statement_newline')
SIMPLE_STMTS = declare('simple_stmts')
SIMPLE_STMT = declare('simple_stmt')
COMPOUND_STMT = declare('compound_stmt')

# SIMPLE STATEMENTS
# =================
ASSIGNMENT = declare('assignment')
ANNOTATED_RHS = declare('annotated_rhs')
AUGASSIGN = declare('augassign')
RETURN_STMT = declare('return_stmt')
PASS_STMT = declare('pass_stmt')
BREAK_STMT = declare('break_stmt')
CONTINUE_STMT = declare('continue_stmt')
GLOBAL_STMT = declare('global_stmt')
NONLOCAL_STMT = declare('nonlocal_stmt')
DEL_STMT = declare('del_stmt')
YIELD_STMT = declare('yield_stmt')
ASSERT_STMT = declare('assert_stmt')
IMPORT_STMT = declare('import_stmt')

# Import statements
# -----------------
IMPORT_NAME = declare('import_name')
IMPORT_FROM = declare('import_from')
IMPORT_FROM_TARGETS = declare('import_from_targets')
IMPORT_FROM_AS_NAMES = declare('import_from_as_names')
IMPORT_FROM_AS_NAME = declare('import_from_as_name')
DOTTED_AS_NAMES = declare('dotted_as_names')
DOTTED_AS_NAME = declare('dotted_as_name')
DOTTED_NAME = declare('dotted_name')

# COMPOUND STATEMENTS
# ===================

# Common elements
# ---------------
BLOCK = declare('block')
DECORATORS = declare('decorators')

# Class definitions
# -----------------
CLASS_DEF = declare('class_def')
CLASS_DEF_RAW = declare('class_def_raw')

# Function definitions
# --------------------
FUNCTION_DEF = declare('function_def')
FUNCTION_DEF_RAW = declare('function_def_raw')

# Function parameters
# -------------------
PARAMS = declare('params')
PARAMETERS = declare('parameters')
SLASH_NO_DEFAULT = declare('slash_no_default')
SLASH_WITH_DEFAULT = declare('slash_with_default')
STAR_ETC = declare('star_etc')
KWDS = declare('kwds')
PARAM_NO_DEFAULT = declare('param_no_default')
PARAM_NO_DEFAULT_STAR_ANNOTATION = declare('param_no_default_star_annotation')
PARAM_WITH_DEFAULT = declare('param_with_default')
PARAM_MAYBE_DEFAULT = declare('param_maybe_default')
PARAM = declare('param')
PARAM_STAR_ANNOTATION = declare('param_star_annotation')
ANNOTATION = declare('annotation')
STAR_ANNOTATION = declare('star_annotation')
DEFAULT = declare('default')

# If statement
# ------------
IF_STMT = declare('if_stmt')
ELIF_STMT = declare('elif_stmt')
ELSE_BLOCK = declare('else_block')

# While statement
# ---------------
WHILE_STMT = declare('while_stmt')

# For statement
# -------------
FOR_STMT = declare('for_stmt')

# With statement
# --------------
WITH_STMT = declare('with_stmt')
WITH_ITEM = declare('with_item')

# Try statement
# -------------
TRY_STMT = declare('try_stmt')


# Except statement
# ----------------
EXCEPT_BLOCK = declare('except_block')
EXCEPT_STAR_BLOCK = declare('except_star_block')
FINALLY_BLOCK = declare('finally_block')

# Match statement
# ---------------
MATCH_STMT = declare('match_stmt')
SUBJECT_EXPR = declare('subject_expr')
CASE_BLOCK = declare('case_block')
GUARD = declare('guard')
PATTERNS = declare('patterns')
PATTERN = declare('pattern')
AS_PATTERN = declare('as_pattern')
OR_PATTERN = declare('or_pattern')
CLOSED_PATTERN = declare('closed_pattern')
LITERAL_PATTERN = declare('literal_pattern')
LITERAL_EXPR = declare('literal_expr')
COMPLEX_NUMBER = declare('complex_number')
SIGNED_NUMBER = declare('signed_number')
SIGNED_REAL_NUMBER = declare('signed_real_number')
REAL_NUMBER = declare('real_number')
IMAGINARY_NUMBER = declare('imaginary_number')
CAPTURE_PATTERN = declare('capture_pattern')
PATTERN_CAPTURE_TARGET = declare('pattern_capture_target')
WILDCARD_PATTERN = declare('wildcard_pattern')
VALUE_PATTERN = declare('value_pattern')
ATTR = declare('attr')
NAME_OR_ATTR = declare('name_or_attr')
GROUP_PATTERN = declare('group_pattern')
SEQUENCE_PATTERN = declare('sequence_pattern')
OPEN_SEQUENCE_PATTERN = declare('open_sequence_pattern')
MAYBE_SEQUENCE_PATTERN = declare('maybe_sequence_pattern')
MAYBE_STAR_PATTERN = declare('maybe_star_pattern')
STAR_PATTERN = declare('star_pattern')
MAPPING_PATTERN = declare('mapping_pattern')
ITEMS_PATTERN = declare('items_pattern')
KEY_VALUE_PATTERN = declare('key_value_pattern')
DOUBLE_STAR_PATTERN = declare('double_star_pattern')
CLASS_PATTERN = declare('class_pattern')
POSITIONAL_PATTERNS = declare('positional_patterns')
KEYWORD_PATTERNS = declare('keyword_patterns')
KEYWORD_PATTERN = declare('keyword_pattern')

# Type statement
# ---------------
TYPE_ALIAS = declare('type_alias')

# Type parameter declaration
# --------------------------
TYPE_PARAMS = declare('type_params')
TYPE_PARAM_SEQ = declare('type_param_seq')
TYPE_PARAM = declare('type_param')
TYPE_PARAM_BOUND = declare('type_param_bound')
TYPE_PARAM_DEFAULT = declare('type_param_default')
TYPE_PARAM_STARRED_DEFAULT = declare('type_param_starred_default')

# EXPRESSIONS
# -----------
EXPRESSIONS = declare('expressions')
EXPRESSION = declare('expression')
YIELD_EXPR = declare('yield_expr')
STAR_EXPRESSIONS = declare('star_expressions')
STAR_EXPRESSION = declare('star_expression')
STAR_NAMED_EXPRESSIONS = declare('star_named_expressions')
STAR_NAMED_EXPRESSION = declare('star_named_expression')
ASSIGNMENT_EXPRESSION = declare('assignment_expression')
NAMED_EXPRESSION = declare('named_expression')
DISJUNCTION = declare('disjunction')
CONJUNCTION = declare('conjunction')
INVERSION = declare('inversion')

# Comparison operators
# --------------------
COMPARISON = declare('comparison')
COMPARE_OP_BITWISE_OR_PAIR = declare('compare_op_bitwise_or_pair')
EQ_BITWISE_OR = declare('eq_bitwise_or')
NOTEQ_BITWISE_OR = declare('noteq_bitwise_or')
LTE_BITWISE_OR = declare('lte_bitwise_or')
LT_BITWISE_OR = declare('lt_bitwise_or')
GTE_BITWISE_OR = declare('gte_bitwise_or')
GT_BITWISE_OR = declare('gt_bitwise_or')
NOTIN_BITWISE_OR = declare('notin_bitwise_or')
IN_BITWISE_OR = declare('in_bitwise_or')
ISNOT_BITWISE_OR = declare('isnot_bitwise_or')
IS_BITWISE_OR = declare('is_bitwise_or')

# Bitwise operators
# -----------------
BITWISE_OR = declare('bitwise_or')
BITWISE_XOR = declare('bitwise_xor')
BITWISE_AND = declare('bitwise_and')
SHIFT_EXPR = declare('shift_expr')

# Arithmetic operators
# --------------------
SUM = declare('sum')
TERM = declare('term')
FACTOR = declare('factor')
POWER = declare('power')

# Primary elements
# ----------------
AWAIT_PRIMARY = declare('await_primary')
PRIMARY = declare('primary')
SLICES = declare('slices')
SLICE = declare('slice')
ATOM = declare('atom')
GROUP = declare('group')

# Lambda functions
# ----------------
LAMBDEF = declare('lambdef')
LAMBDA_PARAMS = declare('lambda_params')
LAMBDA_PARAMETERS = declare('lambda_parameters')
LAMBDA_SLASH_NO_DEFAULT = declare('lambda_slash_no_default')
LAMBDA_SLASH_WITH_DEFAULT = declare('lambda_slash_with_default')
LAMBDA_STAR_ETC = declare('lambda_star_etc')
LAMBDA_KWDS = declare('lambda_kwds')
LAMBDA_PARAM_NO_DEFAULT = declare('lambda_param_no_default')
LAMBDA_PARAM_WITH_DEFAULT = declare('lambda_param_with_default')
LAMBDA_PARAM_MAYBE_DEFAULT = declare('lambda_param_maybe_default')

# LITERALS
# ========
FSTRING_MIDDLE = declare('fstring_middle')
FSTRING_REPLACEMENT_FIELD = declare('fstring_replacement_field')
FSTRING_CONVERSION = declare('fstring_conversion')
FSTRING_FULL_FORMAT_SPEC = declare('fstring_full_format_spec')
FSTRING_FORMAT_SPEC = declare('fstring_format_spec')
FSTRING = declare('fstring')
TSTRING_FORMAT_SPEC_REPLACEMENT_FIELD = declare('tstring_format_spec_replacement_field')
TSTRING_FORMAT_SPEC = declare('tstring_format_spec')
TSTRING_FULL_FORMAT_SPEC = declare('tstring_full_format_spec')
TSTRING_REPLACEMENT_FIELD = declare('tstring_replacement_field')
TSTRING_MIDDLE = declare('tstring_middle')
TSTRING = declare('tstring')
STRING = declare('string')
STRINGS = declare('strings')
LIST = declare('list')
TUPLE = declare('tuple')
SET = declare('set')
# Dicts
# -----
DICT = declare('dict')
DOUBLE_STARRED_KVPAIRS = declare('double_starred_kvpairs')
DOUBLE_STARRED_KVPAIR = declare('double_starred_kvpair')
KVPAIR = declare('kvpair')

# Comprehensions & Generators
# ---------------------------
FOR_IF_CLAUSES = declare('for_if_clauses')
FOR_IF_CLAUSE = declare('for_if_clause')
LISTCOMP = declare('listcomp')
SETCOMP = declare('setcomp')
GENEXP = declare('genexp')
DICTCOMP = declare('dictcomp')

# FUNCTION CALL ARGUMENTS
# =======================
ARGUMENTS = declare('arguments')
ARGS = declare('args')
KWARGS = declare('kwargs')
STARRED_EXPRESSION = declare('starred_expression')
KWARG_OR_STARRED = declare('kwarg_or_starred')
KWARG_OR_DOUBLE_STARRED = declare('kwarg_or_double_starred')

# ASSIGNMENT TARGETS
# ==================

# Generic targets
# ---------------
STAR_TARGETS = declare('star_targets')
STAR_TARGETS_LIST_SEQ = declare('star_targets_list_seq')
STAR_TARGETS_TUPLE_SEQ = declare('star_targets_tuple_seq')
STAR_TARGET = declare('star_target')
TARGET_WITH_STAR_ATOM = declare('target_with_star_atom')
STAR_ATOM = declare('star_atom')
SINGLE_TARGET = declare('single_target')
SINGLE_SUBSCRIPT_ATTRIBUTE_TARGET = declare('single_subscript_attribute_target')
T_PRIMARY = declare('t_primary')
T_LOOKAHEAD = declare('t_lookahead')

# Targets for del statements
# --------------------------
DEL_TARGETS = declare('del_targets')
DEL_TARGET = declare('del_target')
DEL_T_ATOM = declare('del_t_atom')

# TYPING ELEMENTS
# ---------------
TYPE_EXPRESSIONS = declare('type_expressions')
FUNC_TYPE_COMMENT = declare('func_type_comment')

# INVALID RULES
# =============
INVALID_ARGUMENTS = declare('invalid_arguments')
EXPRESSION_WITHOUT_INVALID = declare('expression_without_invalid')
INVALID_LEGACY_EXPRESSION = declare('invalid_legacy_expression')
INVALID_TYPE_PARAM = declare('invalid_type_param')
INVALID_EXPRESSION = declare('invalid_expression')
INVALID_NAMED_EXPRESSION = declare('invalid_named_expression')
INVALID_ASSIGNMENT = declare('invalid_assignment')
INVALID_ANN_ASSIGN_TARGET = declare('invalid_ann_assign_target')
INVALID_RAISE_STMT = declare('invalid_raise_stmt')
INVALID_DEL_STMT = declare('invalid_del_stmt')
INVALID_BLOCK = declare('invalid_block')
INVALID_COMPREHENSION = declare('invalid_comprehension')
INVALID_DICT_COMPREHENSION = declare('invalid_dict_comprehension')
INVALID_PARAMETERS = declare('invalid_parameters')
INVALID_DEFAULT = declare('invalid_default')
INVALID_STAR_ETC = declare('invalid_star_etc')
INVALID_KWDS = declare('invalid_kwds')
INVALID_PARAMETERS_HELPER = declare('invalid_parameters_helper')
INVALID_LAMBDA_PARAMETERS = declare('invalid_lambda_parameters')
INVALID_LAMBDA_PARAMETERS_HELPER = declare('invalid_lambda_parameters_helper')
INVALID_LAMBDA_STAR_ETC = declare('invalid_lambda_star_etc')
INVALID_LAMBDA_KWDS = declare('invalid_lambda_kwds')
INVALID_DOUBLE_TYPE_COMMENTS = declare('invalid_double_type_comments')
INVALID_WITH_ITEM = declare('invalid_with_item')
INVALID_FOR_IF_CLAUSE = declare('invalid_for_if_clause')
INVALID_FOR_TARGET = declare('invalid_for_target')
INVALID_GROUP = declare('invalid_group')
INVALID_IMPORT = declare('invalid_import')
INVALID_DOTTED_AS_NAME = declare('invalid_dotted_as_name')
INVALID_IMPORT_FROM_AS_NAME = declare('invalid_import_from_as_name')
INVALID_IMPORT_FROM_TARGETS = declare('invalid_import_from_targets')
INVALID_WITH_STMT = declare('invalid_with_stmt')
INVALID_WITH_STMT_INDENT = declare('invalid_with_stmt_indent')
INVALID_TRY_STMT = declare('invalid_try_stmt')
INVALID_EXCEPT_STMT = declare('invalid_except_stmt')
INVALID_EXCEPT_STAR_STMT = declare('invalid_except_star_stmt')
INVALID_FINALLY_STMT = declare('invalid_finally_stmt')
INVALID_EXCEPT_STMT_INDENT = declare('invalid_except_stmt_indent')
INVALID_EXCEPT_STAR_STMT_INDENT = declare('invalid_except_star_stmt_indent')
INVALID_MATCH_STMT = declare('invalid_match_stmt')
INVALID_CASE_BLOCK = declare('invalid_case_block')
INVALID_AS_PATTERN = declare('invalid_as_pattern')
INVALID_CLASS_PATTERN = declare('invalid_class_pattern')
INVALID_CLASS_ARGUMENT_PATTERN = declare('invalid_class_argument_pattern')
INVALID_IF_STMT = declare('invalid_if_stmt')
INVALID_ELIF_STMT = declare('invalid_elif_stmt')
INVALID_ELSE_STMT = declare('invalid_else_stmt')
INVALID_WHILE_STMT = declare('invalid_while_stmt')
INVALID_FOR_STMT = declare('invalid_for_stmt')
INVALID_DEF_RAW = declare('invalid_def_raw')
INVALID_CLASS_DEF_RAW = declare('invalid_class_def_raw')
INVALID_DOUBLE_STARRED_KVPAIRS = declare('invalid_double_starred_kvpairs')
INVALID_KVPAIR = declare('invalid_kvpair')
INVALID_STARRED_EXPRESSION_UNPACKING = declare('invalid_starred_expression_unpacking')
INVALID_STARRED_EXPRESSION = declare('invalid_starred_expression')
INVALID_FSTRING_REPLACEMENT_FIELD = declare('invalid_fstring_replacement_field')
INVALID_FSTRING_CONVERSION_CHARACTER = declare('invalid_fstring_conversion_character')
INVALID_TSTRING_REPLACEMENT_FIELD = declare('invalid_tstring_replacement_field')
INVALID_TSTRING_CONVERSION_CHARACTER = declare('invalid_tstring_conversion_character')
INVALID_ARITHMETIC = declare('invalid_arithmetic')
INVALID_FACTOR = declare('invalid_factor')
INVALID_TYPE_PARAMS = declare('invalid_type_params')
