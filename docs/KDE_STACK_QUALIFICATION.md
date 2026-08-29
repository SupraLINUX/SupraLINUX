# Aurora KDE Stack Qualification

Status: **ACTIVE — KSQ-0 CERTIFIED / KSQ-1 ACTIVE**

This gate decides which KDE stack becomes the versioned foundation for the rest of Aurora's C4 certification. Feature certification is meaningful only against the software stack that will actually ship.

C4.1 and later feature work remain paused while KDE Stack Qualification is open.

Canonical KSQ-0 acceptance: `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`.

Canonical override ownership: `docs/KDE_STACK_OVERRIDES.md`.

## 1. Existing known-good baseline

The development repository reached these milestones using Ubuntu 26.04's historical KDE stack:

- Plasma 6.6.6;
- KDE Frameworks 6.24.x;
- Qt 6.10.2 from Ubuntu;
- C1 accepted;
- C2 accepted;
- C3 accepted;
- C4.0 accepted;
- incremental C4.1 evidence accepted for the capabilities recorded in the C4 documentation.

This evidence is not discarded. It is **historical version-scoped evidence**. It may be used for regression comparison, but it must never be represented as evidence produced by the candidate KDE stack.

The Baloo compatibility launcher and C4.1b harness introduced while diagnosing the 6.6.6 baseline remain until the candidate stack proves whether they are still needed. Removing a workaround before reproducing the corresponding behavior on the new stack would destroy useful evidence.

## 2. Candidate architecture

Qualified source/dependency target as of 2026-08-29:

| Layer | Candidate owner/version |
|---|---|
| Ubuntu base | Ubuntu 26.04 LTS (`resolute`) |
| Kernel | Ubuntu |
| Mesa/libdrm | Ubuntu |
| systemd | Ubuntu |
| PipeWire/WirePlumber | Ubuntu |
| NetworkManager | Ubuntu |
| Wayland runtime | Ubuntu |
| Qt | Ubuntu Qt 6.10.2 |
| KDE Frameworks | SupraLINUX candidate 6.29.0 |
| Plasma | SupraLINUX candidate 6.7.4 |
| KWin | SupraLINUX candidate 6.7.4 |
| `plasma-wayland-protocols` | SupraLINUX backport candidate 1.21.0-1 |
| `qtkeychain` | SupraLINUX backport candidate 0.17.0-1 |
| `wayland-protocols` | SupraLINUX compatibility backport candidate 1.48-1 |
| `kwallet-pam` | 4:6.7.4-0ubuntu3 with build-only debhelper compat 14→13 adaptation and compat-13 relationship substvar restoration |
| `kf6-syntax-highlighting` | 6.29.0-0ubuntu1 plus one SupraLINUX build-time deterministic Jinja traversal patch; no intended runtime/API/content semantic change |
| KDE Gear | separate stable-version review; not adopted by KSQ-0 |

KDE upstream's current stable releases at the time of this certification are Plasma 6.7.4, Frameworks 6.29.0 and KDE Gear 26.08. Gear is intentionally evaluated independently and is not implicitly inherited from the Plasma qualification.

These are still **candidate product versions**, not a release commitment. KSQ-0 certifies that the exact source/dependency architecture is closed and compatible at the metadata/source level. KSQ-1 and later must still prove builds, repository closure, installation, upgrade, rollback and runtime behavior.

## 3. KSQ-0 certified result

KSQ-0 is **CERTIFIED** on engineering commit:

`4e7db453f626e78ca72c353ab314e16e00c9003f`

Canonical strict closure run: `33231879994`.

Canonical inventory run: `33231880014`.

Pinned Ubuntu archive snapshot: `20260829T022000Z`.

Accepted source closure:

