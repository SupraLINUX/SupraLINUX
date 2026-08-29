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

## Current override boundary

KSQ-0 certifies **three source backports and one packaging adaptation only**. The compat-13 relationship restoration above is part of the single `kwallet-pam` packaging adaptation; it does not create another source/backport exception.

There is no authorization to override Qt, Wayland runtime, Mesa, libdrm, kernel, firmware, systemd, PipeWire/WirePlumber, NetworkManager, or base compiler/runtime libraries.

A candidate change that requires any such expansion stops qualification and opens a new architecture review before implementation.
