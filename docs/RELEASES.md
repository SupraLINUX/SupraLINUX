# SupraLINUX Releases

## Versioning model

SupraLINUX uses `MAJOR.MINOR.PATCH` internally.

- `PATCH`: fixes and integration/security corrections within a release line.
- `MINOR`: meaningful feature/integration releases within the same generation/base when practical.
- `MAJOR`: new generation, normally aligned with a new Ubuntu LTS base or another compatibility boundary large enough to justify it.

Public UI may emphasize a shorter form such as `SupraLINUX 1.0 - Aurora`, while diagnostics and release metadata retain the complete technical version, for example `1.0.3`.

## Generation 1 — Aurora

- Codename: **Aurora**
- Base: Ubuntu 26.04 LTS
- Initial version: `1.0.0`
- Full initial release identity: **SupraLINUX 1.0.0 - Aurora**

Public-facing style may use:

```text
SupraLINUX 1.0 - Aurora
```

The codename identifies the generation and does not replace the numeric version used for packaging, diagnostics, upgrades, or repository logic.