- 101 selected source packages;
- 101 topologically ordered build nodes;
- 59 Frameworks 6.29.0 sources;
- 39 Plasma 6.7.4 sources;
- 2 KDE-adjacent explicit backports;
- 1 Ubuntu-platform compatibility backport;
- 1 explicit packaging build-dependency adaptation;
- 0 unresolved dependencies;
- 0 unresolved source/package decisions.

The strict workflow does not use `--allow-unresolved`. Any unresolved dependency, stale declared exception, source selection conflict, DAG cycle, or unconsumed policy entry fails the gate.

The three explicit source selections are:

1. `plasma-wayland-protocols 1.21.0-1` because Plasma/KWin 6.7.4 require >=1.21 while Resolute has 1.20;
2. `qtkeychain 0.17.0-1` because Plasma-NM 6.7.4 requires >=0.16 while Resolute has 0.15;
3. `wayland-protocols 1.48-1` because KWin 6.7.4 requires >=1.48 while Resolute has 1.47. Version 1.48 is deliberately used instead of widening the Wayland runtime boundary for newer packaging.

`kwallet-pam 4:6.7.4-0ubuntu3` requires one packaging-only adaptation from `debhelper-compat (= 14)` to `debhelper-compat (= 13)`. Because debhelper compat 14 automatically applies relationship substvars that compat 13 does not, KSQ-1 must also restore the explicit `${misc:Depends}`, `${qml6:Depends}` and `${shlibs:Depends}` relationships removed by the compat-14 packaging transition. This restores dependency-generation semantics only; no PAM functional file is intentionally changed. The source audit proves the PAM installation, postinst, prerm and PAM profile files are byte-identical to Debian 6.7.4-3 and retains a later installation contract checking `pam_kwallet5.so` in both `common-session` and `common-auth`.

The obsolete direct dependency/root `plasma-session-wayland` was removed because current Plasma 6.7.4 packages the Wayland session through `plasma-workspace` itself.

The later KSQ-1 Syntax Highlighting reproducibility patch does not change the 101-source dependency closure, package-selection set, or Ubuntu platform boundary. This was explicitly regression-tested after materialization: KSQ-0 closure run `33281492212` is PASS, artifact `9723122890`, digest `sha256:8a305b70965c98702122d2afc30da08474234a04e8422bd09da391f8f22396ff`. Source-inventory regression run `33281492218` is also PASS, artifact `9723114366`, digest `sha256:e380ae378d9cb2161b66557d9eaafb9ae7f8b253691b8324a9506cc19c8d75a1`. These regressions confirm that KSQ-0 remains closed rather than redefining its accepted architecture.

See `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md` for canonical KSQ-0 artifact IDs/digests and `docs/KDE_STACK_OVERRIDES.md` for maintenance/security ownership and removal conditions.

## 4. Research and provenance basis

The architecture decision is based on upstream/distribution evidence, not version-number preference alone:

- Ubuntu 26.04 provides Qt 6.10.2, matching the Qt generation required by the candidate;
- KDE Frameworks 6.29.0 remains compatible with that Qt generation;
- current Ubuntu/Kubuntu development source packaging provides a maintained packaging reference for Plasma/KWin 6.7.4 and Frameworks 6.29.0;
- the dependency graph proves a small explicit compatibility set rather than a requirement to replace kernel, Mesa, Qt or Wayland runtime;
- Ubuntu source/binary metadata is pinned to the Ubuntu Snapshot Service;
- deliberately historical Debian source inputs are addressed through Debian Snapshot immutable content identities plus pinned SHA-256 verification.

Before implementing or updating any package, current official KDE, Ubuntu and Debian/Kubuntu source metadata must be rechecked because versions and dependency relationships can move.

## 5. Packaging principles

