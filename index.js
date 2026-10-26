// The corpus directories, for implementations that depend on this repository
// ("shex-test-contrib": "github:rdf-array/shexTest-contrib#main").
const path = require("path");
module.exports = {
  schemas: path.join(__dirname, "schemas-contrib/"),
  validation: path.join(__dirname, "validation-contrib/"),
  negativeSyntax: path.join(__dirname, "negativeSyntax-contrib/"),
};
