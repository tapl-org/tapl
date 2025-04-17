# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import codegen_setting


def test_default_codegen_setting():
    # Verify the default CodegenSetting
    current_setting = codegen_setting.get_current()
    assert current_setting.variable_handling == codegen_setting.VariableHandling.NATIVE
    assert current_setting.scope_level == 0


def test_set_current():
    # Verify that set_current temporarily changes the CodegenSetting
    new_setting = codegen_setting.CodegenSetting(
        variable_handling=codegen_setting.VariableHandling.MANUAL, scope_level=1
    )
    with codegen_setting.set_current(new_setting):
        current_setting = codegen_setting.get_current()
        assert current_setting.variable_handling == codegen_setting.VariableHandling.MANUAL
        assert current_setting.scope_level == 1

    # Ensure the setting is restored after the context
    current_setting = codegen_setting.get_current()
    assert current_setting.variable_handling == codegen_setting.VariableHandling.NATIVE
    assert current_setting.scope_level == 0


def test_new_inner_scope():
    # Verify that new_inner_scope increments the scope level
    initial_setting = codegen_setting.get_current()
    assert initial_setting.scope_level == 0

    with codegen_setting.new_inner_scope():
        inner_setting = codegen_setting.get_current()
        assert inner_setting.scope_level == 1
        assert inner_setting.variable_handling == codegen_setting.VariableHandling.NATIVE

        with codegen_setting.new_inner_scope():
            deeper_setting = codegen_setting.get_current()
            assert deeper_setting.scope_level == 2
            assert deeper_setting.variable_handling == codegen_setting.VariableHandling.NATIVE

    # Ensure the setting is restored after the context
    restored_setting = codegen_setting.get_current()
    assert restored_setting.scope_level == 0
    assert restored_setting.variable_handling == codegen_setting.VariableHandling.NATIVE