1. Build DEBs; never install the supported KDE stack manually into `/usr/local`.
2. Use official stable KDE source tarballs/releases.
3. Prefer maintained Debian/Kubuntu packaging as the packaging base when technically valid for Resolute.
4. Record the exact packaging source/version for every source package.
5. Keep SupraLINUX patches minimal, reviewable and removable.
6. Do not enable a third-party binary repository as an undeclared runtime dependency.
7. Every intentional override must use deterministic versions and APT behavior; no blanket origin priority may accidentally override unrelated Ubuntu packages.
8. Build dependencies used only in CI/builders must not leak into product dependencies.
9. The source-package graph, not a hand-maintained list of executable names, determines what must be rebuilt.
10. Every override/backport must remain documented in `docs/KDE_STACK_OVERRIDES.md` with origin, reason, security ownership, update procedure and removal condition.
11. Build/reproducibility evidence may be reused only when source-package identity, dependency inputs, snapshot and relevant builder semantics are proven equivalent. Matching package names or versions alone are insufficient.

## 6. Platform-boundary rule

The default answer for the following remains **Ubuntu package**:

- kernel;
- firmware;
- Mesa;
- libdrm;
- systemd;
- PipeWire/WirePlumber;
- NetworkManager;
- Wayland runtime;
- Qt;
- base compiler/runtime libraries.

If a later KDE candidate/build requires replacing one of these layers, stop and open a documented architecture review. Do not silently widen the backport set until a solver/build becomes green.

A small protocol-data/build-tool backport does not automatically imply replacing its runtime platform. The exact dependency semantics must be investigated first.

## 7. Qualification stages

### KSQ-0 — Source and dependency inventory — **CERTIFIED**

PASS contract:

- exact KDE release-set/source-package inventory;
- exact Frameworks package inventory required by that release-set;
- complete build-dependency DAG;
- explicit list of Resolute packages that already satisfy requirements;
- explicit list of packages that require backport/override;
- no unresolved package-name/API assumptions;
- source provenance and checksums/signature verification strategy documented.

All criteria passed. Canonical evidence is `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`.

A change to the candidate release set, source selections, packaging overrides, pinned snapshot, or a relevant platform dependency reopens the corresponding KSQ-0 regression before downstream evidence can be reused.

### KSQ-1 — Reproducible source builds — **ACTIVE**

Build the certified 101-source candidate only on clean Ubuntu 26.04 builders.

PASS requires:

- all selected source packages build successfully from source;
- deterministic documented build order or dependency-driven builder process;
- no dependency on packages from an uncontrolled newer Ubuntu suite at build or runtime;
- build logs and resulting source/binary package manifests retained;
- package versions make the intended upgrade relationships explicit;
- the `kwallet-pam` compat-13 adaptation is materialized reproducibly without changing its certified PAM functional files;
- the only KSQ-1 packaging/source adaptations are the exact IDs declared by `tests/kde-stack/ksq-1-packaging-adaptations.tsv` and every built source records its applied adaptation metadata;
- built packages that can receive meaningful package-level installation smoke tests do so before KSQ-1 closes;
- reproducibility is demonstrated by independent rebuild comparison, not inferred from one successful clean build;
- final acceptance evidence is relocatable and self-verifying rather than depending on temporary runner paths or unrecorded sibling artifacts.

The build system consumes only the KSQ-0 certified closure/selections and the pinned Ubuntu snapshot `20260829T022000Z`. Candidate package versions append `~supra26.04.1` to the certified packaging base so they sort above the older Resolute KDE baseline while remaining below an equivalent official packaging revision.

#### KSQ-1 evidence to date

Canonical bootstrap run `33248631454` on `a414245cb2c66d754cb046bdca06188e2bfd059d` built DAG nodes 1–4 successfully and produced self-contained, relocatable SHA-256 evidence. Bootstrap artifact `9713725769` has digest `sha256:ee26c3f3421adcf4e64d351e10ba61c2bc890ba8c4bfded4b7e37dcb72fd9c7d`.

The first full-DAG run `33250886255` on `964561767fb1d0c45883d3de6754958e4263eebf` proved nodes 1–39 build successfully. Node 40, `kf6-kfilemetadata 6.29.0-0ubuntu1~supra26.04.1`, stopped during Build-Depends resolution. No package or platform change was made from that symptom.

