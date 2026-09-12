# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **attempts 1 and 2 are historical FAIL; remediation `-0supralinux3` prepared**  
Last reviewed: **2026-09-12**

## Scope and authority

The first generalized Tier 1 package batch contains `kcodecs`, `kdbusaddons` and `threadweaver`. They are independent KDE Frameworks 6.30 nodes whose only KDE predecessor is the retained Extra CMake Modules PASS root, so the CI matrix keeps `fail-fast: false` and attempts all three even when another fails.

KDE upstream `v6.30.0` remains authoritative for source, CMake requirements, Qt minimums, defaults and tests. Ubuntu Resolute provides compatible Qt/general dependencies and remains the application/package compatibility target. Ubuntu and Debian packaging trees are reference inputs only.

Retained inputs:

- ECM `6.30.0-0supralinux3`: run `34694951158`, artifact `10298635300`, `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- generic Tier 1 packaging trees: run `34708030450`, artifact `10301938362`, artifact SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`;
- Debian watch-v5 KDE signing key: SHA-256 `86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d`.

## Attempt 1 — real FAIL on all three nodes

Commit `50611225422b05803ee49d8d5fc8ff4f84a21d99`, workflow `34709829162`.

- KCodecs: job `103596438631`, artifact `10302917591`, SHA-256 `6fcf23a69991e453d3563d580aa63fa082c27ce8490ad52dd9e125ee41cd8f6f`.
- KDBusAddons: job `103596438606`, artifact `10303285563`, SHA-256 `2a581e9f4c01c15c611b5b3d3a98343504177f1d52fb2225f92ce3c6428f54ed`.
- ThreadWeaver: job `103596438491`, artifact `10303265649`, SHA-256 `0b47374207ae54632c4ba9594eedbcc72d46eed552696b608110ebb5bce6acb6`.

All three were genuinely attempted and are therefore FAIL, not BLOCKED. They reached `sbuild` but the SupraLINUX packaging override ran an invented full-tree `reuse lint` before KDE's real tests. **The KDE autotests did not run in attempt 1.** The REUSE gate was removed because KDE 6.30 does not define full-tree REUSE compliance as a package-build requirement.

Repository Policy run `34709829038` also independently exposed unused variables in the generic runner. That was CI infrastructure evidence, not a Framework package failure.

## Attempt 2 — KDE tests PASS, packaging still FAIL

Commit `3fa96423bb01b8a7cd63a62ab5947cf7ef57b482`, workflow `34710627400`. Repository Policy run `34710627439` was PASS.

The REUSE remediation worked: all upstream test suites ran and passed before later packaging failures.

- KCodecs: **8/8 tests PASS**; job `103598645411`, artifact `10303621032`, SHA-256 `722b83f04fadc67337129f6435547e0c9b3ad6b8b3d02655be258d86cb62e6a6`. The build then failed at `dpkg-gensymbols`: the Ubuntu Resolute 6.24 reference still required `KCharsets` C1/C2 constructors that are absent in KDE 6.30. Debian 6.28 had already removed exactly those two symbols from its reference. KDE 6.30 also introduces `std::format` in `UnicodeGroupProber`, and GCC/libstdc++ emits additional implementation/template symbols; these are non-fatal additions and are recorded rather than treated as an upstream ABI regression.
- KDBusAddons: **3/3 tests PASS** and the binary build completed; job `103598645369`, artifact `10303366682`, SHA-256 `75879797c369c29c00eb6fa647cca9958645eb80437531f7dfee42fe99327763`. The SupraLINUX contract checker then failed because `dpkg-deb -f Multi-Arch` reports an absent field as `no`, while the retained package-contract snapshot normalizes absence to `null`. The build log also exposed `debian-watch-file-pubkey-file-is-missing`; `Standards-Version: 4.7.4` was newer than Resolute's recognized 4.7.3 baseline.
- ThreadWeaver: **8/8 tests PASS** and the binary build completed; job `103598645228`, artifact `10302524114`, SHA-256 `5582b94c2e134011297a51fd02183464253c0c5f43678a79fd256f128b2f2d6f`. It hit the same Multi-Arch normalization issue and the same watch-key/Standards-Version packaging issues.

The three attempt-2 results remain historical FAIL. Passing KDE tests do not convert a failed package gate into PASS.

## Remediation `6.30.0-0supralinux3`

The third candidate keeps KDE source and tests unchanged. Only packaging contracts and metadata are corrected:

1. KCodecs selects the retained **Debian sid `kf6-kcodecs 6.28.0-1` symbols baseline**, SHA-256 `35f6b7b6885b3db41bcce95b99610b2e917e1b4e13d5ba7e801b93dd47c4f8c7`, instead of the stale Ubuntu 6.24 symbols baseline. Debian remains a reference provider, not an authority over KDE.
2. The generic runner selects the symbols tree explicitly from the campaign manifest; KDBusAddons and ThreadWeaver continue using the Ubuntu Resolute symbols references.
3. The binary-contract validator normalizes both an absent `Multi-Arch` field and `Multi-Arch: no` to the same internal `null` representation. It does **not** add `Multi-Arch: no` to package control files, preserving the established package contract.
4. Each package includes `debian/upstream/signing-key.asc`, matching the retained Debian watch-v5 metadata, instead of disabling PGP verification. Key SHA-256: `86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d`.
5. `Standards-Version` is set to `4.7.3`, the policy level recognized by the current Resolute Lintian.
6. KDE autotests remain enabled exactly as in attempt 2: KCodecs/ThreadWeaver through `dh_auto_test`, KDBusAddons inside `dbus-run-session`.
7. Lintian `--fail-on error`, SONAME checks, exact binary split/contracts, retained ECM proof and package-specific downstream CMake consumer smoke remain mandatory.

Warnings for the intentionally compatibility-only empty `*-doc` packages remain visible. KDBusAddons' missing manpage warning for `kquitapp6` also remains visible; neither is suppressed as an error workaround.

## KCodecs symbols note

The switch from Ubuntu 6.24 to Debian 6.28 is evidence-driven. The fatal difference was the pair:

- `_ZN9KCharsetsC1Ev`
- `_ZN9KCharsetsC2Ev`

Both are already absent from the Debian 6.28 symbols baseline. The selected KDE 6.30 source additionally uses `<format>` in `src/probers/UnicodeGroupProber.cpp`; the resulting libstdc++ `std::format`/Unicode implementation symbols are new, non-fatal symbol additions. SupraLINUX records them as implementation/compiler-derived output rather than inventing them as KDE public API.

## Current state before attempt 3

`kcodecs`, `kdbusaddons` and `threadweaver` are current **FAIL** package attempts with a prepared `-0supralinux3` remediation. None is BLOCKED because ECM is PASS and the nodes are independent. No node becomes downstream-eligible until the complete hosted package gate returns PASS and its evidence is recorded.
