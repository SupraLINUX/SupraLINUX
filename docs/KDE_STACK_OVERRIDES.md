# Aurora KDE Stack Overrides and Backports

Status: **ACTIVE — candidate qualification only**

This document records every non-Resolute source selection or packaging adaptation currently required by the Aurora KDE candidate. An entry here is not permission to widen the override set. Any new exception must be investigated, documented, added to the strict KSQ dependency model, and recertified before use.

Canonical KSQ-0 acceptance: `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md`.

## Maintenance policy

For every override below SupraLINUX owns:

- tracking the upstream/KDE and distribution source used as its baseline;
- rebuilding relevant security and bug-fix updates;
- confirming that Ubuntu security updates to the overridden binary do not silently leave the SupraLINUX build vulnerable;
- rerunning the dependency/build/install/functional regressions affected by any update;
- removing the override when the supported Ubuntu base can satisfy the requirement directly.

The preferred exit is always to return ownership to Ubuntu once the required stable capability exists in the supported base without violating the product architecture.

## 1. `plasma-wayland-protocols` 1.21.0-1

**Classification:** KDE-adjacent source backport.

**Upstream/source origin:** KDE Plasma Wayland Protocols 1.21.0; Ubuntu Stonking packaging `1.21.0-1` used only as source/packaging reference from Ubuntu snapshot `20260829T022000Z`.

**Resolute baseline:** 1.20.0.

**Reason:** KWin and `plasma-workspace` 6.7.4 require `plasma-wayland-protocols >= 1.21.0`.

**Difference from Ubuntu 26.04:** only this protocol package is advanced to the exact required stable generation. This entry does not authorize replacing Wayland runtime packages.

**Maintenance/security responsibility:** SupraLINUX while the binary is overridden. Track KDE stable point/security updates plus Ubuntu/Debian packaging changes; rebuild and rerun KSQ regressions when the selected source changes.

**Update procedure:** select a newer stable source only when required by the accepted Plasma/KWin release or when it contains a relevant fix. Recompute KSQ-0 closure before promotion, then rerun source build, repository, install, upgrade, rollback and affected runtime certification.

**Removal condition:** remove the override when the supported Ubuntu base provides a version satisfying the accepted Plasma/KWin requirement with no SupraLINUX-specific package ownership needed.

## 2. `qtkeychain` 0.17.0-1

**Classification:** KDE-adjacent source backport.

**Upstream/source origin:** QtKeychain 0.17.0; Ubuntu Stonking packaging `0.17.0-1` used as source/packaging reference from Ubuntu snapshot `20260829T022000Z`.

**Resolute baseline:** 0.15.0.

**Reason:** `plasma-nm` 6.7.4 requires `qtkeychain-qt6-dev >= 0.16.0`.

**Difference from Ubuntu 26.04:** QtKeychain is advanced while Qt itself remains the Ubuntu 26.04 Qt 6.10.2 platform.

**Maintenance/security responsibility:** SupraLINUX while overridden. Monitor QtKeychain upstream plus Debian/Ubuntu packaging and rebuild relevant stable fixes.

**Update procedure:** do not advance merely because a newer version exists. Re-evaluate the minimum needed by the accepted Plasma-NM release and any security/functional fixes, recompute closure, then rerun affected KSQ and C4 network/KWallet regressions.

**Removal condition:** remove when the supported Ubuntu base supplies a version satisfying the accepted Plasma-NM dependency and functional certification.

## 3. `wayland-protocols` 1.48-1

**Classification:** Ubuntu-platform compatibility backport of protocol data/build inputs; not a Wayland runtime replacement.

**Source origin:** Debian `wayland-protocols 1.48-1`. Exact source files are retrieved from Debian Snapshot by immutable content hash and validated against pinned SHA-256 values retained by the KSQ-0 source audit.

**Resolute baseline:** 1.47.

**Reason:** KWin 6.7.4 requires `wayland-protocols >= 1.48`.

**Why not current 1.49 packaging:** Debian 1.48-1 requires `libwayland-dev >= 1.23.0`, compatible with the Resolute Wayland generation. The evaluated 1.49 packaging requires `libwayland-dev >= 1.25.0`; adopting it would force an unnecessary Wayland platform expansion merely to obtain protocol definitions.

**Difference from Ubuntu 26.04:** protocol definitions move from 1.47 to 1.48. Ubuntu's Wayland runtime remains owned by Ubuntu.

