# KDE Tier 3 KIO Attempt 10 symbol-metadata remediation

Status: **definition pending CI and source materialization**.  
Attempt 10 binary execution: **not authorized**.

## Attempt 9 evidence

Attempt 9 workflow `36416891314` proved the functional remediation in the real package path:

- KIO `6.30.0-0supralinux9`: **69/69 upstream tests PASS**;
- KXMLGui `6.30.0-0supralinux5`: **7/7 PASS** plus Python import PASS;
- KIO binary packages were produced;
- KIO failed only at Lintian symbol metadata.

The failure is package-owned, so Attempt 9 remains FAIL for KIO despite the complete upstream test PASS.

## Root cause

With `BUILD_TESTING=ON`, KIO 6.30 exposes 34 symbols absent from the Debian 6.30 symbols templates:

- 1 KIOCore symbol: `Worker::setTestWorkerFactory`, a private test hook declared in `worker_p.h`;
- 33 KIOGui `FilePreviewJob` symbols. Upstream wraps the class export in `KIOGUI_TEST_EXPORT`, which expands to `KIOGUI_EXPORT` only when `BUILD_TESTING` is enabled.

Because the templates omitted them, `dpkg-gensymbols` assigned `6.30.0-0supralinux9` as their first version. Lintian correctly rejected that Debian-revision ABI baseline.

## Remediation

Materialize those 34 symbols as:

- `(optional)`;
- minimum version `6.30.0`;
- private/test-build metadata, not public ABI;
- no Lintian override or suppression.

The exact KRecent source patch, visible test HOME, Qt SVG provider and complete 69-test policy remain unchanged.

## Package revision

```text
previous:  6.30.0-0supralinux9
candidate: 6.30.0-0supralinux10
```

The revision bump is required because the Debian symbols templates change.

## Lifecycle

This definition authorizes **KIO source/package materialization only**.

```text
Attempt 9 CLOSED-MIXED
→ Attempt 10 definition
→ materialize KIO 6.30.0-0supralinux10
→ verify symbols/source/package artifacts
→ planning validation
→ explicit Attempt 10 activation
→ binary build
```

KXMLGui is retained at `6.30.0-0supralinux5` and will be revalidated only in the full Level 1 rerun. Binary Attempt 10 remains unauthorized.

Current canonical state:

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux9 = FAIL
KXMLGui 6.30.0-0supralinux5 = PASS
Candidate KIO = 6.30.0-0supralinux10
Next gate = tier3-attempt10-kio-symbol-metadata-materialization-evidence
```
