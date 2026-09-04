# Aurora KSQ-1 — orders 061–065 and KWallet/PAM package gate

Status: **ACCEPTED / PASS** for source orders 61–65 and the package/install/PAM-registration scope described here.

This record does **not** certify KWallet runtime session automatic unlock. That behavior remains a later end-to-end functional certification.

## Accepted candidate checkpoint

The maintained candidate advances from order 60 / 275 accumulated DEBs to order 65 / 295 accumulated DEBs.

Exact build evidence:

- source-build run: `33805321380`;
- source-build artifact: `9913134271`;
- artifact digest: `sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65`;
- exact range: orders `61..65`;
- sources: `5/5 PASS`;
- new DEBs: `20`;
- accumulated DEBs: `295`;
- prior accepted checkpoint: order 60 / `275` DEBs.

The source-build workflow itself was not used as the final KWallet acceptance authority because its first-generation post-build validator required further root-cause correction. The exact already-built candidate artifact above was therefore revalidated independently rather than rebuilt or altered.

## Immutable Ubuntu build slice remains unchanged

The canonical Ubuntu input remains:

- upstream snapshot: `20260829T022000Z`;
- SupraLINUX slice: `20260829T022000Z-r2`;
- binary objects: `1783`;
- r2 archive SHA-256: `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`.

r2 was **not mutated** to make the KWallet installation gate pass.

The order-65 install solver proved an exact 375-package runtime selection. Of those acquisitions, 372 were already physically present through r2/Supra candidate inputs and exactly three Ubuntu runtime objects were absent from r2:

- `lsb-base=11.6build1`;
- `libwrap0=7.6.q-36build2`;
- `socat=1.8.1.1-1ubuntu0.1`.

This is expected separation of concerns: r2 is the immutable build-closure slice, not a claim to be a complete arbitrary runtime-install mirror.

## KWallet runtime extension sidecar

The three-object set difference is published separately and immutably as:

- extension ID: `20260829T022000Z-kwallet-runtime-r1`;
- release ID: `382325880`;
- release tag: `ksq-kwallet-runtime-20260829T022000Z-r1`;
- archive asset ID: `543326513`;
- archive SHA-256: `89f9861d061a68498950bddb96b1f22ed41ddd205db118719f23b8836284b40e`;
- archive bytes: `2775040`;
- manifest asset ID: `543326512`;
- manifest SHA-256: `40a2a1f2e720dd07c93ecdfc52c42b1cd2202a495a749d2722109028cbdf0c32`;
- publication run: `33804710558`;
- independent validation artifact: `9912479235`, digest `sha256:6ae93f1906617e67734ca5afa6e675ec47aec2f27a7e0a0799c76145b84e8f1c`.

The sidecar is materialized from the same timestamped Ubuntu Snapshot Service state and validates signed Ubuntu `InRelease` metadata, signed `Packages.xz` hashes, exact package/version/architecture/filename, DEB size/SHA-256 and binary control identity.

Canonical pointer: `scripts/ci/aurora-ksq-kwallet-runtime-extension.env`.

## Correct installation model

The independent post-validator intentionally separates two concepts:

1. **APT package selection** from an empty dpkg status, which must reproduce the exact normal/default-Recommends KWallet closure of `375` packages;
2. **isolated rootfs bootstrap**, whose only purpose is to provide the minimum operational APT environment in which that selected closure can be installed and checked.

Ubuntu Resolute's current `mmdebstrap` documentation defines `--variant=apt` as the Essential set plus APT. It also states that mmdebstrap does not install Recommends by default and that normal Recommends behavior must be enabled explicitly with:

`--aptopt='Apt::Install-Recommends "true"'`

Official Resolute manpage: <https://manpages.ubuntu.com/manpages/resolute/man1/mmdebstrap.1.html>

Using `--variant=minbase` for this isolated runtime test was rejected after controlled evidence showed that it adds the full `Priority: required` set, introducing unrelated bootstrap packages that are outside the already-proven 375-package KWallet install selection. The accepted validator therefore uses:

