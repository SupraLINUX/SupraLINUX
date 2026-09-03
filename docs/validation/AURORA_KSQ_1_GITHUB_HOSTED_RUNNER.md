# Aurora KSQ-1 GitHub-hosted Ubuntu 26.04 qualification

Status: **QUALIFIED NATIVE EXECUTION ARCHITECTURE — NOT KSQ-1 ACCEPTANCE**

This document records the current GitHub-hosted execution architecture for Aurora KSQ engineering. It qualifies CI/build behavior only. It does not certify the complete 101-source candidate or KSQ-1.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Policy decision

Ubuntu 26.04 LTS is the SupraLINUX base. GitHub still labels the standard x64 `ubuntu-26.04` hosted runner **Public Preview** as of 2026-09-03. Therefore it is acceptable for engineering/qualification only after fail-closed empirical checks, but it cannot be the sole canonical release builder while that preview status remains.

The future canonical SupraLINUX release builder is tracked separately in `docs/architecture/FUTURE_CANONICAL_RELEASE_BUILDER.md`.

## Selected native architecture

The selected KSQ execution path is now:

1. GitHub-hosted x64 `runs-on: ubuntu-26.04`.
2. Ubuntu Resolute `sbuild 0.91.2ubuntu3`, `libsbuild-perl 0.91.2ubuntu3`, `mmdebstrap 1.5.7-3` and stock `uidmap 1:4.17.4-2ubuntu3`.
3. Immutable validated snapshot `20260829T022000Z` staged below `/opt/supralinux/archive`.
4. APT metadata regenerated from the local `file:` slice and checked against certified KSQ-0 evidence.
5. `mmdebstrap --mode=unshare --variant=buildd` creates the Resolute buildd tarball.
6. `sbuild --chroot-mode=unshare --no-enable-network` builds the source package directly on the hosted Ubuntu 26.04 VM.
7. Only Ubuntu's packaged AppArmor profiles for `sbuild`/`mmdebstrap` are used; SupraLINUX does not load a custom build AppArmor profile.
8. `newuidmap`/`newgidmap` remain in the stock Ubuntu package privilege model. No setuid-to-file-capability rewrite is permitted.
9. `BUILD_ENV_CMND` runs the maintained network-proof wrapper in the same build context as `dpkg-buildpackage`.
10. Every formal native build must prove a different network namespace from the host, `/proc/net/dev` containing only `lo`, zero IPv4 routes, local-only package transport and zero relevant AppArmor denials.

Ubuntu's Resolute `sbuild.conf(5)` documents `$enable_network = 0` as the default and states that network access is blocked during builds in unshare mode. `BUILD_ENV_CMND` receives the actual `dpkg-buildpackage` command line, making it the correct observation point for the network gate.

## Native source-001 proof

Final direct-runner proof:

- commit `38116f958add18c216f83caf57ae15b61386ca6a`;
- run `33721612626`;
- result **SUCCESS**;
- artifact `9880467340` (`aurora-ksq-native-build-context-nonet`);
- artifact digest `sha256:fd54b92d0ccf4144d28d1dcff0a884f5bd9f7102534f21f0c590f08c61d7c4c9`.

The artifact proves:

- `AURORA_NATIVE_LOCAL_APT=PASS`;
- `AURORA_NATIVE_MMDEBSTRAP=PASS`;
- source preparation PASS;
- real `sbuild` RC `0`;
- generated native `.build` status `successful`;
- host and build network namespace inodes differ;
- `/proc/net/dev` inside `dpkg-buildpackage` exposes only `lo`;
- IPv4 route count is `0`;
- the actual invocation contains `sbuild-usernsexec --nonet`;
- HTTP/HTTPS APT acquisition lines during the build are `0`;
- relevant AppArmor denials are `0`;
- Docker used: `0`;
- custom AppArmor used: `0`.

The inherited `/sys/class/net` view is not a network-isolation gate because sysfs can retain the network namespace view associated with the sysfs mount. Namespace-aware `/proc/net/*` plus the namespace inode are the maintained evidence.

## Docker-era architecture: rejected / retired

The prior hosted design used a pinned Ubuntu 26.04 Docker container, a Docker Engine API helper, a SupraLINUX AppArmor profile derived from `docker-default`, selective `/proc` mask changes and a setuid-to-file-capability rewrite for `newuidmap`/`newgidmap`.

That design is no longer part of the selected KSQ architecture. It was useful root-cause research, but the clean direct host path has demonstrated that those adaptations are unnecessary.

The following operational components were removed from `feature/kde-stack-qualification` on 2026-09-03:

- `.github/workflows/ksq-1-local-range-probe.yml`;
- `.github/workflows/ksq-docker-builder-helper-probe.yml`;
- `.github/workflows/ksq-docker-proc-userns-ab-probe.yml`;
- `.github/workflows/ksq-github-hosted-builder-profile-probe.yml`;
- `.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`;
- `.github/workflows/ksq-github-hosted-parity.yml`;
- `scripts/ci/ksq-docker-builder.py`;
- `scripts/ci/install-ksq-apparmor-profile.sh`;
- `scripts/ci/apparmor/supralinux-ksq-unshare`;
- `scripts/ci/prepare-ksq-1-local-runner.sh`;
- `scripts/ci/run-ksq-1-local-range.sh`;
- `scripts/ci/configure-ksq-uidmap-filecaps.sh`.

Git history and prior Actions artifacts remain the historical evidence. These mechanisms must not be reintroduced without a demonstrated regression in the native architecture and a new architectural review.

## Durable snapshot input

Published repository-pinned snapshot:

- Release ID `380209318`;
- tag `ksq-snapshot-20260829T022000Z`;
- asset ID `538944111`;
- asset `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- bytes `973148160`;
- SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`;
- repository status `INDEPENDENTLY_VALIDATED` in `scripts/ci/aurora-ksq-snapshot-release.env`.

## Current targeted range proof

`.github/workflows/ksq-native-range-041-043-probe.yml` is the clean targeted migration probe. It restores and verifies the exact 001-020 and 021-040 checkpoints, confirms order 43 remains `kpipewire`, creates the buildd environment natively and builds only orders 41-43.

The workflow also fails closed if any retired Docker/custom-AppArmor/filecap helper is present and verifies stock `newuidmap`/`newgidmap` before the build.

Run `33725437853` on commit `7419221ef3ca5c6a2d1df6e9d4ddbf556c09155a` is the first clean 041-043 execution. Its final result must be recorded in `AURORA_KSQ_1_ACTIVE_STATUS.md`; no PASS is assumed while the run is incomplete.

## Current state

- GitHub-hosted Ubuntu 26.04 native execution architecture: **QUALIFIED FOR KSQ ENGINEERING**;
- GitHub hosted service status: **PUBLIC PREVIEW / NOT SOLE FINAL RELEASE BUILDER**;
- Docker-based KSQ architecture: **REJECTED / RETIRED**;
- custom KSQ AppArmor profile: **REMOVED**;
- uidmap file-capability adaptation: **REMOVED**;
- direct source 001 local-only build: **PASS**;
- clean native range 041-043: **IN PROGRESS**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
