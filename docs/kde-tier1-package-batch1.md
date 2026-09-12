# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **CLOSED PASS — KCodecs, KDBusAddons and ThreadWeaver are 3/3 PASS**

Last reviewed: **2026-09-12**

## Scope

Batch 1 generalized the Attica hosted package path for three independent Tier 1 nodes:

- `kcodecs`;
- `kdbusaddons`;
- `threadweaver`.

All depend only on the retained ECM `6.30.0-0supralinux3` PASS root. KDE upstream remains authority; Ubuntu/Debian package trees are compatibility references.

## Attempt 1 — three real FAILs

Commit `50611225422b05803ee49d8d5fc8ff4f84a21d99`, run `34709829162`.

All three were attempted. The common failure was a SupraLINUX-invented full-tree `reuse lint` executed before KDE's real autotests. KDE does not define that full-tree gate as a build requirement. No KDE autotest result is claimed for attempt 1.

## Attempt 2 — tests PASS, package gates still FAIL

Commit `3fa96423bb01b8a7cd63a62ab5947cf7ef57b482`, run `34710627400`.

- KCodecs: 8/8 tests PASS, then `dpkg-gensymbols` exposed a stale Ubuntu 6.24 baseline.
- KDBusAddons: 3/3 tests PASS, binary build completed, then the SupraLINUX Multi-Arch normalization/checking and watch-key metadata required correction.
- ThreadWeaver: 8/8 tests PASS, binary build completed, with the same packaging-contract issues.

These remain real historical FAILs because their package attempts did not complete the whole gate.

## Attempt 3

Commit `c4de13b66184cb3b84283f1c4c5f0668f577b0de`, run `34713034164`.

### KDBusAddons — PASS

- revision `6.30.0-0supralinux3`;
- job `103605147881`;
- artifact `10304340428`;
- artifact SHA-256 `2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799`;
- tests **3/3 PASS**;
- Lintian error gate PASS;
- SONAME `libKF6DBusAddons.so.6`;
- consumer smoke PASS;
- downstream eligible.

### ThreadWeaver — PASS

- revision `6.30.0-0supralinux3`;
- job `103605147772`;
- artifact `10303986419`;
- artifact SHA-256 `6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8`;
- tests **8/8 PASS**;
- Lintian error gate PASS;
- SONAME `libKF6ThreadWeaver.so.6`;
- consumer smoke PASS;
- downstream eligible.

### KCodecs — FAIL at Lintian

KCodecs built and passed **8/8 tests**, but Lintian correctly rejected 15 newly emitted `std::format`/Unicode implementation symbols whose automatically generated minimum version included the Debian revision.

The solution was not to hide the symbols. They were reviewed as compiler/libstdc++ implementation details and retained as `(optional=toolchain)` with upstream minimum `6.30.0`.

## Attempt 4 — KCodecs PASS

Commit `6c156b6a1dc0fc9e6c9e43eae90c3da86f6b0cb9`, run `34716761551`.

- revision `6.30.0-0supralinux4`;
- job `103615297758`;
- artifact `10305050385`;
- artifact SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`;
- tests **8/8 PASS**;
- Lintian error gate PASS;
- SONAME `libKF6Codecs.so.6`;
- consumer smoke PASS;
- `.buildinfo` proves ECM `6.30.0-0supralinux3`;
- downstream eligible.

KCodecs retained package hashes include runtime `.deb` `66b34b1ec140e1942d906c4e8537661bd540f959277e41de9a772e1e0956be13`, development `.deb` `87be51ba7f3ea8813e1ce61b3c6975b312db9c62d24f41e0909edb4d344f92dd`, data `.deb` `70f2197d5fa6f475d2d414ef9a13a3e885bceee73e7dcf95983f3a3313565c24`, `.buildinfo` `b7b76708384495225491b58067c10547c5c29ab66282bca3371ac2069c649ff6`, `.dsc` `50d5e17652c58fab76fc3c7c4e3f765e14df744487d8600bf2950e68d5403ce4` and rootfs `b0bcb87ff643d730940cbd267745cf18e868e01f64e7270d0ddeb2e348c950cf`.

## Infrastructure scope incident

The same run `34716761551` selected KDBusAddons and ThreadWeaver unnecessarily because the first semantic fingerprint considered descriptive campaign metadata that the runner does not consume.

- KDBusAddons job `103615297686`, artifact `10305410248`, SHA-256 `ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a`.
- ThreadWeaver job `103615297757`, artifact `10304955612`, SHA-256 `79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507`.

Both stopped at `campaign-validation` with `got PASS`, before source-package assembly or `sbuild`. They are **infrastructure scope** failures, not package attempts and not Framework FAIL states. Their previous PASS evidence remains canonical.

The corrected scope compares only build inputs actually consumed by the runner. State, evidence, PASS file hashes and descriptive metadata do not trigger a rebuild.

## Closure

Batch 1 is **3/3 PASS**. Together with Attica, the canonical Tier 1 state is **4 Tier 1 PASS, 25 pending, 0 current FAIL, 0 BLOCKED**.

The next batch may proceed independently from the remaining 25 Tier 1 nodes.
