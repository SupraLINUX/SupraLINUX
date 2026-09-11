# KVM/libvirt host orchestration

Status: **host bootstrap, golden-image build and JIT orchestration implemented; not yet executed on a real host**  
Last reviewed: **2026-09-11**

The long-lived host is an infrastructure provider only. It is not a SupraLINUX build runner and must not be treated as release evidence. Its job is to provide KVM/libvirt, build the sealed Ubuntu 26.04 golden runner image, create one disposable runner guest per authoritative GitHub Actions job, preserve host/runner diagnostics, and destroy writable VM state afterwards.

## Current upstream inputs

The authoritative runner image starts from Ubuntu's **released** Resolute cloud image, not a daily image. `scripts/fetch-ubuntu-26.04-cloud-image.sh` verifies `SHA256SUMS.gpg` with Ubuntu's cloud-image keyring and records the signed SHA-256 actually observed.

GitHub's REST API provides repository-scoped JIT runner configuration through:

```text
POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig
```

The response includes a runner record and `encoded_jit_config`, which is passed to `run.sh --jitconfig`. The JIT configuration is generated per VM and is not baked into the golden image.

Ubuntu 26.04 provides the host packages used by the supported bootstrap recipe, including `libvirt-daemon-system`, `qemu-system-x86`, `virt-install` and `libguestfs-tools`. Exact installed versions are runtime evidence from the real host.

## Supported host bootstrap recipe

The repository currently supports an automated host-bootstrap recipe for **Ubuntu 26.04 amd64/x86_64**. Ubuntu is the provider for this CI infrastructure recipe; it does not become authoritative for KDE or desktop contents.

Run as the intended orchestration user with sudo available:

```bash
scripts/provision-kvm-host.sh
```

The script installs KVM/QEMU, libvirt, `virt-install`, libguestfs and support tools, configures `kvm`/`libvirt` group access, starts the selected libvirt network when available and records host package/network/module state.

It deliberately does **not** alter firmware/BIOS settings or forcibly unload/reload KVM modules. Those operations can disrupt existing VMs and require explicit operator action.

After provisioning, open a new login session and run the read-only preflight:

```bash
scripts/check-kvm-host.sh
```

The preflight requires:

- x86_64 and visible `vmx`/`svm`;
- `/dev/kvm` present and readable/writable;
- user membership in `kvm` and `libvirt`;
- nested virtualization enabled in the loaded vendor KVM module;
- QEMU/KVM, `virsh`, `virt-install`, `virt-sysprep`, `virt-cat`, `virt-copy-out` and support commands;
- working `qemu:///system` access;
- an active configured libvirt network.

If nested KVM is disabled, the preflight reports **FAIL** and does not attempt to modify the host automatically.

## Golden image build

After host preflight passes:

```bash
scripts/fetch-ubuntu-26.04-cloud-image.sh
scripts/build-authoritative-runner-image.sh
```

`build-authoritative-runner-image.sh` is the preferred reproducible path. It requires the verified source image plus provenance, creates a preparation overlay, boots it under KVM with host CPU passthrough, checks out the exact requested SupraLINUX commit, provisions the guest, creates the nested `autopkgtest` image, seals guest-side state, powers the VM off, exports evidence, runs explicit offline `virt-sysprep`, flattens the overlay, validates the resulting qcow2 with `qemu-img check` and records its SHA-256/provenance.

Default output:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

An existing image is not replaced unless the operator explicitly sets:

```bash
SUPRALINUX_REPLACE_GOLDEN_IMAGE=1
```

A failed golden build preserves its work directory/evidence and must not be treated as a certified image.

## Host authentication

`scripts/run-kvm-jit-gate.sh` consumes a host-only token from `SUPRALINUX_GITHUB_TOKEN` (or `GITHUB_TOKEN` as fallback). It is never copied into the guest.

The token must be able to create repository JIT runner configuration, list/delete repository runners, read Actions runs, and create/add/remove the controlled PR gate labels. The runner group ID is supplied explicitly through `SUPRALINUX_RUNNER_GROUP_ID`; the script does not guess one.

## Security boundary

Authoritative self-hosted workflows are not allowed to run arbitrary fork PRs. Both the workflow condition and the host orchestrator verify that the PR head repository is exactly `SupraLINUX/SupraLINUX` before a self-hosted gate is triggered.

The host waits for the JIT runner to become `online` before adding one controlled label:

```text
ci:runner-contract
ci:authoritative-package-proof
```

## One-job JIT gate lifecycle

With a sealed golden image and runner group configured:

```bash
export SUPRALINUX_GITHUB_TOKEN='...'
export SUPRALINUX_RUNNER_GROUP_ID='...'
export SUPRALINUX_GOLDEN_IMAGE='/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2'

scripts/run-kvm-jit-gate.sh runner-contract
scripts/run-kvm-jit-gate.sh authoritative-package-proof
```

For each invocation the host script:

1. verifies the target PR is open and same-repository;
2. creates a fresh qcow2 overlay from the golden image;
3. boots a KVM VM with host CPU passthrough;
4. waits for qemu-guest-agent;
5. requests a fresh GitHub JIT configuration;
6. writes that configuration only to `/run/supralinux-jit-config` in the guest;
7. launches the non-root runner;
8. waits for it to become online;
9. adds exactly the requested controlled PR label;
10. observes the one JIT job;
11. requires the workflow conclusion to be `success`;
12. removes the label, exports `_diag` and SupraLINUX evidence, and destroys the VM/overlay.

Cleanup runs on failed/interrupted invocations. No authoritative PASS is inferred from provisioning or from the host script alone.

## Evidence

Host-side evidence includes host provisioning/preflight data, verified source-image provenance, golden-image build inputs, guest provisioning evidence, offline sysprep log, qcow2 validation, golden-image SHA-256, PR head SHA, VM definition, runner state snapshots, resolved workflow run and exported guest diagnostics.

The GitHub workflow separately uploads package/runner evidence. Promotion decisions require the workflow result plus retained evidence.

## Current blocker

No real KVM host has executed this complete chain yet. Therefore host preflight, golden-image build, nested KVM, JIT startup, runner-group policy, QEMU system testing and cleanup/export behavior remain **pending execution**, not PASS.
