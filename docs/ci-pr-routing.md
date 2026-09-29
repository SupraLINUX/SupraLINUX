# CI PR routing architecture

Normal pull-request events have exactly one entrypoint: `.github/workflows/pr-ci-router.yml`.

The router is responsible for:

- running Repository Policy on every normal PR through `workflow_call`;
- deciding whether a semantic delta needs reusable build/reference/provider lanes;
- activating only the lifecycle-specific diagnostic or remediation lane that is currently authorized;
- skipping expensive historical lanes when their evidence is already closed.

Repository Policy keeps direct `push` validation on `main`, remains manually runnable with `workflow_dispatch`, and is reusable through `workflow_call`. It does not listen to normal PR events directly.

Closed Tier 2/Tier 3 workflows are retained as reusable/manual workflows. Historical KIO diagnostic/remediation workflows are `workflow_call` + `workflow_dispatch` only; changing an unrelated manifest must not recapture them.

Two exceptional workflows may still use `pull_request`, but only with `types: [labeled]`:

- `authoritative-package-proof.yml`;
- `runner-contract.yml`.

Those label-gated actions are explicit operator requests, not normal PR CI.

The invariant is enforced by `scripts/validate_pr_workflow_entrypoints.py` from Repository Policy. Adding a new direct normal-PR listener outside the router is a Policy failure.
