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

The LIST syntax (rdf-array's docs/array-syntax.md §2, its ShExJ and ShExR §7) replaced the
((shapeExpr))[min, max] strawman on 2026-10-31. The first .json and .ttl files of that rewrite came
from the array-syntax harness parser; this script, run against shex.js-array and jena-array, then
reproduced them unchanged.

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
LIST, SEQ = 'ra:ListShapeExpression', 'ra:Sequences'
# name: comment, ShExC, requirement (what a test of the schema needs beyond ShEx)
SCHEMAS = {
    'listRef1to2': ('a sequence of one or two nodes, each with an integer :q',
                    P + ':T { :q xsd:integer }\n\n:S1 { :p1 LIST {1,2} @:T }\n', LIST),
    'listInt': ('a sequence of any length (empty included) of integers', P + ':S1 { :p1 LIST * xsd:integer }\n', LIST),
    'listInt2': ('a sequence of exactly two integers', P + ':S1 { :p1 LIST {2} xsd:integer }\n', LIST),
    'listInt1Plus': ('a sequence of one or more integers', P + ':S1 { :p1 LIST + xsd:integer }\n', LIST),
    'listNested': ('a non-empty sequence of one-member sequences of nodes with an integer :q',
                   P + ':T { :q xsd:integer }\n\n:S1 { :p1 LIST + LIST {1} @:T }\n', LIST),
    'listDot': ('a sequence of any length of anything', P + ':S1 { :p1 LIST * . }\n', LIST),
    'listIriOrInt': ('a non-empty sequence whose members are IRIs or integers: a parenthesised member',
                     P + ':S1 { :p1 LIST + ( IRI OR xsd:integer ) }\n', LIST),
    'listNotInt': ('a sequence of any length none of whose members is an integer', P + ':S1 { :p1 LIST * ( NOT xsd:integer ) }\n', LIST),
    'seqValueIri': ('an IRI value constraint is not satisfied by a sequence', P + ':S1 { :p1 IRI }\n', SEQ),
    'listColour': ('a colour is a sequence of exactly three bytes: the member is a datatype with facets',
                   P + ':Colour { :rgb LIST {3} xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 255 }\n', LIST),
    'listPolygon': ('a polygon is three or more points, each a sequence of two decimals',
                    P + ':Polygon { :points LIST {3,} LIST {2} xsd:decimal }\n', LIST),
    'listPlaylist': ('a playlist is a title and one or more tracks, in order',
                     P + ':Playlist { :title xsd:string ; :tracks LIST + @:Track }\n\n'
                         ':Track { :title xsd:string ; :seconds xsd:integer }\n', LIST),
    'listDecl': ('a shape declaration whose shape expression is a LIST',
                 P + ':L LIST + IRI\n\n:S1 { :p1 @:L }\n', LIST),
    # docs/array-syntax.md §4.2: the LIST ( regex ) form on nested data
    'listBP': ('a non-empty list of components, each a code, a name and an (integer unit) pair: LIST ( ; ) tuples',
               P + ':Observation { :component @:BP }\n\n:BP LIST + @:Component\n\n'
                   ':Component LIST ( xsd:string ; xsd:string ; LIST ( xsd:integer ; xsd:string ) )\n', LIST),
    'listMatrix2x3': ('a 2x3 matrix: two rows of three integers, as nested member regular expressions',
                      P + ':Matrix { :matrix @:Matrix2x3 }\n\n:Matrix2x3 LIST ( LIST ( xsd:integer {3} ) {2} )\n', LIST),
    'listMatrix2x3Short': ('the same 2x3 matrix with the cardinality-first shorthand: the same ShExJ as listMatrix2x3',
                           P + ':Matrix { :matrix @:Matrix2x3 }\n\n:Matrix2x3 LIST {2} LIST {3} xsd:integer\n', LIST),
    'listRagged': ('a ragged list of lists of integers', P + ':Matrix { :matrix @:Ragged }\n\n:Ragged LIST ( LIST ( xsd:integer * ) * )\n', LIST),
    'listRaggedShort': ('the same ragged list with the shorthand: the same ShExJ as listRagged',
                        P + ':Matrix { :matrix @:Ragged }\n\n:Ragged LIST * LIST * xsd:integer\n', LIST),
    'listPolyline': ('a polyline: two or more (x y) points',
                     P + ':Points { :points @:Polyline }\n\n:Matrix { :matrix @:Polyline }\n\n'
                         ':Polyline LIST ( LIST ( xsd:integer ; xsd:integer ) {2,} )\n', LIST),
    'listPairs': ('a flat key/value list: a repeated (string ; integer) group, which nested LISTs cannot say',
                  P + ':KeyValues { :pairs @:Pairs }\n\n:Points { :points @:Pairs }\n\n'
                      ':Pairs LIST ( ( xsd:string ; xsd:integer ) * )\n', LIST),
    'listIntsOrPairs': ('members that are each an integer or an (x y) pair: a choice among members',
                        P + ':Points { :points @:IntsOrPairs }\n\n:Matrix { :matrix @:IntsOrPairs }\n\n'
                            ':IntsOrPairs LIST ( ( xsd:integer | LIST ( xsd:integer ; xsd:integer ) ) + )\n', LIST),
    'listTree': ('a tree is a (label children) pair whose children are trees: recursion through two LISTs',
                 P + ':Node { :node @:Tree }\n\n:Matrix { :matrix @:Tree }\n\n'
                     ':Tree LIST ( xsd:string ; LIST ( @:Tree * ) )\n', LIST),
}

D = 'PREFIX : <http://a.example/>\n\n'
J = 'jena-array jena-shex TestShexList'
V = 'shex.js-array packages/shex-validator/test/ListShape-test.js'
W = 'shex.js-array packages/shex-webapp/examples/manifest.json'
OBS1 = ':obs1 :component ( ( "8480-6" "systolic" ( 120 "mm[Hg]" ) ) ( "8462-4" "diastolic" ( 80 "mm[Hg]" ) ) ) .'
OBS2 = ':obs2 :component ( ( "8480-6" "systolic" ( 150 "mm[Hg]" ) ) ( "8462-4" "diastolic" ( 95 "mm[Hg]" ) ) ) .'
OBS3 = ':obs3 :component ( ( "8480-6" "systolic" ( "high" "mm[Hg]" ) ) ) .'
M1, M2 = ':m1 :matrix ( ( 1 2 3 ) ( 4 5 6 ) ) .', ':m2 :matrix ( ( 1 2 3 ) ( 4 5 ) ) .'
POLY, KV = ':poly :points ( ( 0 0 ) ( 3 0 ) ( 3 4 ) ) .', ':kv :pairs ( "a" 1 "b" 2 "c" 3 ) .'
TREE = ':tree :node ( "root" ( ( "left" ( ) ) ( "right" ( ( "leaf" ( ) ) ) ) ) ) .'
# name, schema, data, focus, shape, conformant?, comment, duplicates
VALIDATION = [
    ('listRef1to2_two_pass', 'listRef1to2', ':n1 :p1 (:a :b) . :a :q 1 . :b :q 2 .', 'n1', 'S1', True,
     'each member satisfies the member shape', [f'{V} "accepts a sequence of the right length whose members conform"']),
    ('listRef1to2_one_pass', 'listRef1to2', ':n1 :p1 (:a) . :a :q 1 .', 'n1', 'S1', True,
     'one member is within {1,2}', []),
    ('listRef1to2_three_fail', 'listRef1to2', ':n1 :p1 (:a :b :c) . :a :q 1 . :b :q 2 . :c :q 3 .', 'n1', 'S1', False,
     'three members exceed {1,2}', [f'{V} "counts the members"']),
    ('listRef1to2_empty_fail', 'listRef1to2', ':n1 :p1 () .', 'n1', 'S1', False,
     'the empty sequence is below {1,2}', [f'{V} "counts the members"']),
    ('listRef1to2_badMember_fail', 'listRef1to2', ':n1 :p1 (:a :b) . :a :q 1 . :b :q "two" .', 'n1', 'S1', False,
     'the second member fails the member shape', [f'{V} "reports every member that fails, by index"', f'{V} "follows shape references from the members"']),
    ('listRef1to2_notSeq_fail', 'listRef1to2', ':n1 :p1 :a . :a :q 1 .', 'n1', 'S1', False,
     'an IRI is not a sequence', [f'{J}.not_a_sequence', f'{V} "wants a sequence"']),
    ('listInt_literal_fail', 'listInt', ':n1 :p1 1 .', 'n1', 'S1', False,
     'a literal is not a sequence', [f'{J}.not_a_sequence']),
    ('listInt_empty_pass', 'listInt', ':n1 :p1 () .', 'n1', 'S1', True,
     'LIST *: the empty sequence', [f'{J}.empty_sequences', f'{V} "accepts the empty sequence where the cardinality allows it (§5)"']),
    ('listInt_three_pass', 'listInt', ':n1 :p1 (1 2 3) .', 'n1', 'S1', True,
     'LIST *: three integers', [f'{J}.empty_sequences']),
    ('listInt_mixed_fail', 'listInt', ':n1 :p1 (1 "a") .', 'n1', 'S1', False,
     'a string member fails xsd:integer', [f'{J}.empty_sequences']),
    ('listInt2_two_pass', 'listInt2', ':n1 :p1 (1 2) .', 'n1', 'S1', True, '{2}: exactly two', []),
    ('listInt2_one_fail', 'listInt2', ':n1 :p1 (1) .', 'n1', 'S1', False, '{2}: one is too few', []),
    ('listInt2_three_fail', 'listInt2', ':n1 :p1 (1 2 3) .', 'n1', 'S1', False, '{2}: three is too many', []),
    ('listInt1Plus_empty_fail', 'listInt1Plus', ':n1 :p1 () .', 'n1', 'S1', False, 'LIST +: empty is too few', []),
    ('listInt1Plus_one_pass', 'listInt1Plus', ':n1 :p1 (1) .', 'n1', 'S1', True, 'LIST +: one', []),
    ('listInt1Plus_four_pass', 'listInt1Plus', ':n1 :p1 (1 2 3 4) .', 'n1', 'S1', True, 'LIST +: four', []),
    ('listNested_pass', 'listNested', ':n1 :p1 ((:a) (:b)) . :a :q 1 . :b :q 2 .', 'n1', 'S1', True,
     'a sequence of one-member sequences', [f'{J}.matrix_2x3', f'{V} "nests"']),
    ('listNested_pairInside_fail', 'listNested', ':n1 :p1 ((:a :b)) . :a :q 1 . :b :q 2 .', 'n1', 'S1', False,
     'the inner sequence has two members, not one', [f'{J}.matrix_2x3']),
    ('listNested_flat_fail', 'listNested', ':n1 :p1 (:a) . :a :q 1 .', 'n1', 'S1', False,
     'the members are not sequences', [f'{J}.matrix_2x3']),
    ('listDot_empty_pass', 'listDot', ':n1 :p1 () .', 'n1', 'S1', True, 'LIST * . matches the empty sequence', [f'{W} "rdf-array: a bag of anything" with ()']),
    ('listDot_mixed_pass', 'listDot', ':n1 :p1 (1 :x "s" (2)) .', 'n1', 'S1', True, 'LIST * . matches any members, sequences included', [f'{V} "is none of the node kinds, but matches `.`"']),
    ('listDot_notSeq_fail', 'listDot', ':n1 :p1 "s" .', 'n1', 'S1', False, 'LIST * . wants a sequence', [f'{W} "rdf-array: a bag of anything" with a non-sequence']),
    ('listIriOrInt_pass', 'listIriOrInt', ':n1 :p1 (:x 1 :y) .', 'n1', 'S1', True, 'IRI OR xsd:integer as the member', []),
    ('listIriOrInt_string_fail', 'listIriOrInt', ':n1 :p1 (:x "1") .', 'n1', 'S1', False, 'a string is neither an IRI nor an integer', []),
    ('listNotInt_pass', 'listNotInt', ':n1 :p1 (:x "1") .', 'n1', 'S1', True, 'NOT xsd:integer as the member', []),
    ('listNotInt_fail', 'listNotInt', ':n1 :p1 (:x 1) .', 'n1', 'S1', False, 'an integer member fails NOT xsd:integer', []),
    ('seqValueIri_fail', 'seqValueIri', ':n1 :p1 (:x) .', 'n1', 'S1', False, 'a sequence is not an IRI (a sequence is none of the node kinds)', [f'{V} "is none of the node kinds, but matches `.`"']),
    ('listColour_red_pass', 'listColour', '<http://a.example/red> :rgb (255 0 0) .', 'red', 'Colour', True, 'three bytes', [f'{W} "red"']),
    ('listColour_pink_fail', 'listColour', '<http://a.example/pink> :rgb (255 192) .', 'pink', 'Colour', False, 'only two components', [f'{W} "pink has only two components"']),
    ('listColour_overflow_fail', 'listColour', '<http://a.example/hot> :rgb (256 0 0) .', 'hot', 'Colour', False, '256 is not a byte', []),
    ('listPolygon_triangle_pass', 'listPolygon', '<http://a.example/triangle> :points ((0.0 0.0) (4.0 0.0) (0.0 3.0)) .', 'triangle', 'Polygon', True, 'three points of two decimals', [f'{W} "a triangle"']),
    ('listPolygon_line_fail', 'listPolygon', '<http://a.example/line> :points ((0.0 0.0) (4.0 0.0)) .', 'line', 'Polygon', False, 'two points are too few', []),
    ('listPolygon_badPoint_fail', 'listPolygon', '<http://a.example/bent> :points ((0.0 0.0) (4.0) (0.0 3.0)) .', 'bent', 'Polygon', False, 'a point with one coordinate', []),
    ('listPlaylist_pass', 'listPlaylist', '<http://a.example/mix> :title "Monday" ; :tracks (<http://a.example/t1> <http://a.example/t2>) .\n<http://a.example/t1> :title "Intro" ; :seconds 95 .\n<http://a.example/t2> :title "Outro" ; :seconds 210 .', 'mix', 'Playlist', True, 'two tracks', [f'{W} "two tracks"']),
    ('listPlaylist_badTrack_fail', 'listPlaylist', '<http://a.example/mix> :title "Monday" ; :tracks (<http://a.example/t1> <http://a.example/t2>) .\n<http://a.example/t1> :title "Intro" ; :seconds 95 .\n<http://a.example/t2> :title "Outro" .', 'mix', 'Playlist', False, 'the second track has no :seconds', []),
    ('listDecl_pass', 'listDecl', ':n1 :p1 (:x :y) .', 'n1', 'S1', True, 'a declared LIST referenced from a triple constraint', []),
    ('listDecl_empty_fail', 'listDecl', ':n1 :p1 () .', 'n1', 'S1', False, 'the declared LIST + needs one or more', []),
    # docs/array-syntax.md §4.2, with its verdicts
    ('listBP_obs1_pass', 'listBP', OBS1, 'obs1', 'Observation', True, 'two components, each a code, a name and an (integer unit) pair', []),
    ('listBP_obs2_pass', 'listBP', OBS2, 'obs2', 'Observation', True, 'two components, each a code, a name and an (integer unit) pair', []),
    ('listBP_obs3_fail', 'listBP', OBS3, 'obs3', 'Observation', False, "the value 'high' is a string, not an xsd:integer", []),
    ('listMatrix2x3_m1_pass', 'listMatrix2x3', M1, 'm1', 'Matrix', True, 'two rows of three', []),
    ('listMatrix2x3_m2_fail', 'listMatrix2x3', M2, 'm2', 'Matrix', False, 'the second row has two members, not three', []),
    ('listMatrix2x3Short_m1_pass', 'listMatrix2x3Short', M1, 'm1', 'Matrix', True, 'two rows of three, with the shorthand', []),
    ('listMatrix2x3Short_m2_fail', 'listMatrix2x3Short', M2, 'm2', 'Matrix', False, 'the second row has two members, not three', []),
    ('listRagged_m1_pass', 'listRagged', M1, 'm1', 'Matrix', True, 'rows of any length', []),
    ('listRagged_m2_pass', 'listRagged', M2, 'm2', 'Matrix', True, 'rows of any length, a short one included', []),
    ('listRaggedShort_m1_pass', 'listRaggedShort', M1, 'm1', 'Matrix', True, 'rows of any length, with the shorthand', []),
    ('listRaggedShort_m2_pass', 'listRaggedShort', M2, 'm2', 'Matrix', True, 'rows of any length, a short one included', []),
    ('listPolyline_poly_pass', 'listPolyline', POLY, 'poly', 'Points', True, 'three (x y) points', []),
    ('listPolyline_m1_fail', 'listPolyline', M1, 'm1', 'Matrix', False, 'rows of three integers are not (x y) pairs', []),
    ('listPairs_kv_pass', 'listPairs', KV, 'kv', 'KeyValues', True, 'three (string integer) pairs in one flat list', []),
    ('listPairs_poly_fail', 'listPairs', POLY, 'poly', 'Points', False, 'the members are sequences, not a string then an integer', []),
    ('listIntsOrPairs_poly_pass', 'listIntsOrPairs', POLY, 'poly', 'Points', True, 'every member is an (x y) pair', []),
    ('listIntsOrPairs_m1_fail', 'listIntsOrPairs', M1, 'm1', 'Matrix', False, 'a row of three is neither an integer nor a pair', []),
    ('listTree_tree_pass', 'listTree', TREE, 'tree', 'Node', True, 'a root with two children, one of them with a leaf; () is an empty list of children', []),
    ('listTree_m1_fail', 'listTree', M1, 'm1', 'Matrix', False, 'a row of integers is not a (label children) pair', []),
]

# name, ShExC after the prefixes, comment; what the grammar of docs/array-syntax.md §2.1 rejects
NEGATIVE_SYNTAX = [
    ('listBare', ':S1 { :p1 LIST xsd:integer }', 'a bare LIST x: LIST takes ( regex ) or a cardinality first'),
    ('listEmpty', ':S1 { :p1 LIST ( ) }', 'LIST ( ) needs at least one member'),
    ('listGroupThenAnd', ':S1 { :p1 LIST ( ( @:T ) AND @:U ) }', 'inside LIST ( ), ( opens a group, which AND cannot follow; write ( @:T AND @:U )'),
    ('listComma', ':S1 { :p1 LIST ( xsd:string , xsd:integer ) }', 'members are joined by ; and |, not by commas'),
    ('listAfterExtends', ':T { :q . }\n\n:S1 EXTENDS LIST + @:T { :p1 . }', 'LIST may not follow EXTENDS'),
    ('listOldBounds', ':S1 { :p1 ((xsd:integer))[1, *] }', 'the former ((x))[m, n] spelling is no longer syntax'),
]
NEG_DUP = []


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
    for name, (comment, text, req) in SCHEMAS.items():
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
        jn = jena(['shex', ROOT / nfile, ROOT / 'validation-contrib/listInt_empty_pass.ttl', 'http://a.example/n1', 'http://a.example/S1']).returncode != 0
        if not (js and jn):
            problems.append(f'{name}: not rejected by {"" if js else "shex.js-array "}{"" if jn else "jena-array"}')
    if problems:
        raise SystemExit('cross-check failed:\n  ' + '\n  '.join(problems))
    changed += write_manifests()
    changed += write_duplicates()
    print(f'{len(SCHEMAS)} schemas, {len(VALIDATION)} validation and {len(NEGATIVE_SYNTAX)} negative-syntax tests, '
          f'cross-checked by shex.js-array and jena-array (ShExC and ShExR); {len(changed)} files written')


def write_duplicates():
    dup = {'suite': 'shexTest-contrib', 'tests': [
        {'test': f'validation-contrib/manifest#{n}', 'duplicates': d} for n, *_rest, d in VALIDATION if d] + [
        {'test': f'negativeSyntax-contrib/manifest#{n}', 'duplicates': NEG_DUP} for n, *_ in NEGATIVE_SYNTAX if NEG_DUP]}
    return ['duplicates.json'] if write('duplicates.json', json.dumps(dup, indent=1) + '\n') else []


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
    s = HEAD.format(base=BASE, dir='schemas-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array representation tests: the LIST shape expression in ShExC, ShExJ and ShExR" ;\n' + entries(SCHEMAS)
    for name, (comment, _, req) in SCHEMAS.items():
        s += f'''
<#{name}> a sht:RepresentationTest ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires {req} ;
    sx:shex <{name}.shex> ;
    sx:json <{name}.json> ;
    sx:ttl <{name}.ttl> ;
    .
'''
    out += ['schemas-contrib/manifest.ttl'] if write('schemas-contrib/manifest.ttl', s) else []
    v = HEAD.format(base=BASE, dir='validation-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array validation tests: sequences against LIST shape expressions" ;\n' + entries(n for n, *_ in VALIDATION)
    for name, schema, data, focus, shape, ok, comment, dups in VALIDATION:
        v += f'''
<#{name}> a sht:{"ValidationTest" if ok else "ValidationFailure"} ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires {SCHEMAS[schema][2]} ;
    mf:action [
      sht:schema <../schemas-contrib/{schema}.shex> ;
      sht:shape <http://a.example/{shape}> ;
      sht:data <{name}.ttl> ;
      sht:focus <http://a.example/{focus}>
    ]
    .
'''
    out += ['validation-contrib/manifest.ttl'] if write('validation-contrib/manifest.ttl', v) else []
    n = HEAD.format(base=BASE, dir='negativeSyntax-contrib') + '\n<> a mf:Manifest ;\n    rdfs:comment "ShEx-array negative syntax tests: what the LIST grammar rejects" ;\n' + entries(n for n, *_ in NEGATIVE_SYNTAX)
    for name, text, comment in NEGATIVE_SYNTAX:
        n += f'''
<#{name}> a sht:NegativeSyntax ;
    mf:name "{name}" ;
    rdfs:comment "{comment}" ;
    mf:status mf:Proposed ;
    mf:requires {LIST} ;
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
