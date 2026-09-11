# KVM/libvirt host orchestration

Status: **implemented in repository; not yet executed on a real host**  
Last reviewed: **2026-09-11**

The long-lived host is an infrastructure provider only. It is not a SupraLINUX build runner and must not be treated as release evidence. Its job is to create one disposable Ubuntu 26.04 KVM guest for one authoritative GitHub Actions job, preserve host/runner diagnostics, and destroy the writable VM state afterwards.

## Current upstream inputs

The authoritative runner image starts from Ubuntu's **released** Resolute cloud image, not a daily image. As observed on 2026-09-11, the release endpoint publishes `ubuntu-26.04-server-cloudimg-amd64.img` under the Resolute released-image tree. SupraLINUX does not hard-code an image hash before downloading it; `scripts/fetch-ubuntu-26.04-cloud-image.sh` verifies `SHA256SUMS.gpg` with Ubuntu's cloud-image keyring and records the signed SHA-256 actually observed.

GitHub's current REST API provides repository-scoped JIT runner configuration through:

```text
POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig
```

The response includes a runner record and `encoded_jit_config`, which is passed to the runner process with `run.sh --jitconfig`. The JIT configuration is generated per VM and is not baked into the golden image.

## Host requirements

The orchestration user needs:

- KVM with `/dev/kvm` readable/writable;
- libvirt and an active network, `default` unless overridden;
- `virsh` and `virt-install`;
- `qemu-img`;
- `virt-copy-out` from libguestfs tools;
- `curl`, `jq`, `base64` and `sha256sum`;
- read access to the sealed golden qcow2 image;
- write access to the configured ephemeral-disk and host-evidence directories.

Nested virtualization must be enabled on the host. The definitive check remains inside the guest: the authoritative workflows require `/dev/kvm` to be usable from the Ubuntu 26.04 runner VM.

## Host authentication

`scripts/run-kvm-jit-gate.sh` consumes a host-only token from `SUPRALINUX_GITHUB_TOKEN` (or `GITHUB_TOKEN` as a fallback). It is never copied into the guest.

The token must be able to:

- create repository JIT runner configuration;
- list/delete repository self-hosted runners;
- read Actions runs;
- create/add/remove the controlled PR gate labels.

For fine-grained credentials this means repository Administration access sufficient for self-hosted-runner configuration, Actions read access, and Issues write access for labels. If the selected runner group is managed at organization scope, the host operator must also have the corresponding organization runner-group access.

The required runner group ID is supplied explicitly through `SUPRALINUX_RUNNER_GROUP_ID`; the script does not guess a group ID.

## Security boundary

Authoritative self-hosted workflows are not allowed to run arbitrary fork PRs. Both the workflow condition and the host orchestrator verify that the PR head repository is exactly `SupraLINUX/SupraLINUX` before a self-hosted gate is triggered.

The host waits for the JIT runner to become `online` before adding one of these controlled labels:

```text
ci:runner-contract
ci:authoritative-package-proof
```

The workflows listen only for the corresponding `pull_request` `labeled` event. `workflow_dispatch` remains available after the workflow exists on the default branch, but pre-merge certification does not depend on merging first.

## Golden image preparation

1. Fetch and verify the released Ubuntu 26.04 image:

   ```bash
   scripts/fetch-ubuntu-26.04-cloud-image.sh
   ```

2. Boot a preparation VM from that image under KVM, with nested KVM exposed.
3. Inside the guest, from the repository checkout, run:

   ```bash
   scripts/provision-authoritative-runner-guest.sh
   ```

4. Start a new login session so `kvm` group membership applies, then create the nested QEMU test image:

   ```bash
   scripts/prepare-autopkgtest-qemu-image.sh
   ```

5. Seal the golden image:

   ```bash
   scripts/seal-authoritative-runner-image.sh
   ```

6. Power the preparation VM off and use that disk only as a read-only backing image for ephemeral overlays.

The seal removes runner registration/job state and uses `cloud-init clean --logs --machine-id` so each clone receives a new machine identity on boot. The image remains **pending certification** until its first real contract and package-proof runs pass.

## One-job JIT gate lifecycle

For a real host, configure the golden image and runner group, then run one gate at a time:

```bash
export SUPRALINUX_GITHUB_TOKEN='...'
export SUPRALINUX_RUNNER_GROUP_ID='...'
export SUPRALINUX_GOLDEN_IMAGE='/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2'

scripts/run-kvm-jit-gate.sh runner-contract
scripts/run-kvm-jit-gate.sh authoritative-package-proof
```

For each invocation the host script:

1. verifies the target PR is open and same-repository;
2. creates a fresh qcow2 overlay from the sealed golden image;
3. boots a KVM VM with host CPU passthrough;
4. waits for qemu-guest-agent;
5. requests a fresh GitHub JIT configuration;
6. writes that configuration only to `/run/supralinux-jit-config` inside the guest;
7. launches the runner as the non-root runner user;
8. waits for the runner to become online;
9. adds the controlled PR label, causing exactly the requested self-hosted workflow to queue;
10. observes the runner become busy and then disappear after its one JIT job;
11. resolves the workflow conclusion and requires `success`;
12. removes the PR label, exports `_diag` and SupraLINUX evidence with libguestfs, records host/overlay metadata, and destroys the VM/overlay.

A failed or interrupted invocation still executes cleanup. An unused/stale JIT runner record is explicitly deleted where possible. No authoritative PASS is inferred from provisioning alone.

## Evidence

Host-side evidence is stored outside the guest under the configured host evidence root. It includes the PR head SHA, golden-image SHA-256, VM definition, runner state snapshots, resolved workflow run and exported guest diagnostics where available.

The GitHub workflow separately uploads package/runner evidence. Promotion decisions must use the workflow result plus retained evidence, not the host script exit code in isolation.

## Current blocker

No real KVM host has executed this orchestration yet. Therefore nested KVM, JIT guest startup, runner-group policy, QEMU system testing and destruction/export behavior remain **pending execution**, not PASS.
