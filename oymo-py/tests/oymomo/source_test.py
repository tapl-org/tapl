# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pathlib

import pytest
from google.protobuf import descriptor_pb2
from grpc_tools import protoc

from oymo.core import syntax
from oymo.oymomo import meta, meta_pb2, source, terms

ALCOR = b'language alcor\nfn f() { return 5; }\n'
ALCOR_FILE = meta.File.of('alcor/f.oymo', 'alcor', ALCOR)
CODE = "language oymomo\nlet x = 'add' {'i32', a, b} in {x, [05]}\n"


def read(text: str) -> syntax.Term:
    loaded = source.read(text, 'a.oymo')
    assert not loaded.warnings
    return loaded.term


def where(tag: meta.Tag) -> tuple[str, int, int] | None:
    """`(path, line, column)` of a tag's start."""
    return None if tag.file is None else (tag.file.path, *tag.file.position(tag.start))


def with_alcor_tags() -> syntax.Term:
    """CODE, whose `add` call and returned struct point into ALCOR."""
    term = read(CODE)
    for node in terms.nodes(term):
        match node:
            case terms.Apply(function=terms.ByteArray(value=b'add')):
                node.tag = meta.Tag(ALCOR_FILE, ALCOR.index(b'5'), 1)
            case terms.Struct(fields=[_, _]):
                node.tag = meta.Tag(ALCOR_FILE, ALCOR.index(b'return'), 9)
    return term


def test_nodes_are_in_pre_order_with_fields_before_their_values() -> None:
    term = read('language oymomo\n{a = x, y}.a\n')
    kinds = [type(node).__name__ for node in terms.nodes(term)]
    assert kinds == ['Project', 'Struct', 'Field', 'Variable', 'Field', 'Variable']


def test_a_hand_written_file_tags_its_own_bytes() -> None:
    text = 'language oymomo\n// λ\nλa. a\n'
    term = read(text)
    assert isinstance(term, terms.Lambda)
    assert term.tag.file == meta.File.of('a.oymo', 'oymomo', text.encode())
    assert term.tag.start == text.encode().index('λa'.encode())
    assert where(term.tag) == ('a.oymo', 3, 1)
    assert where(term.body.tag) == ('a.oymo', 3, len('λa. '.encode()) + 1)
    assert term.tag.length == len('λa. a'.encode())


def test_places_in_an_oymomo_file_are_never_written() -> None:
    assert source.write(read(CODE)) == CODE


def test_places_in_a_frontend_file_survive_a_round_trip() -> None:
    text = source.write(with_alcor_tags())
    assert 'path: "alcor/f.oymo"' in text
    again = read(text)
    assert isinstance(again, terms.Apply)
    assert isinstance(again.function, terms.Lambda)
    add = again.argument
    struct = again.function.body
    assert (where(add.tag), add.tag.length) == (('alcor/f.oymo', 2, 17), 1)
    assert (where(struct.tag), struct.tag.length) == (('alcor/f.oymo', 2, 10), 9)
    assert add.tag.file == ALCOR_FILE
    assert add.tag.file is struct.tag.file
    assert source.write(again) == text


def test_empty_entries_share_the_parent_tag() -> None:
    again = read(source.write(with_alcor_tags()))
    assert isinstance(again, terms.Apply)
    assert isinstance(again.function, terms.Lambda)
    struct = again.function.body
    assert isinstance(struct, terms.Struct)
    assert all(field.tag is struct.tag for field in struct.fields)
    assert struct.fields[0].value.tag is struct.tag


def test_the_meta_section_format() -> None:
    text = source.write(with_alcor_tags())
    code, section = text.split('\n---\n')
    assert section.splitlines() == [
        f'code_md5: "{meta.md5((code + chr(10)).encode())}"',
        'files {',
        '  path: "alcor/f.oymo"',
        '  language: "alcor"',
        f'  md5: "{meta.md5(ALCOR)}"',
        '  lines: [0, 15, 36]',
        '}',
        'tags { skip: 2 }',
        f'tags {{ file: 0 start: {ALCOR.index(b"return")} length: 9 }}',
        'tags { skip: 4 }',
        f'tags {{ file: 0 start: {ALCOR.index(b"5")} length: 1 }}',
        'tags { skip: 8 }',
    ]


def test_a_path_is_written_as_utf8() -> None:
    term = read(CODE)
    term.tag = meta.Tag(meta.File.of('alcor/ä.oymo', 'alcor', ALCOR), 0, 1)
    text = source.write(term)
    assert 'path: "alcor/ä.oymo"' in text
    assert where(read(text).tag) == ('alcor/ä.oymo', 1, 1)


