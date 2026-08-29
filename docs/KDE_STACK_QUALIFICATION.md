# Aurora KDE Stack Qualification

Status: **ACTIVE / PROVISIONAL ARCHITECTURE GATE**

This gate decides which KDE stack becomes the versioned foundation for the rest of Aurora's C4 certification. It exists because feature certification is meaningful only against the software stack that will actually ship.

C4.1 and later feature work are paused while this gate is open.

## 1. Existing known-good baseline

The current development repository reached these milestones using Ubuntu 26.04's KDE stack:

- Plasma 6.6.6;
- KDE Frameworks 6.24.x;
- Qt 6.10.2 from Ubuntu;
- C1 accepted;
- C2 accepted;
- C3 accepted;
- C4.0 accepted;
- incremental C4.1 evidence accepted for the capabilities recorded in the C4 documentation.

This evidence is not discarded. It is **historical version-scoped evidence**. It may be used for regression comparison, but it must never be represented as evidence produced by a newer KDE stack.

The Baloo compatibility launcher and C4.1b harness introduced while diagnosing the 6.6.6 baseline also remain in the repository until the candidate stack proves whether they are still needed. Removing a workaround before reproducing the corresponding behavior on the new stack would destroy useful evidence.

## 2. Candidate architecture

Qualification target as of 2026-08-28:

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
| KDE Frameworks | SupraLINUX candidate 6.29.x |
| Plasma | SupraLINUX candidate 6.7.4 |
| KWin | SupraLINUX candidate 6.7.4 |
| `plasma-wayland-protocols` | backport only if required by the selected Plasma/KWin source packages |
| `wayland-protocols` | minimal compatible backport only if required; do not replace Wayland runtime merely to obtain a newer protocol-data package |
| KDE Gear | **not decided here**; separate stable-version review after this gate |

The candidate versions are not release commitments. If exact build requirements prove that another stable point release in the same compatible generation is the cleaner target, the change must be documented before proceeding.

## 3. Research basis

The architecture decision is based on current upstream/distribution evidence, not on version-number preference alone:

- Ubuntu 26.04 already provides Qt 6.10.2, matching the Qt generation expected by Plasma 6.7;
- KDE Frameworks 6.29 remains compatible with Qt 6.10;
- Kubuntu/Ubuntu development packaging already contains Plasma/KWin 6.7.4 and current Frameworks source packaging that can be audited as a packaging reference;
- KDE neon demonstrates that modern KDE releases can be built on an Ubuntu 26.04/Resolute base, but SupraLINUX will not depend on neon binary repositories for its supported product;
- dependency research found a small set of protocol/build-package deltas rather than an immediate requirement to replace kernel, Mesa, Qt or the Wayland runtime.

These findings authorize a prototype; they do **not** constitute a PASS.

Before implementing each package, current official KDE, Ubuntu and Debian/Kubuntu source metadata must be rechecked because versions and dependency relationships can move.

## 4. Packaging principles

1. Build DEBs; never install the supported KDE stack manually into `/usr/local`.
2. Use official stable KDE source tarballs/releases.
3. Prefer maintained Debian/Kubuntu packaging as the packaging base when technically valid for Resolute.
4. Record the exact packaging base commit/version for every source package.
5. Keep SupraLINUX patches minimal, reviewable and removable.
6. Do not enable a third-party binary repository as an undeclared runtime dependency.
7. Every intentional override must use deterministic package versions and APT behavior; no blanket origin priority may accidentally override unrelated Ubuntu packages.
8. Build dependencies used only in CI/builders must not leak into product dependencies.
9. The source-package graph, not a hand-maintained list of executable names, determines what must be rebuilt.

## 5. Platform-boundary rule

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

If the KDE candidate requires replacing one of these layers, stop and open a documented architecture review. Do not silently widen the backport set until the dependency solver becomes green.

A small protocol-data/build-tool backport does not automatically imply replacing its runtime platform. The exact dependency semantics must be investigated first.

## 6. Qualification stages

### KSQ-0 — Source and dependency inventory

PASS requires:

- exact KDE release-set/source-package inventory;
- exact Frameworks package inventory required by that release-set;
- complete build-dependency DAG;
- explicit list of Resolute packages that already satisfy requirements;
- explicit list of packages that require backport/override;
- no unresolved package-name/API assumptions;
- source provenance and checksums/signature verification strategy documented.

### KSQ-1 — Reproducible source builds

Build the candidate only on clean Ubuntu 26.04 builders.

PASS requires:

- all selected source packages build successfully from source;
- deterministic documented build order or dependency-driven builder process;
- no dependency on packages from an uncontrolled newer Ubuntu suite at build or runtime;
- build logs and resulting source/binary package manifests retained;
- package versions make the intended upgrade relationships explicit.

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
- no unintended Ubuntu/Kubuntu desktop metapackage is pulled in.

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

This gate does not require SupraLINUX to expose a polished end-user rollback UI yet. It requires engineering recovery during qualification.

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
- documentation that Ubuntu security updates to an overridden binary package do not automatically patch the SupraLINUX build.

### KSQ-10 — Architecture decision

The gate closes with one explicit result:

**GO:** adopt the qualified SupraLINUX KDE stack, update `PROJECT_RULES.md` candidate versions from PROVISIONAL to the accepted release baseline, rebase C4 documentation/manifests on the newly accepted C4.0 surface, and resume C4.1.

**NO-GO:** retain the Ubuntu KDE baseline, document the blocking reasons, resume C4.1 on that known stack, and remove qualification-only packaging that has no future engineering value.

There is no partial implicit adoption.

## 7. C4 interaction while this gate is open

- C4.1 is paused.
- Existing C4.1 workflows/harnesses may remain in Git as historical/regression tooling.
- A green result produced on the old 6.6.6 stack while this gate is open does not certify the candidate stack.
- No pending C4 capability is promoted solely because the equivalent behavior passed on the historical stack.
- If the new stack is adopted, the new C4.0 surface becomes canonical before further feature certification.

## 8. KDE Gear

KDE Gear is deliberately excluded from the GO/NO-GO decision for Plasma/Frameworks.

After this gate closes, open a separate review that asks whether the newest stable KDE Gear release can be integrated without destabilizing the qualified desktop/platform boundary. Gear must receive the same source-provenance, packaging, dependency, upgrade and functional-treatment discipline appropriate to the applications that SupraLINUX actually ships.

Do not keep an older Gear merely because Ubuntu froze it, and do not update Gear merely because a newer version number exists.

## 9. Evidence retention

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