- `mmdebstrap --mode=unshare --variant=apt`;
- `Apt::Install-Recommends "true"`;
- local r2 source only for Ubuntu archive content;
- exact local Supra candidate DEBs;
- exact three-object validated runtime sidecar;
- HTTP/HTTPS acquisition blocked by loopback proxy;
- file-mirror automount for local DEB inputs.

The resulting rootfs contains `396` packages total. The validator independently proves that all `375/375` packages selected by the KWallet solver are installed at the exact selected versions. The remaining 21 packages are bootstrap-set consequences and are not silently reclassified as part of the KWallet solver closure.

## Resolute `chroot` provider

The validator also removed an invalid legacy assumption that the host command must be `/usr/sbin/chroot`.

On the qualified Ubuntu 26.04 runner the resolved host command is:

- path: `/usr/bin/chroot`;
- owner: `coreutils-from-uutils`.

Ubuntu Resolute publishes `coreutils-from-uutils` as the uutils-backed coreutils provider. The validator now resolves and records the actual host command instead of forcing the GNU-layout path.

Ubuntu package record: <https://packages.ubuntu.com/resolute/all/coreutils-from-uutils>

## Exact post-validation evidence

Successful exact-candidate post-validation:

- run: `33819688197`;
- commit: `b35215edfa408fa2f13f2bf34d2afbbaa96c1f3a`;
- artifact: `9917851669`;
- artifact digest: `sha256:12b398c5f7388844861cca60f3fac37256eb94b3a32f57a31df8802bdf258a5c`;
- job conclusion: **SUCCESS**.

Proven invariants include:

- post-validator RC `0`, tee RC `0`;
- solver selections `375`;
- file URIs `372` + preseeded validated sidecar DEBs `3` = `375`;
- Recommends policy `default-enabled`;
- mmdebstrap RC `0`;
- bootstrap variant `apt`;
- install Recommends `true`;
- exact selected-package install verification `375/375 PASS`;
- total installed rootfs packages `396`;
- `apt-get check` successful;
- zero HTTP/HTTPS package transport;
- zero unresolved APT `Err:` acquisitions;
- relevant AppArmor denials `0`;
- Docker `0`;
- custom AppArmor `0`.

Exact candidate KWallet versions installed:

- `libpam-kwallet-common=4:6.7.4-0ubuntu3~supra26.04.1`;
- `libpam-kwallet5=4:6.7.4-0ubuntu3~supra26.04.1`;
- `kwallet6=6.29.0-0ubuntu1~supra26.04.1`;
- `libkf6wallet-data=6.29.0-0ubuntu1~supra26.04.1`;
- `libkf6wallet6=6.29.0-0ubuntu1~supra26.04.1`;
- `libkf6walletbackend6=6.29.0-0ubuntu1~supra26.04.1`.

PAM registration is present in both `common-auth` and `common-session`.

## Independent acceptance gate

A second workflow accepts only the exact successful post-validation artifact and fails closed on the stronger final invariants above.

Final acceptance:

- workflow: `.github/workflows/ksq-accept-061-065-r2-kwallet-sidecar.yml`;
- run: `33821228782`;
- commit: `5b021477f00ab97e03b19e19da4e681abd7af7c0`;
- artifact: `9918320108`;
- artifact digest: `sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730`;
- conclusion: **SUCCESS**.

The downloaded acceptance artifact was independently checked outside the runner. Its relative `evidence.sha256` and top-level `artifact-manifest.sha256` both verify successfully after extraction, so the acceptance evidence is relocatable and self-verifying.

## Scope boundary

This closes the KSQ-1 package gate through order 65 only.

It proves package relationships, complete local installation of the exact KWallet closure, exact candidate versions, APT consistency and PAM module registration.

It deliberately records:

`AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED=no`

Runtime login/session automatic unlock is therefore **not** inferred from this result and must be certified in the later functional session gate.

## Next build unit

Orders `66..80` are now unblocked for native r2 qualification. No packaging adaptation is currently declared for orders 66–80, so that range must record zero applied adaptation IDs for all 15 sources. Order 68 `drkonqi` also remains subject to its later dedicated independent reproducibility rebuild under the maintained 95+6 contract.
