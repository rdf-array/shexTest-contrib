# shexTest-contrib

ShEx tests that every [rdf-array](https://github.com/rdf-array/rdf-array) ShEx implementation can share, but
that shexTest does not contain because they test what ShEx-array adds: the **Collection shape expression**
`((shapeExpr))[min, max]`, satisfied by a sequence term of `min`..`max` elements (`*` for unbounded) each
satisfying `shapeExpr`. That is the syntax proposed today; it is expected to change with ongoing research,
and every test using it says so with `mf:requires ra:CollectionShapeExpression`. Published at
<https://rdf-array.github.io/shexTest-contrib/>.

The layout follows shexTest's own `schemas-contrib` and `validation-contrib` directories, in the same
manifest vocabulary, so the same runners walk it: point a shexTest runner at this checkout
(shex.js: `TESTSDIR=path/to/shexTest-contrib`, whose `ValidationContrib-test.js` runs `validation-contrib`).

| Directory | Tests |
|---|---|
| [schemas-contrib](schemas-contrib/manifest.ttl) | 13 schemas, each in ShExC, ShExJ and ShExR (representation tests) |
| [validation-contrib](validation-contrib/manifest.ttl) | 37 validation tests: bounds, element shapes, nesting, `.`, `NOT`/`OR` inside a Collection, declared Collections |
| [negativeSyntax-contrib](negativeSyntax-contrib/manifest.ttl) | malformed bounds |

The manifests' `@base` is shexTest's conventional `https://raw.githubusercontent.com/shexSpec/shexTest/master/<dir>/manifest`,
as in shexTest's own contrib directories, because shexTest's `bin/genJSON.js` and the runners derive file
paths from it; only relative resolution depends on it.

## How the expectations were made

[bin/build.py](bin/build.py) holds every case and writes every file. Each schema's ShExJ and ShExR forms come
from shex.js-array. Each validation case is run by shex.js-array and by jena-array, the latter against both the
ShExC and the ShExR form, and every run must give the expected verdict; each negative case must be rejected
by both parsers. `python3 bin/build.py --check` rebuilds and fails if anything would change. One question the
two implementations answer differently is left out: bounds whose minimum exceeds the maximum,
`((x))[3, 1]`, which shex.js-array accepts and jena-array rejects.
[contrib-duplicates.md](https://github.com/rdf-array/rdf-array/blob/main/contrib-duplicates.md) in
rdf-array/rdf-array lists which implementation test each case reproduces.

## Using it from JavaScript

`package.json` makes the repository an npm dependency (`"shex-test-contrib": "github:rdf-array/shexTest-contrib#main"`);
`require("shex-test-contrib")` gives the paths of `schemas-contrib/`, `validation-contrib/` and
`negativeSyntax-contrib/`. [shex.js-array](https://github.com/rdf-array/shex.js-array) runs it that way.

