# Release verification keys

`kde-plasma-release.asc` contains only the Plasma 6.7.5 release manager's primary
key and its bound subkeys, exported with GnuPG's `export-minimal` option.

- Fingerprint authority: [official Plasma 6.7.5 release page](https://kde.org/info/plasma-6.7.5/).
- Retrieved keyring: [KDE Plasma release managers](https://kde.org/info/plasma-signing-keys.pgp).
- Required primary fingerprint: `0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D`.
- Retained armored key SHA-256: `b4007ced96841a5553d670dd63130df97e6faa9b47d151b842a810ebe5ea9917`.
- Retrieved on 2026-10-04. This is a public verification key, with no private material.

Repository policy checks that the retained key has this primary fingerprint.
Materialization then requires a valid detached signature belonging to that
primary key and the separately pinned release tarball SHA-256. An unrelated
Frameworks keyring must not substitute for the Plasma release key.