def test_files_are_numbered_by_first_use_with_offsets_of_their_own() -> None:
    second = meta.File.of('b.alcor', 'alcor', b'one\ntwo\n')
    term = read('language oymomo\n{[01], [02], [03]}\n')
    assert isinstance(term, terms.Struct)
    # The first field points into `second`, the others into ALCOR: `second` is file 0.
    term.fields[0].value.tag = meta.Tag(second, 4, 3)
    term.fields[1].value.tag = meta.Tag(ALCOR_FILE, 4, 3)
    term.fields[2].value.tag = meta.Tag(meta.File.of('b.alcor', 'alcor', b'one\ntwo\n'), 0, 3)
    text = source.write(term)
    section = text.split('\n---\n')[1]
    assert section.index('path: "b.alcor"') < section.index('path: "alcor/f.oymo"')
    assert section.count('files {') == 2
    assert 'tags { file: 0 start: 4 length: 3 }' in section
    assert 'tags { file: 1 start: 4 length: 3 }' in section
    assert 'tags { file: 0 length: 3 }' in section
    again = read(text)
    assert isinstance(again, terms.Struct)
    values = [field.value.tag for field in again.fields]
    assert [where(tag) for tag in values] == [('b.alcor', 2, 1), ('alcor/f.oymo', 1, 5), ('b.alcor', 1, 1)]
    assert values[0].file is values[2].file


def test_a_length_past_16_bits_is_kept() -> None:
    big = meta.File.of('big.alcor', 'alcor', b'x' * 100_000)
    term = read('language oymomo\nx\n')
    term.tag = meta.Tag(big, 70_000, 30_000)
    text = source.write(term)
    assert 'tags { file: 0 start: 70000 length: 30000 }' in text
    again = read(text).tag
    assert (again.start, again.length) == (70_000, 30_000)


def meta_text(code: str, section: str, md5: str | None = None) -> str:
    md5 = meta.md5(code.encode()) if md5 is None else md5
    return f'{code}---\ncode_md5: "{md5}"\n{section}'


FILE = f'files {{ path: "alcor/f.oymo" language: "alcor" md5: "{meta.md5(ALCOR)}" lines: [0, 15, 36] }}\n'


def test_skip_runs_no_place_and_empty_entries() -> None:
    entries = FILE + 'tags { file: 0 length: 1 }\ntags { skip: 2 }\ntags { file: -1 }\ntags {}\n'
    term = read(meta_text('language oymomo\n{x, y}\n', entries))
    assert isinstance(term, terms.Struct)
    assert where(term.tag) == ('alcor/f.oymo', 1, 1)
    assert term.fields[0].tag is term.fields[0].value.tag is term.tag
    assert term.fields[1].tag == meta.NO_TAG
    assert term.fields[1].value.tag is term.fields[1].tag


def test_a_tag_with_no_file_is_the_parent_place() -> None:
    # The field's tag has an unknown field only: it inherits the struct's place.
    entries = FILE + 'tags { file: 0 start: 4 length: 5 }\ntags { range: 1 }\ntags {}\n'
    term = read(meta_text('language oymomo\n{x}\n', entries))
    assert isinstance(term, terms.Struct)
    assert term.tag.place() == (ALCOR_FILE, 4, 5)
    assert term.fields[0].tag.place() == term.fields[0].value.tag.place() == (ALCOR_FILE, 4, 5)


def test_unknown_fields_are_skipped() -> None:
    entries = FILE.replace('lines:', 'id: 7 lines:') + 'range { start: 1 end: 2 }\ntags { file: 0 flags: [1, 2] }\n'
    term = read(meta_text('language oymomo\nx\n', entries))
    assert where(term.tag) == ('alcor/f.oymo', 1, 1)


def test_a_changed_code_drops_the_tags_with_a_warning() -> None:
    text = meta_text('language oymomo\nx\n', FILE + 'tags { file: 0 }\n').replace('\nx\n', '\ny\n', 1)
    loaded = source.read(text, 'a.oymo')
    assert [message for message, _ in loaded.warnings] == [
        'The code changed since its tags were written; the tags are dropped.'
    ]
    assert where(loaded.term.tag) == ('a.oymo', 2, 1)


def test_a_textproto_error_points_into_the_meta() -> None:
    text = meta_text('language oymomo\nx\n', 'tags { file: x }\n')
    with pytest.raises(source.SourceError) as info:
        source.read(text, 'a.oymo')
    assert (
        info.value.message == "The meta section is not valid textproto: 'tags { file: x }': Couldn't parse integer: x"
    )
    assert where(info.value.tag) == ('a.oymo', 5, 14)


