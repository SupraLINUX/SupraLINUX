# KDE Tier 3 KIO Round 23 — Attempt 8 rootfs KRecent diagnostic

Status: definition pending diagnostic retry 3.

Diagnostic attempt 1 (workflow `36279506026`) is recorded as **INFRA_INVALID**: the runner stopped at `stage-inputs` because a non-recursive wildcard attempted to copy the materialization artifact's `debian/` directory. No chroot test or package build occurred, so it carries no KIO conclusion. The retry copies only the `.dsc`, `.orig.tar.*` and `.debian.tar.*` source files and resolves `sbuild` ownership by account name rather than an assumed UID.

Diagnostic attempt 2 (workflow `36279908858`, job `108509683175`, artifact `10918078631`, SHA-256 `adb866de60351fa0cb104b3f10187df1532863af639a2ae1227367ae32e5e19f`) is also **INFRA_INVALID**. It reached source extraction but the manual wrapper tried to call `useradd`; the exact buildd rootfs does not contain that utility. No tests or package build ran.

Diagnostic attempt 3 (workflow `36280922944`, job `108512470733`) is **INFRA_INVALID** and produced no artifact: `SBUILD_LOG` was expanded before `EVIDENCE` was assigned under `set -u`. Execution stopped during initialization, before sbuild or package activity.

The retry also restores the exact rootfs-selection mechanism already proven by Attempt 8: the verified tarball is linked as `~/.cache/sbuild/resolute-amd64.tar` and sbuild is invoked with `--chroot-mode=unshare --dist=resolute`.

The retry now delegates containment to the actual Ubuntu Resolute `sbuild 0.91.2ubuntu3` unshare backend. The exact historical rootfs is passed directly to sbuild, the same predecessor packages are injected with `--extra-package`, and sbuild provides its native `sbuild` user and namespace. A `starting-build-commands` hook runs the diagnostic after dependency installation and exits with sentinel code 86 before `dpkg-buildpackage`. The outer runner accepts the result only if the hook completes, the log contains no `Command: dpkg-buildpackage`, and no package artifacts exist.

Round 22 eliminated two host-side explanations: hidden HOME and complete KRecent CTest execution. Round 23 therefore moves the test into the **exact Attempt 8 rootfs artifact** while retaining the same KIO 6.30.0-0supralinux8 source materialization and predecessor package set.

This remains diagnostic-only. It does not invoke `dpkg-buildpackage` or sbuild package construction, does not create `.deb` artifacts, does not allocate a revision and does not authorize Attempt 9.

## Exact historical environment reused

- Attempt 8 workflow: `36238357510`
- KIO job: `108394325161`
- rootfs artifact: `10904512642`
- rootfs artifact SHA-256: `d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe`
- KIO source: `6.30.0-0supralinux8`
- source path: `/build/reproducible-path/kf6-kio-6.30.0`
- HOME: `/build/reproducible-path/kf6-kio-6.30.0/debian/.supralinux-test-home/sbuild`

KIO is configured and compiled with its Debian rules inside the real sbuild-unshare session; the diagnostic hook deliberately stops sbuild before the package-build command.

## Matrix

- **isolated-krecent:** 100 KRecent CTest runs with a fresh hidden HOME.
- **prefix-through-krecent:** 30 runs of tests 1 through 26, recreating the exact CTest prefix that preceded KRecent in Attempt 8.
- **full-suite:** 3 complete 69-test runs with the Attempt 8 environment.

The XBEL is copied only after `recentUrls()` has computed the list and before the failing assertion, so the diagnostic observation cannot reorder that list.

If this rootfs still does not reproduce the failure, the remaining evidence points toward a one-off nondeterministic timing/filesystem event rather than a stable packaging defect. That conclusion would still need a deliberate remediation policy before Attempt 9.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
