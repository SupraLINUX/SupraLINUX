# Current CI PR routing

Normal PR opened/synchronize/reopened events enter `pr-ci-router.yml` only. Repository Policy always runs and performs source syntax checks before validators.

`plan-pr-ci.py` selects current authorized Plasma work from relevant source/manifest changes. Qt provider preflight runs when its implementation or selected platform/desktop/Qt profile changes. Documentation and historical ledger edits do not reopen closed package campaigns.

Closed Frameworks and KIO workflows remain reusable/manual. Their validators preserve historical evidence without requiring a live PR registration. The existing semantic scope fixtures remain as historical regression coverage.

Concurrency is scoped to PR and head SHA, with cancellation disabled. Distinct heads can validate independently; valid in-flight evidence is retained. Authoritative KVM host execution keeps its separate serialized orchestration and exact run binding.

The three authoritative certification workflows retain controlled labeled-only PR entrypoints. They are deliberate operator requests, not ordinary PR fan-out. `validate_pr_workflow_entrypoints.py` enforces the entrypoint boundary.
