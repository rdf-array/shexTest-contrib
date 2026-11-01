# shexTest-contrib

ShEx tests that every [rdf-array](https://github.com/rdf-array/rdf-array) ShEx implementation can share, but
that shexTest does not contain because they test what ShEx-array adds: the **LIST shape expression**.
`LIST ( regex )` is satisfied by a sequence term whose members, in order, match a regular expression of
shape expressions (`;`, `|`, groups and cardinalities, as in a triple expression); `LIST * x`, `LIST + x`
and `LIST {m,n} x` are short for `LIST ( x * )`, `LIST ( x + )` and `LIST ( x {m,n} )`. The syntax, its
ShExJ (`ListShape`, `Member`, `ListEachOf`, `ListOneOf`) and ShExR (`sx:ListShape`, …) are
[array-syntax.md](https://github.com/rdf-array/rdf-array/blob/rdf-sequences/docs/array-syntax.md) §2 and §7 of
rdf-array/rdf-array; they replaced the `((shapeExpr))[min, max]` Collection strawman on 2026-10-31. Every
test using LIST says so with `mf:requires ra:ListShapeExpression`; the one test with a sequence but no LIST
(`seqValueIri`) requires `ra:Sequences`. Published at <https://rdf-array.github.io/shexTest-contrib/>.

The layout follows shexTest's own `schemas-contrib` and `validation-contrib` directories, in the same
manifest vocabulary, so the same runners walk it: point a shexTest runner at this checkout
(shex.js: `TESTSDIR=path/to/shexTest-contrib`, whose `ValidationContrib-test.js` runs `validation-contrib`).

| Directory | Tests |
|---|---|
| [schemas-contrib](schemas-contrib/manifest.ttl) | 22 schemas, each in ShExC, ShExJ and ShExR (representation tests): the shorthand forms, nesting, `.`, `NOT`/`OR` members, a declared LIST, and array-syntax.md §4.2's tuples, matrices, polyline, repeated group, choice and recursive tree (`listMatrix2x3` and `listMatrix2x3Short`, `listRagged` and `listRaggedShort` have identical ShExJ) |
| [validation-contrib](validation-contrib/manifest.ttl) | 56 validation tests: cardinalities, member shapes, nesting, and §4.2's data (`obs1`–`3`, `m1`, `m2`, `poly`, `kv`, `tree`) with its verdicts |
| [negativeSyntax-contrib](negativeSyntax-contrib/manifest.ttl) | what the LIST grammar rejects: a bare `LIST x`, `LIST ( )`, a group followed by `AND`, commas, `LIST` after `EXTENDS`, the former `((x))[m, n]` |

The manifests' `@base` is shexTest's conventional `https://raw.githubusercontent.com/shexSpec/shexTest/master/<dir>/manifest`,
as in shexTest's own contrib directories, because shexTest's `bin/genJSON.js` and the runners derive file
paths from it; only relative resolution depends on it.

## How the expectations were made

[bin/build.py](bin/build.py) holds every case and writes every file. Each schema's ShExJ and ShExR forms come
from shex.js-array. Each validation case is run by shex.js-array and by jena-array, the latter against both the
ShExC and the ShExR form, and every run must give the expected verdict; each negative case must be rejected
by both parsers. One question the two implementations answered differently under the old syntax is still
left out: a minimum above the maximum, `LIST {3,1} x`.

When the syntax was adopted no implementation read it, so the first `.json` and `.ttl` files came from
rdf-array's array-syntax harness. `python3 bin/build.py --check` now runs against shex.js-array and jena-array
and reproduces every one of those files and verdicts unchanged.
[contrib-duplicates.md](https://github.com/rdf-array/rdf-array/blob/rdf-sequences/management/contrib-duplicates.md) in
rdf-array/rdf-array lists which implementation test each case reproduces.

## Using it from JavaScript

`package.json` makes the repository an npm dependency (`"shex-test-contrib": "github:rdf-array/shexTest-contrib#rdf-sequences"`);
`require("shex-test-contrib")` gives the paths of `schemas-contrib/`, `validation-contrib/` and
`negativeSyntax-contrib/`. [shex.js-array](https://github.com/rdf-array/shex.js-array) runs it that way.

