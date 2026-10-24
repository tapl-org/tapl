# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.core import spans, syntax
from oymo.oymomo import source, terms

ALCOR = b'language alcor\nfn f() { return 5; }\n'
CODE = "language oymomo\nlet x = 'add' {'i32', a, b} in {x, [05]}\n"


def read(text: str, table: spans.SpanTable | None = None) -> syntax.Term:
    loaded = source.read(text, 'a.oymo', table or spans.SpanTable())
    assert not loaded.warnings
    return loaded.term


def with_alcor_spans(table: spans.SpanTable) -> syntax.Term:
    """CODE, whose `add` call and returned struct point into ALCOR."""
    term = read(CODE, table)
    alcor = table.add_file('alcor/f.oymo', 'alcor', ALCOR)
    for node in source.nodes(term):
        match node:
            case terms.Apply(function=terms.ByteArray(value=b'add')):
                node.span = spans.make(alcor.start + ALCOR.index(b'5'), 1)
            case terms.Struct(fields=[_, _]):
                node.span = spans.make(alcor.start + ALCOR.index(b'return'), 9)
    return term


def test_nodes_are_in_pre_order_with_fields_before_their_values() -> None:
    term = read('language oymomo\n{a = x, y}.a\n')
    kinds = [type(node).__name__ for node in source.nodes(term)]
    assert kinds == ['Project', 'Struct', 'Field', 'Variable', 'Field', 'Variable']


def test_a_hand_written_file_spans_its_own_row_in_bytes() -> None:
    table = spans.SpanTable()
    term = read('language oymomo\n// λ\nλa. a\n', table)
    assert isinstance(term, terms.Lambda)
    assert table.resolve(term.span) == ('a.oymo', 3, 1)
    assert table.resolve(term.body.span) == ('a.oymo', 3, len('λa. '.encode()) + 1)
    assert spans.length(term.span) == len('λa. a'.encode())


def test_spans_into_an_oymomo_file_are_never_written() -> None:
    table = spans.SpanTable()
    assert source.write(read(CODE, table), table) == CODE


def test_spans_into_a_frontend_file_survive_a_round_trip() -> None:
    table = spans.SpanTable()
    term = with_alcor_spans(table)
    text = source.write(term, table)
    assert "'alcor/f.oymo' alcor" in text
    # Read in another run, where another file came first: the spans move to new rows.
    other = spans.SpanTable()
    other.add_file('first.oymo', 'oymomo', b'language oymomo\n{}\n')
    again = read(text, other)
    assert isinstance(again, terms.Apply)
    assert isinstance(again.function, terms.Lambda)
    add = again.argument
    struct = again.function.body
    assert (other.resolve(add.span), spans.length(add.span)) == (('alcor/f.oymo', 2, 17), 1)
    assert (other.resolve(struct.span), spans.length(struct.span)) == (('alcor/f.oymo', 2, 10), 9)
    assert source.write(again, other) == text


def test_dots_inherit_the_parent_span() -> None:
    table = spans.SpanTable()
    text = source.write(with_alcor_spans(table), table)
    again = read(text, spans.SpanTable())
    assert isinstance(again, terms.Apply)
    assert isinstance(again.function, terms.Lambda)
    struct = again.function.body
    assert isinstance(struct, terms.Struct)
    assert all(field.span == struct.span for field in struct.fields)
    assert struct.fields[0].value.span == struct.span


def test_the_info_section_format() -> None:
    table = spans.SpanTable()
    text = source.write(with_alcor_spans(table), table)
    info = text.split('\n---\n')[1].splitlines()
    assert info[0] == 'info 1'
    assert info[1] == f'code {spans.md5((text.split("---")[0]).encode())}'
    assert info[2] == 'start length file language hash lines'
    assert info[3] == f"1 {len(ALCOR):x} 'alcor/f.oymo' alcor {spans.md5(ALCOR)} {{0, f, 24}}"
    assert info[4] == 'spans'
    assert info[5].split()[0] == '.2'


def info_text(code: str, rows: list[str], entries: str, columns: str = 'start length file language hash lines') -> str:
    md5 = spans.md5(code.encode())
    return code + '\n'.join(['---', 'info 1', f'code {md5}', columns, *rows, 'spans', entries]) + '\n'


ROW = f"1 {len(ALCOR):x} 'alcor/f.oymo' alcor {spans.md5(ALCOR)} {{0, f, 24}}"


def test_runs_of_dots_and_no_span_entries() -> None:
    table = spans.SpanTable()
    term = read(info_text('language oymomo\n{x, y}\n', [ROW], '10001 .2 0 .'), table)
    assert isinstance(term, terms.Struct)
    assert table.resolve(term.span) == ('alcor/f.oymo', 1, 1)
    assert term.fields[0].span == term.fields[0].value.span == term.span
    assert term.fields[1].span == spans.NO_SPAN
    assert term.fields[1].value.span == spans.NO_SPAN


def test_unknown_columns_are_skipped() -> None:
    table = spans.SpanTable()
    row = f"1 {len(ALCOR):x} 'alcor/f.oymo' alcor {spans.md5(ALCOR)} {{0, f, 24}} later"
    columns = 'start length file language hash lines extra'
    term = read(info_text('language oymomo\nx\n', [row], '10001', columns), table)
    assert table.resolve(term.span) == ('alcor/f.oymo', 1, 1)


def test_a_changed_code_drops_the_spans_with_a_warning() -> None:
    table = spans.SpanTable()
    text = info_text('language oymomo\nx\n', [ROW], '10001').replace('\nx\n', '\ny\n', 1)
    loaded = source.read(text, 'a.oymo', table)
    assert [message for message, _ in loaded.warnings] == [
        'The code changed since its spans were written; the spans are dropped.'
    ]
    assert table.resolve(loaded.term.span) == ('a.oymo', 2, 1)


@pytest.mark.parametrize(
    ('text', 'message'),
    [
        ('{}\n', "Expected the first line to be 'language oymomo'."),
        ('language oymomo\nx\n---\ninfo 2\n', "The info section must start with 'info 1'."),
        (info_text('language oymomo\nx\n', [ROW], '10001', 'start length file'), "no column 'language'"),
        (info_text('language oymomo\nx\n', [ROW], '10001 .'), 'has 2 entries; the code has 1 nodes'),
        (info_text('language oymomo\n{x}\n', [ROW], '10001'), 'the code has more nodes'),
        (info_text('language oymomo\nx\n', [ROW], '9990001'), 'is in no row'),
        (info_text('language oymomo\nx\n', [ROW], 'zz'), "'zz' is not a hex number"),
        (info_text('language oymomo\nx\n', ['1 2 alcor/f.oymo alcor 0 {0}'], '10001'), 'in quotes'),
    ],
)
def test_bad_files(text: str, message: str) -> None:
    with pytest.raises(source.SourceError) as info:
        source.read(text, 'a.oymo', spans.SpanTable())
    assert message in info.value.message


def test_a_syntax_error_spans_the_code() -> None:
    table = spans.SpanTable()
    term = source.read('language oymomo\n{x= \n', 'a.oymo', table).term
    assert isinstance(term, syntax.ErrorTerm)
    assert table.resolve(term.span) == ('a.oymo', 2, 1)