A dedicated diagnostic run `33263391639` reproduced node 40 against the same certified 1–20 binary checkpoint and proved the actual cause: the source declares `libpostproc-dev | hello`, while sbuild's APT resolver considered only the first alternative because the builder had not enabled alternative dependency resolution. The failure was therefore a builder-policy defect, not a missing KDE dependency or justification to widen the Ubuntu platform boundary.

Corrective run `33263576164` changed only the relevant sbuild resolver behavior by adding `--resolve-alternatives` plus the APT uninstallable-dependency explainer. It successfully built node 40, selected the valid `hello` alternative, and produced six candidate DEBs. Artifact `9718028796` has digest `sha256:1808c2e3150c5ee8447a0e0242706bdb89f00e613c617b9a6b983479806caac0`.

Global builder commit `fe12df912217d44465a7a613d79ba3f523d4e700` applies the proven alternative-resolver behavior to the complete DAG and also preserves `.build`, `.buildinfo`, `.changes`, partial DEBs, hashes and explicit FAIL state before aborting any future failed source. Full regression run `33264059201` has since built nodes 1–80 successfully and remains useful as an independent reference build for sources whose exact prepared input identity is unchanged. It is not itself sufficient to certify the current patched candidate.

##### Syntax Highlighting reproducibility root cause

Independent builds of nodes 21–60 first showed 171/172 repeated DEBs byte-identical. The sole divergence was `libkf6syntaxhighlighting6`. Investigation proved this was not the timestamp defect already fixed by KDE MR !806: Frameworks 6.29.0 already contains KDE commit `fb41b0e8848ac054d6eda97d65fc63e8880c8360`, which removes `time.time()` from the generated grammar version.

The remaining cause is `data/generators/generate_jinja.py` choosing the next pending grammar with Python `set.pop()`. Hash randomization changes that traversal order, while `data/CMakeLists.txt` consumes the generator dry-run order directly as the generated syntax-resource list. The XML contents stay identical but their QRC/resource ordering changes the resulting library bytes.

Root-cause run `33279585912` on `05df555bd0b023fb9ef42a164f1f6cad30918155` tested the exact `kf6-syntax-highlighting 6.29.0-0ubuntu1` source under `PYTHONHASHSEED=1,2,3,4`: the original generator produced four distinct orders with identical XML content; deterministic lexicographic selection produced one order across all seeds. Artifact `9722594384` has digest `sha256:5891bd63bcf6615c34646c94b45c7efb5383629e118580382aac2ec350e22204`.

Patched package run `33279750116` then rebuilt node 29 twice against only certified nodes 1–28 with independent hash seeds. All six DEBs and three DDEBs passed byte-for-byte `cmp`; the workflow conclusion was red only because a later evidence-copy command attempted to copy multiple `.build` files to one filename after all binary comparisons had already passed. Artifact `9722758709` has digest `sha256:105962964acbfc8f2b13ec0d19675d758a2e5f117e5e8b202ff59943aabaeeaa`.

Formal post-build validator run `33280301683` independently revalidated that exact artifact and is PASS. Artifact `9722778323` has digest `sha256:bc8b272c945cb7124ad67af3b0dd575882eb166faf0bee6d603112ee036b9506`.

The proven fix was materialized as a declared quilt patch in commit `c362bd853bdebbf81d9ee49977a202b6bfd2de4f`. Follow-up commits `3ff7f1f0a00d94ea297c1448ea5ec78a1351e291` and `90fd5d3119ebfaab42f721d3bdd977a3472da498` removed unrelated changelog deltas so all unaffected sources retain their previous prepared-source identity and node 29 uses the same patch/source delta proven by the dedicated experiment. The authoritative full-DAG rebuild for that exact source-preparation state is run `33281736655` on `90fd5d3119ebfaab42f721d3bdd977a3472da498`.

