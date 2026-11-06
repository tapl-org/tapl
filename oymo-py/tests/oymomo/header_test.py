# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Headers: a unit's linked symbols, declared, for other units to read."""

from oymo.oymomo import header, ingot, meta, reduction, source, strategy, terms
from oymo.oymomo.grammar import parse

FUNCTION = "{'function', {a = 'i32', b = 'i32'}, 'i32'}"
BODY = "λg. λp. 'R' (λr. {let y = 'add' {'i32', p.a, p.b} in y})"
ALCOR_FILE = meta.File.of('alcor/math.oymo', 'alcor', b'language alcor\nfn gcd(a: i32, b: i32) -> i32 {}\n')


def read(text: str) -> ingot.Ingot:
    return ingot.ingot_of(parse(text))


def normal(text: str) -> terms.Term:
    return strategy.normalize(reduction.resolve(parse(text)))


def test_linked_definitions_are_kept_internal_symbols_and_imports_dropped():
    void_fn = "{'function', {p = 'ptr'}, 'void'}"
    void_body = "λg. λp. 'R' (λr. {[]})"
    unit = read(
        f"{{math = {{gcd = {{type = {FUNCTION}, body = {BODY}, link = 'gcd'}},"
        f" clear = {{type = {void_fn}, body = {void_body}, link = 'clear'}},"
        f' helper = {{type = {FUNCTION}, body = {BODY}}}}},'
        " puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'}}"
    )
    assert header.header_of(unit) == normal(
        f"{{math = {{gcd = {{type = {FUNCTION}, link = 'gcd'}}, clear = {{type = {void_fn}, link = 'clear'}}}}}}"
    )


def test_namespaces_are_kept_and_empty_ones_removed():
    unit = read(
        f'{{a = {{b = {{f = {{type = {FUNCTION}, body = {BODY}}}}}}},'
        f" c = {{d = {{g = {{type = {FUNCTION}, body = {BODY}, link = 'g'}}}}, e = {{}}}}}}"
    )
    assert header.header_of(unit) == normal(f"{{c = {{d = {{g = {{type = {FUNCTION}, link = 'g'}}}}}}}}")


def test_an_ingot_with_nothing_linked_has_an_empty_header():
    assert header.header_of(read(f'{{f = {{type = {FUNCTION}, body = {BODY}}}}}')) == terms.Struct([])


def test_constants_and_globals_become_declarations():
    unit = read(
        "{k = {type = 'i32', value = [05000000], link = 'k'},"
        " g = {type = {'array', [02], 'i8'}, init = [6869], link = 'g'},"
        " internal = {type = 'i32', value = [01000000]}}"
    )
    assert header.header_of(unit) == normal(
        "{k = {type = 'i32', link = 'k'}, g = {type = {'array', [02], 'i8'}, link = 'g'}}"
    )


def test_a_header_is_an_ingot_of_declarations():
    unit = read(f"{{f = {{type = {FUNCTION}, body = {BODY}, link = 'f'}}}}")
    (symbol,) = ingot.read_ingot(header.header_of(unit)).symbols
    assert isinstance(symbol, ingot.Declaration)
    assert (symbol.path, symbol.link) == (('f',), 'f')


def test_one_layer_gives_its_header():
    unit = read(f"{{f = {{type = {FUNCTION}, body = {BODY}, link = 'f'}}}}")
    assert header.header_of_layers([unit]) == header.header_of(unit)


def test_two_layers_are_one_header_low_then_high():
    written = parse(
        "{g = {type = 'i32', init = [01000000] : [02000000], link = 'g'},"
        " h = {type = 'i32', init = [01000000], link = 'h' : 'h2'}}"
    )
    separated = header.header_of_layers(ingot.ingots_of(written))
    assert source.write(separated) == (
        "language oymomo\n{g= {type= 'i32', link= 'g'}, h= {type= 'i32', link= 'h'}}\n"
        "  : {g= {type= 'i32', link= 'g'}, h= {type= 'i32', link= 'h2'}}\n"
    )


def test_two_layers_merged_on_request():
    # The layers agree on `g`'s declaration (only its init differs) and differ in `h`'s link.
    written = parse(
        "{g = {type = 'i32', init = [01000000] : [02000000], link = 'g'},"
        " h = {type = 'i32', init = [01000000], link = 'h' : 'h2'}}"
    )
    merged = header.header_of_layers(ingot.ingots_of(written), merged=True)
    assert (
        source.write(merged) == "language oymomo\n{g= {type= 'i32', link= 'g'}, h= {type= 'i32', link= 'h' : 'h2'}}\n"
    )


def test_a_symbol_linked_in_one_layer_only_layers_its_namespace():
    written = parse(
        "{g = {type = 'i32', init = [01000000], link = 'g'},"
        " i = {type = 'i32', init = [01000000], link = 'i'} : {type = 'i32', init = [01000000]}}"
    )
    merged = header.header_of_layers(ingot.ingots_of(written), merged=True)
    assert source.write(merged) == (
        "language oymomo\n{g= {type= 'i32', link= 'g'}, i= {type= 'i32', link= 'i'}}\n  : {g= {type= 'i32', link= 'g'}}\n"
    )


def test_a_declaration_keeps_the_tag_of_its_definition():
    loaded = source.read(f"language oymomo\n{{f = {{type = {FUNCTION}, body = {BODY}, link = 'f'}}}}\n", 'a.oymo')
    unit = ingot.ingot_of(loaded.term)
    declaration = header.header_of(unit).fields[0].value
    assert declaration.tag == unit.symbols[0].tag
    assert declaration.tag.file is not None
    # Places into a `language oymomo` file are never written.
    assert '---' not in source.write(header.header_of(unit))


def test_a_place_in_a_frontend_source_is_written():
    unit = read(f"{{f = {{type = {FUNCTION}, body = {BODY}, link = 'gcd'}}}}")
    unit.symbols[0].tag = meta.Tag(ALCOR_FILE, 15, 32)
    text = source.write(header.header_of(unit))
    assert 'path: "alcor/math.oymo"' in text
    assert source.read(text, 'math.h.oymo').term.fields[0].value.tag.file == ALCOR_FILE
