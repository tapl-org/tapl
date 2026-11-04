# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The driver opcodes, inside and outside a driver session."""

import os
import pathlib

import pytest

from oymo.oymomo import driver, reduction, strategy, terms
from oymo.oymomo.grammar import parse

HEADER = 'language oymomo\n'


def write(top: pathlib.Path, path: str, text: str) -> None:
    file = top / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding='utf-8')


def normal(source):
    return strategy.normalize(reduction.resolve(parse(source)))


def path(text: str) -> terms.ByteArray:
    return terms.ByteArray.from_str(text)


def test_read_a_file_with_one_layer(tmp_path):
    write(tmp_path, 'a.oymo', HEADER + '{f = λx. x}\n')
    with driver.session(str(tmp_path)):
        low = normal("'driver.read_low' 'a.oymo'")
        high = normal("'driver.read_high' 'a.oymo'")
    assert low == normal('{f = λx. x}')
    assert high is low


def test_read_a_file_with_two_layers(tmp_path):
    write(tmp_path, 'dir/b.oymo', HEADER + '{a = [01] : [02], b = λx. x}\n')
    with driver.session(str(tmp_path)):
        assert normal("'driver.read_low' 'dir/b.oymo'") == normal('{a = [01], b = λx. x}')
        assert normal("'driver.read_high' 'dir/b.oymo'") == normal('{a = [02], b = λx. x}')


def test_a_read_file_keeps_its_own_tags(tmp_path):
    write(tmp_path, 'a.oymo', HEADER + '{v = [01]}\n')
    with driver.session(str(tmp_path)):
        read = normal("'driver.read_low' 'a.oymo'")
    assert read.tag.file.path == os.path.join(str(tmp_path), 'a.oymo')
    assert read.fields[0].value.tag.file.position(read.fields[0].value.tag.start) == (2, 6)


def test_a_free_name_is_reported_in_the_read_file(tmp_path):
    write(tmp_path, 'a.oymo', HEADER + '{f = λx. y}\n')
    with driver.session(str(tmp_path)) as build:
        term = normal("'driver.read_low' 'a.oymo'")
    assert reduction.reduce(term) is term
    [(message, tag)] = build.errors
    assert message == "Unknown name 'y'."
    assert tag.file.path == os.path.join(str(tmp_path), 'a.oymo')
    assert tag.file.position(tag.start) == (2, len('{f = λx. '.encode()) + 1)
    with pytest.raises(driver.DriverError) as info:
        build.check()
    assert info.value.message == message


def test_each_path_is_read_once(tmp_path):
    write(tmp_path, 'a.oymo', HEADER + '{v = [01]}\n')
    with driver.session(str(tmp_path)) as build:
        first = build.apply('driver.read_low', path('a.oymo'))
        write(tmp_path, 'a.oymo', HEADER + '{v = [02]}\n')
        assert build.apply('driver.read_low', path('a.oymo')) is first
        assert build.apply('driver.read_bytes', path('a.oymo')) == terms.ByteArray((HEADER + '{v = [01]}\n').encode())
    assert build.paths == ['a.oymo']


@pytest.mark.parametrize(
    ('bad', 'message'),
    [
        ('/etc/passwd', "'/etc/passwd' is absolute; a read path is relative to the top of the virtual directory."),
        ('../a.oymo', "'../a.oymo' is not a read path"),
        ('dir/../a.oymo', "'dir/../a.oymo' is not a read path"),
        ('./a.oymo', "'./a.oymo' is not a read path"),
        ('dir//a.oymo', "'dir//a.oymo' is not a read path"),
        ('', "'' is not a read path"),
        ('missing.oymo', "could not find oymo file 'missing.oymo'"),
        ('dir', "Cannot read 'dir': Is a directory."),
    ],
)
def test_bad_paths_are_errors_at_the_path(tmp_path, bad, message):
    (tmp_path / 'dir').mkdir()
    with driver.session(str(tmp_path)) as build:
        term = normal(f"'driver.read_low' '{bad}'")
    assert reduction.reduce(term) is term
    [(error, tag)] = build.errors
    assert error.startswith(message)
    assert tag is term.argument.tag


def test_a_link_may_not_leave_the_top(tmp_path):
    top = tmp_path / 'top'
    top.mkdir()
    write(tmp_path, 'outside.oymo', HEADER + '{}\n')
    (top / 'link.oymo').symlink_to(tmp_path / 'outside.oymo')
    with driver.session(str(top)) as build:
        normal("'driver.read_low' 'link.oymo'")
    assert build.errors[0][0] == "'link.oymo' leaves the top of the virtual directory."


def test_a_mount_shows_a_host_folder(tmp_path):
    top, math = tmp_path / 'top', tmp_path / 'math'
    write(top, 'lib/a.oymo', HEADER + '{f = [01]}\n')
    write(math, 'unit.h.oymo', HEADER + '{f = [02]}\n')
    with driver.session(str(top), mounts={'lib/math': str(math)}) as build:
        assert normal("'driver.read_low' 'lib/math/unit.h.oymo'") == normal('{f = [02]}')
        assert normal("'driver.read_low' 'lib/a.oymo'") == normal('{f = [01]}')
    assert not build.errors
    assert build.paths == ['lib/math/unit.h.oymo', 'lib/a.oymo']
    assert build.host_path('lib/math/unit.h.oymo') == os.path.join(str(math), 'unit.h.oymo')
    # A path that only starts with the mount's name is not under it.
    assert build.host_path('lib/mathx/a.oymo') == os.path.join(str(top), 'lib', 'mathx', 'a.oymo')


