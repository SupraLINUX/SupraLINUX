# KDE Frameworks 6.30 — Batch 2 CI gate evidence

Last reviewed: **2026-09-14**

## Workflow 34884049556

Use commit `e251338e7347e47245a83a64a6ec2efa1651b4ff`.

Classify this workflow as a **CI harness failure**.

Do not classify its three package nodes as package-own FAIL.

All three package builds completed before the wrapper failure.

### KTextTemplate

Use job `104110141498`.

Use artifact `10364256456`.

Use artifact SHA-256 `006b1f60aa28132d1da975432f98acdb57c257430ef3aaabea4e239252edbf0d`.

Record revision `6.30.0-0supralinux3`.

Record `10/10` upstream tests PASS.

Record `Lintian: warn` from `sbuild`.

Record consumer smoke PASS.

Record wrapper failure at `lintian-source-binary`.

### KArchive

Use job `104110142062`.

Use artifact `10364111842`.

Use artifact SHA-256 `6208a5cb9ccf4e1dfb34248573f9cf937dc2e320165ecd811625fbf6ea7c0b5c`.

Record revision `6.30.0-0supralinux4`.

Record `5/5` upstream tests PASS.

Record `Lintian: warn` from `sbuild`.

Record consumer smoke PASS.

Record wrapper failure at `lintian-source-binary`.

### KHolidays

Use job `104110141944`.

Use artifact `10364111805`.

Use artifact SHA-256 `1256146d001bd6792d7844c034cf4589890e51c1e84c2371a8f893d362b1b774`.

Record revision `6.30.0-0supralinux4`.

Record `8/8` upstream tests PASS.

Record `Lintian: warn` from `sbuild`.

Record consumer smoke PASS.

Record wrapper failure at `lintian-source-binary`.

Confirm removal of the previous `python3` prerequisite error.

## Root cause

Inspect standalone Lintian after the successful base runner.

Observe each `.changes` file referencing a generated `*-dbgsym_*.ddeb`.

Observe the evidence directory lacking that referenced `.ddeb`.

Observe Lintian aborting before evaluating the complete `.changes` input.

Example failure:

`libkf6holidays6-dbgsym_6.30.0-0supralinux4_amd64.ddeb does not exist`.

Treat this condition as a wrapper defect.

Do not change KDE source for this defect.

Do not change package revisions for this defect.

## Remediation

Copy generated `.ddeb` files from the build output directory.

Preserve their SHA-256 values as CI evidence.

Run standalone Lintian against `.dsc` and `.changes` afterward.

Retain the existing `sbuild` summary check for `Lintian: fail`.

Keep `dag-node.txt` absent when the corrected gate fails.

Rerun all three nodes after changing the shared wrapper.

Promote no node until that rerun completes.
