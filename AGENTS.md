# SupraLINUX development

SupraLINUX builds and integrates official stable KDE releases on minimal Ubuntu
26.04 LTS. Select the newest KDE stack that passes the Ubuntu application
compatibility contract. A newer Qt dependency is a candidate transition, not
automatic permission to replace Qt. KDE upstream owns KDE development and fixes;
SupraLINUX owns build, packaging, integration, verification and delivery.

Read `docs/project-instructions.md`, `docs/status/current.md`, and the relevant
live manifests before changing a lifecycle. Verify repository, branch and HEAD;
handoffs are navigation aids. Historical evidence remains append-only, while its
applicability depends on unchanged relevant inputs. Never invent results.

Use `scripts/check-source-syntax.py` before executing validators. Repository
Policy is the complete verification entrypoint. Preserve closed build evidence;
ordinary PR CI routes only current work. Reusable/manual historical workflows are
available for intentional reproduction, not automatic reruns.

Prefer generic runners, planners and validators over new scripts per attempt.
An attempt begins at valid package execution; planning, materialization and
infrastructure probes are separate. Report build, package tests, infrastructure
and evidence-validation outcomes independently. A hosted PASS or cache admission
does not certify a package on the authoritative KVM lane.

Use disposable clean sbuild environments, exact eligible predecessor artifacts,
and milestone caches only while their inputs remain applicable. Verify artifact
digest, source package, Debian version and architecture before reuse. Preserve
sources, binaries, buildinfo, changes and logs independently of Actions expiry.

Continue authorized work through dependent gates until completion or a real
blocker. Routine fixes and testing are authorized. Final merge and stable
publication still require explicit approval and their release gates. Use the
authorized GitHub connector for repository reads and atomic publication. Host
scripts may use authenticated GitHub tools for artifact transport; keep tokens
out of output. Do not infer machine paths from another project's checkout.

After each KVM gate, verify that its ephemeral VM, runner and writable overlay
have been removed. Do not leave idle project VMs consuming resources. Preserve
golden images, milestone caches and sealed evidence; never stop unrelated VMs.
Follow active gates through cleanup before ending work or handing off a run.
