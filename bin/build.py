#!/usr/bin/env python3
"""Build shexTest-contrib from the case table below, cross-checking every verdict.

    python3 bin/build.py            write schemas-contrib/, validation-contrib/, negativeSyntax-contrib/ and their manifests
    python3 bin/build.py --check    write nothing; fail if a file or a verdict would change

Each schema is written in ShExC by hand; its ShExJ (.json) and ShExR (.ttl) come from shex.js-array
(shex-to-json, shex-to-turtle). Each validation case is run by shex.js-array (packages/shex-cli/bin/
validate) and by jena-array (rdf-array/rdf-array's tools/JenaArray.java, against the ShExC and the
ShExR forms); a case is written only when every run gives the expected verdict. Each negative-syntax
case must be rejected by both parsers. The implementations are found beside this checkout
(../shex.js-array, ../rdf-array/.tools) or through SHEXJS_ARRAY and JENA_ARRAY_TOOL.

`duplicates` names the implementation tests a case reproduces; rdf-array/rdf-array's
contrib-duplicates.md is generated from it (tools/contrib-duplicates.py).
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for d in ('schemas-contrib', 'validation-contrib', 'negativeSyntax-contrib'):
    (ROOT / d).mkdir(exist_ok=True)
SHEXJS = pathlib.Path(os.environ.get('SHEXJS_ARRAY', ROOT.parent / 'shex.js-array'))
JT = pathlib.Path(os.environ.get('JENA_ARRAY_TOOL', ROOT.parent / 'rdf-array' / '.tools'))
JAVA = os.environ.get('JAVA', '/opt/homebrew/opt/openjdk@21/bin/java')
# The manifests' @base is shexTest's conventional one: shexTest's bin/genJSON.js and the runners
# that read its manifests (shex.js, PyShEx) derive file paths from it. Only relative resolution
# depends on it; the files are wherever this repository is.
BASE = 'https://raw.githubusercontent.com/shexSpec/shexTest/master/'
CHECK = '--check' in sys.argv

P = 'PREFIX : <http://a.example/>\nPREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n\n'
SCHEMAS = {
    'collRef1to2': ('a sequence of one or two nodes, each with an integer :q',
                    P + ':T { :q xsd:integer }\n\n:S1 { :p1 ((@:T))[1, 2] }\n'),
    'collInt': ('a sequence of any length (empty included) of integers', P + ':S1 { :p1 ((xsd:integer)) }\n'),
    'collInt2': ('a sequence of exactly two integers', P + ':S1 { :p1 ((xsd:integer))[2] }\n'),
    'collInt1Plus': ('a sequence of one or more integers', P + ':S1 { :p1 ((xsd:integer))[1, *] }\n'),
    'collNested': ('a non-empty sequence of one-element sequences of nodes with an integer :q',
                   P + ':T { :q xsd:integer }\n\n:S1 { :p1 ((((@:T))[1]))[1, *] }\n'),
    'collDot': ('a sequence of any length of anything', P + ':S1 { :p1 ((.)) }\n'),
    'collIriOrInt': ('a non-empty sequence whose elements are IRIs or integers',
                     P + ':S1 { :p1 ((IRI OR xsd:integer))[1, *] }\n'),
    'collNotInt': ('a sequence of any length none of whose elements is an integer', P + ':S1 { :p1 ((NOT xsd:integer)) }\n'),
    'collValueIri': ('an IRI value constraint is not satisfied by a sequence', P + ':S1 { :p1 IRI }\n'),
    'collColour': ('a colour is a sequence of exactly three bytes',
                   P + ':Colour { :rgb ((xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 255))[3] }\n'),
    'collPolygon': ('a polygon is three or more points, each a sequence of two decimals',
                    P + ':Polygon { :points ((((xsd:decimal))[2]))[3, *] }\n'),
    'collPlaylist': ('a playlist is a title and one or more tracks, in order',
                     P + ':Playlist { :title xsd:string ; :tracks ((@:Track))[1, *] }\n\n'
                         ':Track { :title xsd:string ; :seconds xsd:integer }\n'),
    'collDecl': ('a shape declaration whose shape expression is a Collection',
                 P + ':L ((IRI))[1, *]\n\n:S1 { :p1 @:L }\n'),
}

D = 'PREFIX : <http://a.example/>\n\n'
J = 'jena-array jena-shex TestShexCollection'
V = 'shex.js-array packages/shex-validator/test/Collection-test.js'
W = 'shex.js-array packages/shex-webapp/examples/manifest.json'
# name, schema, data, focus, shape, conformant?, comment, duplicates
VALIDATION = [
    ('collRef1to2_two_pass', 'collRef1to2', ':n1 :p1 (:a :b) . :a :q 1 . :b :q 2 .', 'n1', 'S1', True,
     'each element satisfies the element shape', [f'{J}.elements_each_satisfy_the_element_shape', f'{V} "accepts a sequence of the right length whose elements conform"']),
    ('collRef1to2_one_pass', 'collRef1to2', ':n1 :p1 (:a) . :a :q 1 .', 'n1', 'S1', True,
     'one element is within [1, 2]', [f'{J}.one_element_is_enough']),
    ('collRef1to2_three_fail', 'collRef1to2', ':n1 :p1 (:a :b :c) . :a :q 1 . :b :q 2 . :c :q 3 .', 'n1', 'S1', False,
     'three elements exceed [1, 2]', [f'{J}.too_many_elements', f'{V} "checks the bounds"']),
    ('collRef1to2_empty_fail', 'collRef1to2', ':n1 :p1 () .', 'n1', 'S1', False,
     'the empty sequence is below [1, 2]', [f'{J}.too_few_elements', f'{V} "checks the bounds"']),
    ('collRef1to2_badElement_fail', 'collRef1to2', ':n1 :p1 (:a :b) . :a :q 1 . :b :q "two" .', 'n1', 'S1', False,
     'the second element fails the element shape', [f'{J}.an_element_fails_the_element_shape', f'{V} "reports the elements that fail, by index"', f'{V} "follows shape references from the elements"']),
    ('collRef1to2_notSeq_fail', 'collRef1to2', ':n1 :p1 :a . :a :q 1 .', 'n1', 'S1', False,
     'an IRI is not a sequence', [f'{J}.not_a_sequence', f'{V} "wants a sequence"']),
    ('collInt_literal_fail', 'collInt', ':n1 :p1 1 .', 'n1', 'S1', False,
     'a literal is not a sequence', [f'{J}.not_a_sequence']),
    ('collInt_empty_pass', 'collInt', ':n1 :p1 () .', 'n1', 'S1', True,
     'no bounds: the empty sequence', [f'{J}.any_length_including_empty', f'{V} "accepts the empty sequence where the bounds allow it"']),
    ('collInt_three_pass', 'collInt', ':n1 :p1 (1 2 3) .', 'n1', 'S1', True,
     'no bounds: three integers', [f'{J}.any_length_including_empty']),
    ('collInt_mixed_fail', 'collInt', ':n1 :p1 (1 "a") .', 'n1', 'S1', False,
     'a string element fails xsd:integer', [f'{J}.any_length_including_empty']),
    ('collInt2_two_pass', 'collInt2', ':n1 :p1 (1 2) .', 'n1', 'S1', True, '[2]: exactly two', [f'{J}.exact_length']),
    ('collInt2_one_fail', 'collInt2', ':n1 :p1 (1) .', 'n1', 'S1', False, '[2]: one is too few', [f'{J}.exact_length']),
    ('collInt2_three_fail', 'collInt2', ':n1 :p1 (1 2 3) .', 'n1', 'S1', False, '[2]: three is too many', [f'{J}.exact_length']),
    ('collInt1Plus_empty_fail', 'collInt1Plus', ':n1 :p1 () .', 'n1', 'S1', False, '[1, *]: empty is too few', [f'{J}.at_least_one']),
    ('collInt1Plus_one_pass', 'collInt1Plus', ':n1 :p1 (1) .', 'n1', 'S1', True, '[1, *]: one', [f'{J}.at_least_one']),
    ('collInt1Plus_four_pass', 'collInt1Plus', ':n1 :p1 (1 2 3 4) .', 'n1', 'S1', True, '[1, *]: four', [f'{J}.at_least_one']),
    ('collNested_pass', 'collNested', ':n1 :p1 ((:a) (:b)) . :a :q 1 . :b :q 2 .', 'n1', 'S1', True,
     'a sequence of one-element sequences', [f'{J}.nested_collections', f'{V} "nests"']),
    ('collNested_pairInside_fail', 'collNested', ':n1 :p1 ((:a :b)) . :a :q 1 . :b :q 2 .', 'n1', 'S1', False,
     'the inner sequence has two elements, not one', [f'{J}.nested_collections']),
    ('collNested_flat_fail', 'collNested', ':n1 :p1 (:a) . :a :q 1 .', 'n1', 'S1', False,
     'the elements are not sequences', [f'{J}.nested_collections']),
    ('collDot_empty_pass', 'collDot', ':n1 :p1 () .', 'n1', 'S1', True, '((.)) matches the empty sequence', [f'{W} "rdf-array: anything" with ()']),
    ('collDot_mixed_pass', 'collDot', ':n1 :p1 (1 :x "s" (2)) .', 'n1', 'S1', True, '((.)) matches any elements, sequences included', [f'{V} "is none of the node kinds, but matches `.`"']),
    ('collDot_notSeq_fail', 'collDot', ':n1 :p1 "s" .', 'n1', 'S1', False, '((.)) wants a sequence', [f'{W} "rdf-array: anything" with a non-sequence']),
    ('collIriOrInt_pass', 'collIriOrInt', ':n1 :p1 (:x 1 :y) .', 'n1', 'S1', True, 'IRI OR xsd:integer inside a Collection', [f'{V} (parser) "takes a shape expression of any kind"']),
    ('collIriOrInt_string_fail', 'collIriOrInt', ':n1 :p1 (:x "1") .', 'n1', 'S1', False, 'a string is neither an IRI nor an integer', []),
    ('collNotInt_pass', 'collNotInt', ':n1 :p1 (:x "1") .', 'n1', 'S1', True, 'NOT xsd:integer inside a Collection', []),
    ('collNotInt_fail', 'collNotInt', ':n1 :p1 (:x 1) .', 'n1', 'S1', False, 'an integer element fails NOT xsd:integer', []),
    ('collValueIri_seq_fail', 'collValueIri', ':n1 :p1 (:x) .', 'n1', 'S1', False, 'a sequence is not an IRI (a sequence is none of the node kinds)', [f'{V} "is none of the node kinds, but matches `.`"']),
    ('collColour_red_pass', 'collColour', '<http://a.example/red> :rgb (255 0 0) .', 'red', 'Colour', True, 'three bytes', [f'{W} "red"']),
    ('collColour_pink_fail', 'collColour', '<http://a.example/pink> :rgb (255 192) .', 'pink', 'Colour', False, 'only two components', [f'{W} "pink has only two components"']),
    ('collColour_overflow_fail', 'collColour', '<http://a.example/hot> :rgb (256 0 0) .', 'hot', 'Colour', False, '256 is not a byte', []),
    ('collPolygon_triangle_pass', 'collPolygon', '<http://a.example/triangle> :points ((0.0 0.0) (4.0 0.0) (0.0 3.0)) .', 'triangle', 'Polygon', True, 'three points of two decimals', [f'{W} "a triangle"']),
    ('collPolygon_line_fail', 'collPolygon', '<http://a.example/line> :points ((0.0 0.0) (4.0 0.0)) .', 'line', 'Polygon', False, 'two points are too few', []),
    ('collPolygon_badPoint_fail', 'collPolygon', '<http://a.example/bent> :points ((0.0 0.0) (4.0) (0.0 3.0)) .', 'bent', 'Polygon', False, 'a point with one coordinate', []),
    ('collPlaylist_pass', 'collPlaylist', '<http://a.example/mix> :title "Monday" ; :tracks (<http://a.example/t1> <http://a.example/t2>) .\n<http://a.example/t1> :title "Intro" ; :seconds 95 .\n<http://a.example/t2> :title "Outro" ; :seconds 210 .', 'mix', 'Playlist', True, 'two tracks', [f'{W} "two tracks"']),
    ('collPlaylist_badTrack_fail', 'collPlaylist', '<http://a.example/mix> :title "Monday" ; :tracks (<http://a.example/t1> <http://a.example/t2>) .\n<http://a.example/t1> :title "Intro" ; :seconds 95 .\n<http://a.example/t2> :title "Outro" .', 'mix', 'Playlist', False, 'the second track has no :seconds', []),
    ('collDecl_pass', 'collDecl', ':n1 :p1 (:x :y) .', 'n1', 'S1', True, 'a declared Collection referenced from a triple constraint', []),
    ('collDecl_empty_fail', 'collDecl', ':n1 :p1 () .', 'n1', 'S1', False, 'the declared Collection needs one or more', []),
]

NEGATIVE_SYNTAX = [
    ('collBoundsStar', ':S1 { :p1 ((.))[*] }', 'a lone * is not a minimum'),
    ('collBoundsNoComma', ':S1 { :p1 ((.))[1 2] }', 'the bounds need a comma'),
    ('collBoundsNoMin', ':S1 { :p1 ((.))[,1] }', 'the minimum is required'),
    ('collBoundsThree', ':S1 { :p1 ((.))[1, 2, 3] }', 'at most two bounds'),
    ('collBoundsEmpty', ':S1 { :p1 ((.))[] }', 'empty bounds'),
    ('collBoundsUnclosed', ':S1 { :p1 ((.))[1 }', 'the bounds are not closed'),
]
NEG_DUP = [f'{V.replace("shex-validator", "shex-parser")} "rejects malformed bounds"']


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def write(path, text):
    path = ROOT / path
    old = path.read_text(encoding='utf-8') if path.exists() else None
    if old == text:
        return False
    if CHECK:
        raise SystemExit(f'{path.relative_to(ROOT)} would change')
    path.write_text(text, encoding='utf-8')
    return True


def shexjs_validate(schema, data, focus, shape):
    r = run(['node', SHEXJS / 'packages/shex-cli/bin/validate', '-x', schema, '-d', data, '-s', shape, '-n', focus])
    return r.returncode == 0


def jena(cmd):
    cp = (JT / 'cp.txt').read_text().strip()
    return run([JAVA, '-cp', f'{JT}:{cp}', 'JenaArray', *cmd])


def main():
    changed = []
    for name, (comment, text) in SCHEMAS.items():
        changed += [f'schemas-contrib/{name}.shex'] if write(f'schemas-contrib/{name}.shex', text) else []
        j = run(['node', SHEXJS / 'packages/shex-cli/bin/shex-to-json', ROOT / f'schemas-contrib/{name}.shex'])
        t = run(['node', SHEXJS / 'packages/shex-cli/bin/shex-to-turtle', ROOT / f'schemas-contrib/{name}.shex'])
        if j.returncode or t.returncode:
            raise SystemExit(f'shex.js-array cannot convert {name}: {j.stderr or t.stderr}')
        changed += [f'schemas-contrib/{name}.json'] if write(f'schemas-contrib/{name}.json', json.dumps(json.loads(j.stdout), indent=2) + '\n') else []
        changed += [f'schemas-contrib/{name}.ttl'] if write(f'schemas-contrib/{name}.ttl', t.stdout) else []
    problems = []
    for name, schema, data, focus, shape, ok, comment, dups in VALIDATION:
        dfile = f'validation-contrib/{name}.ttl'
        changed += [dfile] if write(dfile, D + data + '\n') else []
        f, s = f'http://a.example/{focus}', f'http://a.example/{shape}'
        verdicts = {
            'shex.js-array': shexjs_validate(ROOT / f'schemas-contrib/{schema}.shex', ROOT / dfile, f, s),
            'jena-array ShExC': jena(['shex', ROOT / f'schemas-contrib/{schema}.shex', ROOT / dfile, f, s]).stdout.strip() == 'conformant',
            'jena-array ShExR': jena(['shex', ROOT / f'schemas-contrib/{schema}.ttl', ROOT / dfile, f, s, 'http://a.example/']).stdout.strip() == 'conformant',
        }
        wrong = [k for k, v in verdicts.items() if v != ok]
        if wrong:
            problems.append(f'{name}: expected {"pass" if ok else "fail"}, {", ".join(wrong)} disagree')
    for name, text, comment in NEGATIVE_SYNTAX:
        nfile = f'negativeSyntax-contrib/{name}.shex'
        changed += [nfile] if write(nfile, P + text + '\n') else []
        js = run(['node', SHEXJS / 'packages/shex-cli/bin/shex-to-json', ROOT / nfile]).returncode != 0
        jn = jena(['shex', ROOT / nfile, ROOT / 'validation-contrib/collInt_empty_pass.ttl', 'http://a.example/n1', 'http://a.example/S1']).returncode != 0
        if not (js and jn):
            problems.append(f'{name}: not rejected by {"" if js else "shex.js-array "}{"" if jn else "jena-array"}')
    if problems:
        raise SystemExit('cross-check failed:\n  ' + '\n  '.join(problems))
    changed += write_manifests()
    dup = {'suite': 'shexTest-contrib', 'tests': [
        {'test': f'validation-contrib/manifest#{n}', 'duplicates': d} for n, *_rest, d in VALIDATION if d] + [
        {'test': f'negativeSyntax-contrib/manifest#{n}', 'duplicates': NEG_DUP} for n, *_ in NEGATIVE_SYNTAX]}
    changed += ['duplicates.json'] if write('duplicates.json', json.dumps(dup, indent=1) + '\n') else []
    print(f'{len(SCHEMAS)} schemas, {len(VALIDATION)} validation and {len(NEGATIVE_SYNTAX)} negative-syntax tests, '
          f'cross-checked by shex.js-array and jena-array (ShExC and ShExR); {len(changed)} files written')


HEAD = '''@base <{base}{dir}/manifest> .
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix mf:     <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix sht:    <http://www.w3.org/ns/shacl/test-suite#> .
@prefix sx:     <https://shexspec.github.io/shexTest/ns#> .
@prefix ra:     <https://rdf-array.github.io/rdf-array/vocab#> .

# Generated by bin/build.py -- edit the case table there.
'''


def entries(names):
    return '    mf:entries (\n' + ''.join(f'        <#{n}>\n' for n in names) + '    ) .\n'


def write_manifests():
    out = []
    s = HEAD.format(base=BASE, dir='schemas-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array representation tests: the Collection shape expression in ShExC, ShExJ and ShExR" ;\n' + entries(SCHEMAS)
    for name, (comment, _) in SCHEMAS.items():
        s += f'''
<#{name}> a sht:RepresentationTest ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires ra:CollectionShapeExpression ;
    sx:shex <{name}.shex> ;
    sx:json <{name}.json> ;
    sx:ttl <{name}.ttl> ;
    .
'''
    out += ['schemas-contrib/manifest.ttl'] if write('schemas-contrib/manifest.ttl', s) else []
    v = HEAD.format(base=BASE, dir='validation-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array validation tests: sequences against Collection shape expressions" ;\n' + entries(n for n, *_ in VALIDATION)
    for name, schema, data, focus, shape, ok, comment, dups in VALIDATION:
        v += f'''
<#{name}> a sht:{"ValidationTest" if ok else "ValidationFailure"} ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires ra:CollectionShapeExpression ;
    mf:action [
      sht:schema <../schemas-contrib/{schema}.shex> ;
      sht:shape <http://a.example/{shape}> ;
      sht:data <{name}.ttl> ;
      sht:focus <http://a.example/{focus}>
    ]
    .
'''
    out += ['validation-contrib/manifest.ttl'] if write('validation-contrib/manifest.ttl', v) else []
    n = HEAD.format(base=BASE, dir='negativeSyntax-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array negative syntax tests: malformed Collection bounds" ;\n' + entries(n for n, *_ in NEGATIVE_SYNTAX)
    for name, text, comment in NEGATIVE_SYNTAX:
        n += f'''
<#{name}> a sht:NegativeSyntax ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires ra:CollectionShapeExpression ;
    sx:shex <{name}.shex> ;
    .
'''
    out += ['negativeSyntax-contrib/manifest.ttl'] if write('negativeSyntax-contrib/manifest.ttl', n) else []
    gen = ROOT.parent / 'shexTest-array' / 'bin' / 'genJSON.js'
    for d in ('schemas-contrib', 'validation-contrib', 'negativeSyntax-contrib'):
        if gen.exists():
            r = run(['node', gen, 'manifest.ttl'], cwd=ROOT / d)
            if r.returncode == 0 and write(f'{d}/manifest.jsonld', r.stdout):
                out.append(f'{d}/manifest.jsonld')
    return out


if __name__ == '__main__':
    main()
