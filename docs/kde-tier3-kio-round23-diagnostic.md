# KDE Tier 3 KIO Round 23 — Attempt 8 rootfs KRecent diagnostic

Status: definition pending diagnostic retry 6.

Diagnostic attempt 1 (workflow `36279506026`) is recorded as **INFRA_INVALID**: the runner stopped at `stage-inputs` because a non-recursive wildcard attempted to copy the materialization artifact's `debian/` directory. No chroot test or package build occurred, so it carries no KIO conclusion. The retry copies only the `.dsc`, `.orig.tar.*` and `.debian.tar.*` source files and resolves `sbuild` ownership by account name rather than an assumed UID.

Diagnostic attempt 2 (workflow `36279908858`, job `108509683175`, artifact `10918078631`, SHA-256 `adb866de60351fa0cb104b3f10187df1532863af639a2ae1227367ae32e5e19f`) is also **INFRA_INVALID**. It reached source extraction but the manual wrapper tried to call `useradd`; the exact buildd rootfs does not contain that utility. No tests or package build ran.

Diagnostic attempt 3 (workflow `36280922944`, job `108512470733`) is **INFRA_INVALID** and produced no artifact: `SBUILD_LOG` was expanded before `EVIDENCE` was assigned under `set -u`. Execution stopped during initialization, before sbuild or package activity.

Diagnostic attempt 4 (workflow `36281142919`, job `108513096316`, artifact `10918188486`, SHA-256 `3e34166181099e5e5534a6e0e54138390ea5384eaf072ea3b0e2c17ab8266897`) is **INFRA_INVALID**. All historical inputs were downloaded and verified, but generation of `sbuild-config.pl` failed because Python %-formatting interpreted the hook's literal `%p`. sbuild itself was never invoked and no package/test execution occurred.

Diagnostic attempt 5 (workflow `36281666521`, job `108514584256`, artifact `10919077905`, SHA-256 `8cf052daaa71449c16caf978a19b8b372184ba29d1ccf047529417d9eead8c77`) is **INFRA_INVALID**. This time sbuild 0.91.2ubuntu3 opened the exact Attempt 8 rootfs, but session creation failed before dependency installation because the requested bind mountpoint `/supralinux-round23` did not exist in that rootfs. No KIO test or package command ran.

Diagnostic attempt 6 (workflow `36282461028`, job `108516845093`, artifact `10919516426`, SHA-256 `246b6bfb1a52a99718c8e242bb5b5907da8f84ec5844e8a62c685cbb78f74477`) is **INFRA_INVALID**. The exact rootfs verified that `/mnt` and `/media` existed and were empty, but sbuild-usernsexec still could not bind-mount the GitHub workspace filesystem into its user namespace (`ENOTTY`). This happened during session creation, before dependency installation, tests or package execution.

The retry removes `UNSHARE_BIND_MOUNTS` entirely. sbuild's documented external-command stdio transport is used instead: a `pre-build-commands` command copies the hook from the host to `/tmp/supralinux-round23-hook.sh` through `%SBUILD_CHROOT_EXEC`; `starting-build-commands` then executes it after dependencies are installed. The hook stores evidence in chroot-local `/tmp`, emits a compressed evidence tar as base64 over stdout, and the outer runner reconstructs that artifact from `sbuild.log`. No host filesystem is mounted into the chroot. citeturn248189search1turn248189search0

The retry preserves `%p` literally by replacing named placeholders rather than using Python's %-format operator. Policy's ShellCheck warning is also resolved by documenting the intentional indirect EXIT-trap invocation of `finish()`.

The retry also restores the exact rootfs-selection mechanism already proven by Attempt 8: the verified tarball is linked as `~/.cache/sbuild/resolute-amd64.tar` and sbuild is invoked with `--chroot-mode=unshare --dist=resolute`.

The retry now delegates containment to the actual Ubuntu Resolute `sbuild 0.91.2ubuntu3` unshare backend. The exact historical rootfs is selected through the same `~/.cache/sbuild/resolute-amd64.tar` mechanism as Attempt 8, the same predecessor packages are injected with `--extra-package`, and sbuild provides its native `sbuild` user and namespace. A `pre-build-commands` transfer injects the diagnostic script through sbuild's chroot-exec stdin channel. A `starting-build-commands` hook then runs the diagnostic after dependency installation and exits with sentinel code 86 before `dpkg-buildpackage`. The outer runner accepts the result only if the hook completes, the log contains no `Command: dpkg-buildpackage`, and no package artifacts exist.

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