The materialized adaptation boundary is machine-readable in `tests/kde-stack/ksq-1-packaging-adaptations.tsv` and is currently exactly two IDs:

- `kwallet-pam-compat13-relationship-substvars`;
- `kf6-syntax-highlighting-deterministic-jinja-order`.

The final full-build validator fails if another adaptation appears implicitly or if any source reports adaptation metadata inconsistent with that manifest.

##### Reproducibility acceptance plan

The reproducibility criterion is fixed before examining the final hashes. The candidate must account for all 101 source nodes and every produced binary DEB.

For the 95 nodes unaffected by the Syntax Highlighting source delta, `scripts/ci/validate-ksq-1-reproducibility.py` may use an independent earlier full-DAG build only after first proving prepared-source identity (`.dsc`, generated Debian source delta, `debian/control` and `debian/changelog`) and binary package shape are exact. It then requires byte-identical DEBs. A matching version string without matching prepared source is rejected.

The patch invalidates node 29 plus exactly five descendants in the certified source DAG: node 68 `drkonqi`, node 81 `kf6-ktexteditor`, node 99 `plasma-workspace`, node 100 `plasma-desktop`, and node 101 `powerdevil`. These six nodes require dedicated independent rebuild evidence against the patched candidate inputs and cannot inherit pre-patch hashes. Their proof hashes must match the authoritative full-DAG candidate byte-for-byte.

This 95+6 split does not weaken the gate: it avoids rebuilding sources whose complete inputs are independently proven unchanged, while refusing to reuse evidence for any source whose dependency ancestry changed. `reprotest`/`diffoscope` remain diagnostic tools for controlled variation and divergence analysis; the KSQ-1 exit contract requires complete independent byte-identity coverage of the shipping candidate.

KSQ-1 is **not certified** until the authoritative 101-source build, KWallet package gate, 101-source final validator, complete reproducibility comparison and consolidated self-contained artifact all pass.

### KSQ-2 — APT repository and dependency closure

Publish the prototype packages to a temporary/testing SupraLINUX APT repository used by disposable test systems.

PASS requires:

- `apt update` and dependency resolution succeed from Ubuntu 26.04 + the candidate SupraLINUX repository only;
- no KDE package is satisfied accidentally from another distribution/repository;
- no unrelated Ubuntu package is overridden by broad pinning;
- resulting installed package versions/owners are recorded;
- package removals/replacements caused by ABI transitions are understood and intentional.

### KSQ-3 — Clean installation

Starting from the same clean Ubuntu 26.04 base contract used by SupraLINUX, install the candidate desktop.

PASS requires:

- package installation completes without broken dependencies or maintainer-script failures;
- `apt --fix-broken install` is not required as a repair step;
- no manual post-install command is needed to finish the KDE stack;
- expected Plasma Wayland and SDDM components are installed;
- Snap policy remains intact;
- no unintended Ubuntu/Kubuntu desktop metapackage is pulled in;
- `scripts/ci/validate-kwallet-pam-installation.sh` passes against the installed candidate rootfs.

### KSQ-4 — Upgrade from the historical baseline

Exercise a real supported upgrade from the current development KDE 6.6.6/KF 6.24 package state to the candidate.

PASS requires:

- APT computes and completes the transition normally;
- every ABI/package rename/removal is classified;
- user configuration is preserved unless an upstream migration intentionally changes it;
- no packages remain half-configured;
- no obsolete package silently keeps an old runtime component active;
- the resulting package set matches a clean candidate install except for explicitly justified historical/user-state differences.

### KSQ-5 — Rollback/recovery

A testing candidate must not make recovery undefined.

PASS requires a documented and tested method to return a disposable upgraded system to the previous known-good KDE baseline or an equivalent known-good snapshot/image state. The method must account for package-version downgrades, ABI transitions and configuration compatibility; “manually reinstall packages until it works” is not a rollback strategy.