X = 'language oymomo\nx\n'


@pytest.mark.parametrize(
    ('text', 'message'),
    [
        ('{}\n', "Expected the first line to be 'language oymomo'."),
        (X + '---\ninfo 1\n', 'The meta section is not valid textproto: '),
        (meta_text(X, 'tags { file: "a" }\n'), 'The meta section is not valid textproto: '),
        (meta_text(X, FILE + 'tags { file: 0 }\ntags {}\n'), 'The meta has 2 tags; the code has 1 nodes.'),
        (meta_text(X, FILE + 'tags { skip: 2 }\n'), 'The meta has 2 tags; the code has 1 nodes.'),
        (meta_text(X, ''), 'The meta has 0 tags; the code has more nodes.'),
        (meta_text(X, FILE + 'tags { file: 1 }\n'), 'A tag of the meta names file 1; there are 1 files.'),
        (meta_text(X, FILE + 'tags { file: -2 }\n'), 'A tag of the meta names file -2; there are 1 files.'),
        (meta_text(X, FILE + 'tags { file: 0 skip: 2 }\n'), 'A tag of the meta has both a file and a skip.'),
        (meta_text(X, FILE + 'tags { start: 3 }\n'), 'A tag of the meta has a start or a length but no file.'),
        (meta_text(X, 'files { path: "a" }\ntags {}\n'), "The file 'a' in the meta has no line starts."),
    ],
)
def test_bad_files(text: str, message: str) -> None:
    with pytest.raises(source.SourceError) as info:
        source.read(text, 'a.oymo')
    assert info.value.message.startswith(message)


def test_a_syntax_error_tags_the_code() -> None:
    term = source.read('language oymomo\n{x= \n', 'a.oymo').term
    assert isinstance(term, syntax.ErrorTerm)
    assert where(term.tag) == ('a.oymo', 2, 1)


def test_meta_pb2_is_generated_from_meta_proto(tmp_path: pathlib.Path) -> None:
    """If this fails, regenerate it: `hatch run proto:generate`."""
    root = pathlib.Path(source.__file__).parents[2]
    descriptors = tmp_path / 'meta.pb'
    command = ['protoc', f'--proto_path={root}', f'--descriptor_set_out={descriptors}', 'oymo/oymomo/meta.proto']
    assert protoc.main(command) == 0
    [compiled] = descriptor_pb2.FileDescriptorSet.FromString(descriptors.read_bytes()).file
    # protoc fills in the JSON names; the generated code leaves them out.
    for message in compiled.message_type:
        for field in message.field:
            field.ClearField('json_name')
    assert compiled == descriptor_pb2.FileDescriptorProto.FromString(meta_pb2.DESCRIPTOR.serialized_pb)


def test_shared_tags_stay_shared_in_bytes() -> None:
    # `let` gives its lambda and application one tag.
    term = read('language oymomo\nlet x = [01] in x\n')
    assert isinstance(term, terms.Apply)
    assert term.function.tag is term.tag


def test_a_tag_equal_to_its_parent_is_an_empty_entry() -> None:
    term = with_alcor_tags()
    assert isinstance(term, terms.Apply)
    assert isinstance(term.function, terms.Lambda)
    struct = term.function.body
    assert isinstance(struct, terms.Struct)
    text = source.write(term)
    # An equal tag, not the same object, is written as an empty entry too.
    struct.fields[0].tag = meta.Tag(ALCOR_FILE, struct.tag.start, struct.tag.length)
    assert struct.fields[0].tag is not struct.tag
    assert source.write(term) == text


def test_a_layering_is_one_node_of_the_meta() -> None:
    # The layering is visited before its sides, so its tag and theirs survive a round trip.
    term = read("language oymomo\nλa. λb. f ('add' {'i32', a, b} : g a)\n")
    layering = next(node for node in terms.nodes(term) if isinstance(node, syntax.Layers))
    assert [type(node).__name__ for node in terms.nodes(layering)][:3] == ['Layers', 'Apply', 'ByteArray']
    layering.tag = meta.Tag(ALCOR_FILE, ALCOR.index(b'return'), 9)
    _, high = layering.layers
    high.tag = meta.Tag(ALCOR_FILE, ALCOR.index(b'5'), 1)
    again = read(source.write(term))
    layering_again = next(node for node in terms.nodes(again) if isinstance(node, syntax.Layers))
    assert where(layering_again.tag) == ('alcor/f.oymo', 2, 10)
    assert where(layering_again.layers[1].tag) == ('alcor/f.oymo', 2, 17)
    assert where(layering_again.layers[0].tag) == ('alcor/f.oymo', 2, 10)  # its parent's place