def test_a_link_may_not_leave_the_mounted_folder(tmp_path):
    top, math = tmp_path / 'top', tmp_path / 'math'
    write(top, 'source.oymo', HEADER + '{}\n')
    math.mkdir()
    (math / 'link.oymo').symlink_to(top / 'source.oymo')
    with driver.session(str(top), mounts={'m': str(math)}) as build:
        normal("'driver.read_low' 'm/link.oymo'")
    assert build.errors[0][0] == "'m/link.oymo' leaves the folder mounted at 'm'."


def test_a_missing_file_under_a_mount(tmp_path):
    (tmp_path / 'math').mkdir()
    with driver.session(str(tmp_path / 'top'), mounts={'m': str(tmp_path / 'math')}) as build:
        normal("'driver.read_low' 'm/unit.h.oymo'")
    assert build.errors[0][0] == "could not find oymo file 'm/unit.h.oymo'"


def test_bad_mounts_raise(tmp_path):
    folder = str(tmp_path / 'd')
    (tmp_path / 'd').mkdir()
    with (
        pytest.raises(driver.MountError, match='overlap'),
        driver.session(str(tmp_path), mounts={'v/w': folder, 'v': folder}),
    ):
        pass
    driver.check_mounts(str(tmp_path), {'v': folder, 'vw': folder})  # `vw` is not under `v`


def test_read_bytes_of_a_missing_file(tmp_path):
    # Not read as an oymo file, so not "could not find oymo file".
    with driver.session(str(tmp_path)) as build:
        normal("'driver.read_bytes' 'data.bin'")
    assert build.errors[0][0] == "Cannot read 'data.bin': No such file or directory."


@pytest.mark.parametrize(
    ('text', 'message'),
    [
        (HEADER + '{x= \n', "Cannot read 'a.oymo': at 2:1: Syntax error."),
        ('{}\n', "Cannot read 'a.oymo': at 1:1: Expected the first line to be 'language oymomo'."),
    ],
)
def test_a_file_that_does_not_parse_is_an_error_at_the_read(tmp_path, text, message):
    write(tmp_path, 'a.oymo', text)
    with driver.session(str(tmp_path)) as build:
        term = normal("'driver.read_low' 'a.oymo'")
    assert build.errors == [(message, term.argument.tag)]


def test_errors_are_recorded_once(tmp_path):
    with driver.session(str(tmp_path)) as build:
        normal("{'driver.read_low' 'missing.oymo', 'driver.read_high' 'missing.oymo', 'add' {'i32', [01], [01]}}")
    assert len(build.errors) == 1


def test_read_bytes(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'\x00\xff')
    with driver.session(str(tmp_path)):
        assert normal("'driver.read_bytes' 'data.bin'") == terms.ByteArray(b'\x00\xff')


def test_a_file_that_is_not_utf8_text_is_not_an_oymo_file(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'\xff')
    with driver.session(str(tmp_path)) as build:
        normal("'driver.read_low' 'data.bin'")
    assert build.errors[0][0] == "Cannot read 'data.bin': it is not UTF-8 text."


def test_config():
    with driver.session('', {'mode': 'debug', 'n': '3'}):
        assert normal("'driver.config' {}") == normal("{mode = 'debug', n = '3'}")
        assert normal("('driver.config' {}).mode") == normal("'debug'")


def test_wrong_operands_are_errors():
    with driver.session('') as build:
        normal("'driver.config' [01]")
        normal("'driver.read_low' {}")
    assert [message for message, _ in build.errors] == [
        "'driver.config' takes {}.",
        "'driver.read_low' takes a path: a text byte array.",
    ]


@pytest.mark.parametrize(
    'source',
    ["'driver.read_low' 'a.oymo'", "'driver.read_high' 'a.oymo'", "'driver.read_bytes' 'a.oymo'", "'driver.config' {}"],
)
def test_no_session_no_step(source):
    term = reduction.resolve(parse(source))
    assert reduction.reduce(term) is term


def test_a_unit_from_files(tmp_path):
    write(tmp_path, 'a.oymo', HEADER + "{ns = {x = {type = 'i32', link = 'x'}}}\n")
    write(tmp_path, 'b.oymo', HEADER + "{ns = {y = {type = 'i32', link = 'y'}}}\n")
    with driver.session(str(tmp_path)) as build:
        unit = normal("'unit.merge' {'driver.read_low' 'a.oymo', 'driver.read_low' 'b.oymo'}")
    build.check()
    assert unit == normal("{ns = {x = {type = 'i32', link = 'x'}, y = {type = 'i32', link = 'y'}}}")


def test_normal_is_decided_per_build(tmp_path):
    # Outside a build a driver call gives no result, so it is normal; inside one it reads.
    write(tmp_path, 'a.oymo', 'language oymomo\n[01]\n')
    call = reduction.resolve(parse("'driver.read_low' 'a.oymo'"))
    assert reduction.is_normal(call)
    with driver.session(str(tmp_path)):
        assert not reduction.is_normal(call)