**Maintenance/security responsibility:** SupraLINUX while overridden. Protocol-data updates are treated as platform-sensitive because they can alter build-time feature exposure even when runtime libraries do not change.

**Update procedure:** update only when the accepted KDE stack requires it or when a relevant stable fix is justified. Verify the new package's `libwayland-dev` requirement against the Ubuntu platform boundary before selecting it, then rerun KSQ-0 and all downstream build/runtime regressions affected by KWin/Wayland protocol changes.

**Removal condition:** remove once the supported Ubuntu base provides an adequate protocol revision directly, or when a future accepted KDE stack no longer needs a SupraLINUX override.

## 4. `kwallet-pam 4:6.7.4-0ubuntu3` packaging adaptation

**Classification:** SupraLINUX packaging adaptation; upstream/runtime behavior must remain unchanged.

**Source origin:** Ubuntu Stonking `kwallet-pam 4:6.7.4-0ubuntu3`, which preserves Debian 6.7.4-3 PAM integration/fixes while retaining Ubuntu's packaging delta that does not use `dh-sequence-plasma`.

**Resolute constraint:** Resolute's `debhelper` provides compat level 13, while this source packaging declares `debhelper-compat (= 14)`.

**Primary SupraLINUX build delta:**

`debhelper-compat (= 14)` → `debhelper-compat (= 13)`

**Required compat-13 relationship restoration:** Debian's 6.7.4-2 packaging changelog records that `${shlibs:Depends}`, `${qml6:Depends}` and `${misc:Depends}` were removed when the packaging moved to debhelper compat 14 because compat 14 automatically applies relationship substvars. Compat 13 does not provide that behavior. Therefore the SupraLINUX compat-13 build must explicitly restore the equivalent relationship tokens:

- `libpam-kwallet-common`: `${misc:Depends}`;
- `libpam-kwallet5`: `${misc:Depends}`, `${qml6:Depends}`, `${shlibs:Depends}`.

This is a dependency-metadata semantic restoration required by the compat downgrade; it is not a KDE/PAM runtime behavior change and does not authorize adding `dh-sequence-plasma` to the Ubuntu packaging.

No PAM functional file is intentionally modified.

**Functional invariants:** the KSQ-0 audit requires these Ubuntu files to remain byte-identical to Debian 6.7.4-3:

- `debian/libpam-kwallet-common.install`
- `debian/libpam-kwallet-common.postinst`
- `debian/libpam-kwallet-common.prerm`
- `debian/pam-configs/kde-kwallet`

It also requires `libpam-runtime`, `pam-auth-update`, and the Password profile. KSQ-1 must verify that the rebuilt binary metadata actually contains the expected runtime dependency closure and install the packages in a disposable Resolute rootfs. `scripts/ci/validate-kwallet-pam-installation.sh` must prove `pam_kwallet5.so` registration in both `common-session` and `common-auth` after installation.

The package-level KSQ-1 installation gate does **not** by itself certify live KWallet auto-unlock in a graphical login session. End-to-end auto-unlock remains a later runtime/functional certification requirement.

**Maintenance/security responsibility:** SupraLINUX owns this rebuilt binary and must track KWallet/KDE Plasma updates and Ubuntu/Debian packaging changes. Any upstream/source update invalidates the current byte-identity and compat-semantics evidence and requires a fresh audit.

**Update procedure:** begin from the newest compatible stable upstream/source packaging, preserve all functional PAM integration, determine whether the compat-level delta and explicit relationship substvars are still required, and rerun KSQ-0 before rebuilding. Never solve a future packaging failure by deleting PAM maintainer scripts, runtime dependency generation, or integration files.

**Removal condition:** remove the adaptation when the supported Ubuntu base's debhelper can build the selected official packaging unchanged, or when newer accepted packaging no longer needs the compat-level change.

## 5. `kf6-syntax-highlighting 6.29.0-0ubuntu1` deterministic Jinja-generation patch

**Classification:** SupraLINUX build-time source adaptation for reproducibility. It changes only the build-time grammar traversal order; it does not intentionally change syntax-definition content or runtime APIs.

**Source origin:** KDE Frameworks Syntax Highlighting 6.29.0 using Ubuntu Stonking packaging `6.29.0-0ubuntu1` from the pinned Ubuntu snapshot `20260829T022000Z`.

