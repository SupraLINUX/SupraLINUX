# KDE Tier 3 KIO Round 23 — Attempt 8 rootfs KRecent diagnostic

Status: definition pending diagnostic retry.

Diagnostic attempt 1 (workflow `36279506026`) is recorded as **INFRA_INVALID**: the runner stopped at `stage-inputs` because a non-recursive wildcard attempted to copy the materialization artifact's `debian/` directory. No chroot test or package build occurred, so it carries no KIO conclusion. The retry copies only the `.dsc`, `.orig.tar.*` and `.debian.tar.*` source files and resolves `sbuild` ownership by account name rather than an assumed UID.

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

KIO is configured and fully compiled using its Debian rules inside that rootfs, but packaging is never attempted.

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
