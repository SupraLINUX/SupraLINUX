# KDE Tier 2 package contracts

Status: **reference capture PASS; deterministic rematerialization pending**  
Date: **2026-09-20**

The first contract batch contains KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. All five already passed the Ubuntu Resolute provider audit and remain package-state `pending`.

Ubuntu 26.04 and Debian packaging are a **technical reference** only. KDE upstream 6.30.0 defines the actual feature/API contract; SupraLINUX owns the package contract.

Compatibility source/binary names are preserved where Ubuntu already exposes them. KNotifications also preserves the QML split because upstream builds that surface when a QML provider is available.

Upstream 6.30.0 enables Python bindings on Linux for KNotifications, KStatusNotifierItem and KUnitConversion. Ubuntu's current source packages do not expose corresponding Python binary packages, so SupraLINUX must not silently disable the feature. The draft adds:
- `python3-kf6notifications` providing module `KNotifications`;
- `python3-kf6statusnotifieritem` providing module `KStatusNotifierItem`;
- `python3-kf6unitconversion` providing module `KUnitConversion`.

The reference-capture workflow records the current Ubuntu Resolute and Debian sid source records, Build-Depends, binary sets and source-file SHA-256 values. This stage is **not a package PASS** and does not authorize publication.


## Pinned reference evidence

Run `35525532348`, job `106116905607`: **PASS**. Artifact `10609796320`, SHA-256 `0d5d1f961e0189190505545aedca169dc0180ed1d9e189a5eca021267a8385e3`. The normalized snapshot SHA-256 is `5bfdf1238cedc31ccda2a3f3c93459911709b3e7650eb40c129354f42d0286e9`.

Ubuntu Resolute references are `6.24.0-0ubuntu1`; Debian sid references are `6.30.0-1`. Exact `.dsc`, `.debian.tar.xz` and `.orig.tar.xz` SHA-256 values are pinned in the manifest.

Four Debian 6.30 orig tarballs match the KDE upstream source SHA exactly. Syndication does not: Debian's referenced orig SHA is `fb46986bd539f49dc39c79553c4e8e9eaeb5953efa8cba1b47d3b139ee54f5af`, while KDE's official 6.30.0 source SHA is `2d44e45b05766d342d3fe19e92d2b039c916a7a83f9e4dff0f9fa15860e140ee`. SupraLINUX therefore rejects the Debian Syndication orig tarball as a source input and may use only its pinned Debian packaging tree as a technical reference.


### Reference-gate revalidation

After pinning the source-authority mismatch policy, run `35525757861`, job `106117497527`, revalidated the reference capture as **PASS**. Artifact `10610520138`, SHA-256 `987ca77884695296ee6d21a841f428f16ed49fb8b103b84a84db8c735ceac9e9`. Its normalized `snapshot.json` and `versions.tsv` are byte-identical to the initial PASS snapshot, so this second run is the canonical current evidence.


## Resolute packaging-tooling adaptation

The first clean-build Batch 2 run, `35530953084`, exposed a shared provider/tooling incompatibility before any of the four affected Frameworks compiled: Debian's 6.30 technical-reference trees request `debhelper-compat (= 14)`, while Ubuntu 26.04 Resolute provides the debhelper 13 compatibility surface used by the SupraLINUX base.

Because Debian is a technical reference rather than packaging authority, SupraLINUX now normalizes this field to `debhelper-compat (= 13)` during deterministic materialization. The transformation is explicit in the contract manifest and generated materialization metadata. It does not change KDE-selected CMake options, Python bindings, QML surfaces, X11/DBus choices, tests, ABI targets, or any other KDE feature decision.

The prior 5/5 materialization PASS from run `35527533481` remains preserved as historical evidence, but its trees are superseded for build consumption. The five package contracts return temporarily to `package-contract-ready` until CI produces and pins replacement source trees. This transition does not alter package state: all five remain `pending`.