**Root cause:** Frameworks 6.29.0's `data/generators/generate_jinja.py` chooses pending grammars with Python `set.pop()`. Python hash randomization therefore changes the generator's dry-run output order across `PYTHONHASHSEED` values. `data/CMakeLists.txt` consumes that output order as `out_xmls`/`gen_defs`, and that ordering reaches the embedded syntax QRC. Independent KSQ-1 builds consequently produced two different `libkf6syntaxhighlighting6` binaries even though the generated XML contents were identical.

KDE upstream commit `fb41b0e8848ac054d6eda97d65fc63e8880c8360`/MR !806, included in Frameworks 6.29.0, fixed an earlier timestamp-based reproducibility defect in the same generator but did not make the pending-set traversal deterministic. Upstream `master` still contained `set.pop()` when rechecked on 2026-08-29.

**SupraLINUX delta:** `packaging/ksq-1/patches/kf6-syntax-highlighting/supralinux-deterministic-jinja-order.patch` replaces the single traversal operation:

`lang = to_do.pop()`

with deterministic lexicographic selection:

`lang = min(to_do)` followed by `to_do.remove(lang)`.

The adaptation is declared machine-readably as `kf6-syntax-highlighting-deterministic-jinja-order` in `tests/kde-stack/ksq-1-packaging-adaptations.tsv`. Source preparation fails closed if the expected upstream line, quilt packaging shape, implementation path or adaptation metadata drifts.

**Evidence:** root-cause run `33279585912` proved four different original orders under `PYTHONHASHSEED=1,2,3,4` while generated XML contents stayed identical; the deterministic traversal produced one order across all four seeds. Patched package run `33279750116` then built the exact node 29 source twice against certified nodes 1–28 with seeds 1 and 2. All six DEBs and three DDEBs were byte-identical; the workflow's red conclusion was caused only by a later evidence-copy command after all binary `cmp` checks had passed. Artifact `9722758709` has digest `sha256:105962964acbfc8f2b13ec0d19675d758a2e5f117e5e8b202ff59943aabaeeaa`. Independent artifact validator run `33280301683` is PASS; artifact `9722778323` has digest `sha256:bc8b272c945cb7124ad67af3b0dd575882eb166faf0bee6d603112ee036b9506`.

**Regression scope:** the certified source DAG gives node 29 five downstream descendants: node 68 `drkonqi`, node 81 `kf6-ktexteditor`, node 99 `plasma-workspace`, node 100 `plasma-desktop`, and node 101 `powerdevil`. Those nodes plus node 29 must not reuse pre-patch build certification. The current full-DAG regression on the materialized adaptation remains authoritative before KSQ-1 can close.

**Maintenance/security responsibility:** SupraLINUX owns the patched binary while the delta exists. Every accepted Frameworks point release must be checked first for an upstream deterministic traversal or equivalent fix. If upstream resolves the defect, carrying this patch forward is prohibited unless a new defect is independently demonstrated.

**Update procedure:** start from the new stable official source/packaging, reproduce the original nondeterminism test, remove the patch if upstream is deterministic, or rebase only after proving the same root cause remains. Re-run the affected build/reproducibility regressions and any downstream gates invalidated by the source change.

**Removal condition:** remove immediately when the accepted stable KDE source produces deterministic Jinja/QRC ordering without the SupraLINUX patch.

## Current override boundary

Canonical KSQ-0 acceptance certifies **three source backports and the `kwallet-pam` packaging adaptation**. KSQ-1 has additionally materialized the single `kf6-syntax-highlighting` reproducibility patch above after independently proving its cause and correction. The new patch does not change the dependency closure or widen Ubuntu platform ownership, but it is an owned source override and therefore invalidates the affected build evidence until the current regressions pass.

The current machine-readable KSQ-1 adaptation boundary is exactly two IDs in `tests/kde-stack/ksq-1-packaging-adaptations.tsv`: the KWallet compat-13 relationship restoration and the Syntax Highlighting deterministic-Jinja patch. Any third adaptation is a boundary change and must fail the current KSQ-1 final validator until explicitly investigated and reviewed.

There is no authorization to override Qt, Wayland runtime, Mesa, libdrm, kernel, firmware, systemd, PipeWire/WirePlumber, NetworkManager, or base compiler/runtime libraries.

A candidate change that requires any such expansion stops qualification and opens a new architecture review before implementation.