This gate does not require a polished end-user rollback UI yet. It requires engineering recovery during qualification.

### KSQ-6 — Boot/session regression

After package-level qualification, re-run the actual product boot/session gates.

Required:

- C1;
- C2 SDDM/KWin Wayland greeter;
- C3 Plasma Wayland session;
- C3 XWayland compatibility;
- failed-unit/crash review;
- package/version evidence showing the candidate stack was actually exercised.

A successful login alone is insufficient.

### KSQ-7 — Surface reconciliation

Re-run C4.0 from the live candidate stack.

PASS requires:

- regenerate the runtime surface inventory rather than forcing the new stack into the 6.6.6 manifest;
- classify all added/removed/renamed KCMs, KWin surfaces, applets, KDED plugins, KIO integrations, portals, services and direct dependencies;
- update capability mappings and package ownership;
- zero unknown/unmapped exposed surfaces before C4 resumes.

The old C4.0 artifact remains historical evidence and is not overwritten.

### KSQ-8 — Integration delta review

Before architecture adoption, review every SupraLINUX-specific compatibility change against the candidate stack, including the Baloo launcher.

For each workaround/override:

- reproduce the original defect on the new stack;
- keep it if still required and prove the fix;
- remove it if upstream/new packaging resolves the defect and prove behavior remains correct without it;
- do not preserve historical patches merely because they existed.

### KSQ-9 — Security and maintenance ownership

PASS requires:

- defined source of KDE security/release notifications;
- defined process for rebuilding security/bug-fix point releases;
- explicit testing→stable promotion procedure;
- ability to identify every supported SupraLINUX KDE binary back to source/version;
- documentation that Ubuntu security updates to an overridden binary package do not automatically patch the SupraLINUX build;
- all active override ownership records remain synchronized with `docs/KDE_STACK_OVERRIDES.md`.

### KSQ-10 — Architecture decision

The gate closes with one explicit result:

**GO:** adopt the qualified SupraLINUX KDE stack, update `PROJECT_RULES.md` candidate versions from PROVISIONAL to the accepted release baseline, rebase C4 documentation/manifests on the newly accepted C4.0 surface, and resume C4.1.

**NO-GO:** retain the Ubuntu KDE baseline, document the blocking reasons, resume C4.1 on that known stack, and remove qualification-only packaging that has no future engineering value.

There is no partial implicit adoption.

## 8. C4 interaction while this gate is open

- C4.1 is paused.
- Existing C4.1 workflows/harnesses remain historical/regression tooling.
- A green result produced on the old 6.6.6 stack does not certify the candidate stack.
- No pending C4 capability is promoted solely because equivalent behavior passed on the historical stack.
- If the new stack is adopted, the candidate C4.0 surface becomes canonical before feature certification resumes.

## 9. KDE Gear

KDE Gear is deliberately excluded from the Plasma/Frameworks source-architecture decision.

The current upstream stable Gear series is 26.08. It must receive a separate compatibility and packaging review for the applications/integrations Aurora actually ships. In particular, currently deferred direct roots such as `kio-extras`, `kdenetwork-filesharing` and `krdc` may not remain indefinitely “deferred” if their functionality is exposed to the user.

Do not keep an older Gear merely because Ubuntu froze it, and do not update Gear merely because a newer version number exists. Choose the newest stable technically compatible set and certify it.

## 10. Evidence retention

Each qualification stage must produce enough evidence to reproduce the decision later. At minimum retain:

- source/package manifest;
- dependency graph/delta;
- build logs;
- repository package index/version evidence;
- clean-install package manifest;
- upgrade transaction/logs;
- rollback/recovery result;
- C1-C3 artifacts;
- regenerated C4.0 artifact;
- known regression list and classifications;
- final GO/NO-GO record with exact commit and package versions.

A phase is not complete because it “looks fine” interactively. It closes only when its written PASS contract is satisfied.
