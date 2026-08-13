# `official/gui`

Standalone home for Toka's official GUI package.

## Migration status

This repository is a migration scaffold and is not yet the canonical package
source. Until standalone qualification, release, and registry consumer replay
are complete, the authoritative source remains
[`tokalang/toka/official/gui`](https://github.com/tokalang/toka/tree/main/official/gui).

Cutover will be one-way. The compiler repository copy will be removed after a
successful standalone release; this repository will not become a long-lived
mirror or submodule. GUI qualification must use an explicit installed SDK or
`TOKA`, `TOKAC`, and `TOKA_LIB` inputs.

## License

Apache License 2.0. See [LICENSE](LICENSE). Migrated native dependencies and
assets must retain their applicable third-party notices and licenses.
Official GUI package for Toka
