#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE="${ROOT}/scripts/ci/validate-ksq-1-kwallet-pam-runtime-sidecar.sh"
EXPECTED_BLOB="41d95eb5126052229e822061e979b32e700f7c33"
TMP="${ROOT}/scripts/ci/.validate-ksq-1-kwallet-runtime-sidecar-v4-${GITHUB_RUN_ID:-local}.sh"

fail() { echo "AURORA_KSQ_1_KWALLET_POSTBUILD_FAILURE: $*" >&2; exit 1; }

[[ -f "${SOURCE}" ]] || fail "source validator missing"
command -v git >/dev/null || fail "git missing"
command -v python3 >/dev/null || fail "python3 missing"
[[ "$(git -C "${ROOT}" hash-object "${SOURCE}")" == "${EXPECTED_BLOB}" ]] \
  || fail "source validator blob changed; review the v4 delta before reuse"

python3 - "${SOURCE}" "${TMP}" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text()
start_marker = 'APT_CONFIG="${SOLVER}/preload.conf" apt-get "${apt_opts[@]}" --download-only --yes --no-remove install "${TARGET_SPECS[@]}" \\\n'
end_marker = '\ncleanup_rootfs() {'
start = text.find(start_marker)
if start < 0:
    raise SystemExit('postbuild validator: solver download marker not found')
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit('postbuild validator: cleanup marker not found')
if text.find(start_marker, start + 1) >= 0:
    raise SystemExit('postbuild validator: solver download marker is not unique')

replacement = r'''# Prove the solver selection independently of APT's archive-cache behavior.
# apt-get --simulate emits one Inst line per selected unpack operation. With the
# empty dpkg status used above, the exact KWallet install closure must contain 375
# package operations under normal/default Recommends semantics.
APT_CONFIG="${SOLVER}/preload.conf" apt-get "${apt_opts[@]}" --simulate --no-remove install "${TARGET_SPECS[@]}" \
  2>&1 | tee "${EVIDENCE}/solver-simulate.log"
! grep -q '^Remv ' "${EVIDENCE}/solver-simulate.log" || fail "solver simulation requested removals"
SIMULATED_INSTALL_COUNT="$(grep -c '^Inst ' "${EVIDENCE}/solver-simulate.log" || true)"
[[ "${SIMULATED_INSTALL_COUNT}" -eq 375 ]] || fail "expected 375 simulated install operations, got ${SIMULATED_INSTALL_COUNT}"

# --print-uris enumerates objects APT would retrieve. The three independently
# validated sidecar DEBs are already preseeded in Dir::Cache::archives, so they
# are deliberately absent from this URI list. Every remaining object must be a
# local file: URI and URI objects + preseeded objects must equal the simulation.
APT_CONFIG="${SOLVER}/preload.conf" apt-get "${apt_opts[@]}" --print-uris --yes --no-remove install "${TARGET_SPECS[@]}" \
  2>&1 | tee "${EVIDENCE}/solver-uris.log"
URI_LINE_COUNT="$(grep -c "^'" "${EVIDENCE}/solver-uris.log" || true)"
FILE_URI_COUNT="$(grep -c "^'file:" "${EVIDENCE}/solver-uris.log" || true)"
[[ "${URI_LINE_COUNT}" -eq "${FILE_URI_COUNT}" ]] || fail "solver URI list contains non-file transport"
! grep -E "^'https?://" "${EVIDENCE}/solver-uris.log" || fail "remote solver URI emitted"
PRESEEDED_DEB_COUNT="$(awk -F '\t' 'NR > 1 && $5 == "yes" {count++} END {print count+0}' "${EVIDENCE}/runtime-extension-staging.tsv")"
[[ "${PRESEEDED_DEB_COUNT}" -eq 3 ]] || fail "expected exactly three preseeded runtime-extension DEBs, got ${PRESEEDED_DEB_COUNT}"
[[ $((FILE_URI_COUNT + PRESEEDED_DEB_COUNT)) -eq "${SIMULATED_INSTALL_COUNT}" ]] \
  || fail "solver object accounting mismatch: file_uris=${FILE_URI_COUNT} preseeded=${PRESEEDED_DEB_COUNT} selected=${SIMULATED_INSTALL_COUNT}"

# Actually retrieve the complete closure from local sources. APT is permitted to
# consume file: objects in place instead of copying them into Dir::Cache::archives;
# success here proves every selected local object is physically available.
APT_CONFIG="${SOLVER}/preload.conf" apt-get "${apt_opts[@]}" --download-only --yes --no-remove install "${TARGET_SPECS[@]}" \
  2>&1 | tee "${EVIDENCE}/solver-download.log"
! grep -E '^(Get|Hit|Ign|Err):[0-9]+ https?://' "${EVIDENCE}/solver-download.log" || fail "remote solver package transport occurred"
! grep -q '^Err:[0-9]' "${EVIDENCE}/solver-download.log" || fail "local solver still has unresolved package objects"

# Parse the exact simulated package/version selection and materialize only those
# Supra candidate DEBs that the solver selected. The sidecar packages are already
# present in CLOSURE from the independently validated staging step.
python3 - "${EVIDENCE}/solver-simulate.log" "${EVIDENCE}/solver-selected-packages.tsv" <<'PYSEL'
from pathlib import Path
import re
import sys

src, dst = map(Path, sys.argv[1:])
rows = []
seen = set()
for line in src.read_text(errors='replace').splitlines():
    if not line.startswith('Inst '):
        continue
    m = re.match(r'^Inst\s+(\S+)\s+\((\S+)', line)
    if not m:
        raise SystemExit(f'unparseable apt simulation line: {line}')
    package, version = m.groups()
    if package.endswith(':amd64') or package.endswith(':all'):
        package = package.rsplit(':', 1)[0]
    if package in seen:
        raise SystemExit(f'duplicate simulated package: {package}')
    seen.add(package)
    rows.append((package, version))
if len(rows) != 375:
    raise SystemExit(f'expected 375 parsed simulated packages, got {len(rows)}')
with dst.open('w') as fh:
    fh.write('package\tversion\n')
    for package, version in rows:
        fh.write(f'{package}\t{version}\n')
PYSEL

printf 'package\tversion\tarchitecture\tfilename\n' > "${EVIDENCE}/candidate-closure.tsv"
while IFS=$'\t' read -r package version; do
  [[ "${package}" != package ]] || continue
  if [[ -n "${CANDIDATE_PATH[${package}]:-}" ]]; then
    [[ "${version}" == "${CANDIDATE_VERSION[${package}]}" ]] \
      || fail "solver selected non-candidate ${package}=${version} instead of ${CANDIDATE_VERSION[${package}]}"
    original="${CANDIDATE_PATH[${package}]}"
    arch="${CANDIDATE_ARCH[${package}]}"
    target="${CLOSURE}/$(basename "${original}")"
    [[ ! -e "${target}" ]] || fail "candidate closure duplicate ${package}"
    install -m 0644 "${original}" "${target}"
    printf '%s\t%s\t%s\t%s\n' "${package}" "${version}" "${arch}" "$(basename "${original}")" \
      >> "${EVIDENCE}/candidate-closure.tsv"
  fi
done < "${EVIDENCE}/solver-selected-packages.tsv"

CLOSURE_DEB_COUNT="$(find "${CLOSURE}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
[[ "${CLOSURE_DEB_COUNT}" -ge 9 ]] || fail "local include closure unexpectedly small: ${CLOSURE_DEB_COUNT}"
for spec in "${TARGET_SPECS[@]}"; do
  wanted_package="${spec%%=*}"
  wanted_version="${spec#*=}"
  awk -F '\t' -v p="${wanted_package}" -v v="${wanted_version}" 'NR > 1 && $1 == p && $2 == v {found=1} END {exit !found}' \
    "${EVIDENCE}/candidate-closure.tsv" || fail "target ${wanted_package}=${wanted_version} absent from candidate closure"
done
for package in lsb-base libwrap0 socat; do
  awk -F '\t' -v p="${package}" 'NR > 1 && $1 == p && $5 == "yes" && $6 == "yes" {found=1} END {exit !found}' \
    "${EVIDENCE}/runtime-extension-staging.tsv" || fail "runtime extension ${package} not present in both local closures"
done
(
  cd "${CLOSURE}"
  find . -maxdepth 1 -type f -name '*.deb' -printf '%f\0' | sort -z | xargs -0 -r sha256sum
) > "${EVIDENCE}/candidate-closure.sha256"
printf 'AURORA_KSQ_1_KWALLET_SOLVER_DEBS=%s\nAURORA_KSQ_1_KWALLET_SOLVER_SELECTED_PACKAGES=%s\nAURORA_KSQ_1_KWALLET_SOLVER_FILE_URIS=%s\nAURORA_KSQ_1_KWALLET_SOLVER_PRESEEDED_DEBS=%s\nAURORA_KSQ_1_KWALLET_SOLVER_ENUMERATION=apt-simulate+print-uris\nAURORA_KSQ_1_KWALLET_CANDIDATE_CLOSURE_DEBS=%s\nAURORA_KSQ_1_KWALLET_RECOMMENDS_POLICY=default-enabled\n' \
  "${SIMULATED_INSTALL_COUNT}" "${SIMULATED_INSTALL_COUNT}" "${FILE_URI_COUNT}" "${PRESEEDED_DEB_COUNT}" "${CLOSURE_DEB_COUNT}" \
  > "${EVIDENCE}/solver-closure.env"

SOLVER_DEB_COUNT="${SIMULATED_INSTALL_COUNT}"
'''

patched = text[:start] + replacement + text[end:]

# minbase adds the unrelated Priority:required bootstrap set. For this isolated
# package-install proof use the documented apt variant (Essential + apt) and let
# the explicitly included KWallet targets pull their own dependency closure.
minbase_marker = '  --mode=unshare --variant=minbase --architectures=amd64 \\\n'
apt_marker = '  --mode=unshare --variant=apt --architectures=amd64 \\\n'
if patched.count(minbase_marker) != 1:
    raise SystemExit('postbuild validator: expected exactly one minbase bootstrap marker')
patched = patched.replace(minbase_marker, apt_marker, 1)

# mmdebstrap disables Recommends by default. The solver and the maintained r2
# builder contract use normal APT semantics, so explicitly restore that policy.
proxy_marker = '  --aptopt=\'Acquire::https::Proxy "http://127.0.0.1:9";\' \\\n'
if patched.count(proxy_marker) != 1:
    raise SystemExit('postbuild validator: https proxy aptopt marker is not unique')
patched = patched.replace(
    proxy_marker,
    proxy_marker + '  --aptopt=\'Apt::Install-Recommends "true";\' \\\n',
    1,
)

install_inputs_marker = 'printf \'AURORA_KSQ_1_KWALLET_INCLUDE_DEBS=%s\\n\' "${CLOSURE_DEB_COUNT}" > "${EVIDENCE}/installation-inputs.env"\n'
if patched.count(install_inputs_marker) != 1:
    raise SystemExit('postbuild validator: installation input marker is not unique')
patched = patched.replace(
    install_inputs_marker,
    install_inputs_marker
    + 'printf \'AURORA_KSQ_1_KWALLET_BOOTSTRAP_VARIANT=apt\\nAURORA_KSQ_1_KWALLET_INSTALL_RECOMMENDS=true\\n\' >> "${EVIDENCE}/installation-inputs.env"\n',
    1,
)

# Ubuntu 26.04 defaults to coreutils-from-uutils, whose chroot lives in /usr/bin.
# Resolve the host binary instead of assuming the GNU-provider /usr/sbin path.
first_helper = 'mmdebstrap --unshare-helper /usr/sbin/chroot "${ROOTFS}" apt-get check | tee "${EVIDENCE}/apt-check.txt"\n'
if patched.count(first_helper) != 1:
    raise SystemExit('postbuild validator: apt-check helper marker is not unique')
helper_prelude = r'''CHROOT_BIN="$(command -v chroot || true)"
[[ -n "${CHROOT_BIN}" && -x "${CHROOT_BIN}" ]] || fail "host chroot binary unavailable"
CHROOT_OWNER="$(dpkg-query -S "${CHROOT_BIN}" 2>/dev/null | head -n 1 || true)"
[[ -n "${CHROOT_OWNER}" ]] || fail "host chroot package ownership unavailable"
printf 'AURORA_KSQ_1_KWALLET_HOST_CHROOT=%s\nAURORA_KSQ_1_KWALLET_HOST_CHROOT_OWNER=%s\n' \
  "${CHROOT_BIN}" "${CHROOT_OWNER}" > "${EVIDENCE}/host-chroot.env"

'''
patched = patched.replace(first_helper, helper_prelude + first_helper, 1)
patched = patched.replace('/usr/sbin/chroot', '"${CHROOT_BIN}"')

# Prove that every package/version selected by the independent 375-operation
# solver is installed in the rootfs, not merely that the six direct targets are.
installed_versions_marker = 'mmdebstrap --unshare-helper "${CHROOT_BIN}" "${ROOTFS}" dpkg-query -W \\\n  libpam-kwallet-common libpam-kwallet5 kwallet6 libkf6wallet-data libkf6wallet6 libkf6walletbackend6 \\\n  | sort | tee "${EVIDENCE}/installed-versions.tsv"\n'
if patched.count(installed_versions_marker) != 1:
    raise SystemExit('postbuild validator: installed-version query marker is not unique')
verify_block = r'''mmdebstrap --unshare-helper "${CHROOT_BIN}" "${ROOTFS}" dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' \
  | sort > "${EVIDENCE}/installed-all-packages.tsv"
python3 - "${EVIDENCE}/solver-selected-packages.tsv" "${EVIDENCE}/installed-all-packages.tsv" "${EVIDENCE}/selected-install-verification.tsv" <<'PYVERIFY'
from pathlib import Path
import sys

selected_path, installed_path, out_path = map(Path, sys.argv[1:])
selected = {}
for line in selected_path.read_text().splitlines()[1:]:
    if not line:
        continue
    package, version = line.split('\t')
    if package in selected:
        raise SystemExit(f'duplicate selected package {package}')
    selected[package] = version
if len(selected) != 375:
    raise SystemExit(f'expected 375 selected packages, got {len(selected)}')
installed = {}
for line in installed_path.read_text().splitlines():
    if not line:
        continue
    package, version, arch = line.split('\t')
    if arch not in ('amd64', 'all'):
        raise SystemExit(f'unexpected installed architecture {package}={arch}')
    if package in installed:
        raise SystemExit(f'duplicate installed package {package}')
    installed[package] = version
rows = []
missing = []
mismatch = []
for package, wanted in selected.items():
    actual = installed.get(package)
    if actual is None:
        missing.append(package)
        rows.append((package, wanted, '', 'MISSING'))
    elif actual != wanted:
        mismatch.append((package, wanted, actual))
        rows.append((package, wanted, actual, 'MISMATCH'))
    else:
        rows.append((package, wanted, actual, 'PASS'))
with out_path.open('w') as fh:
    fh.write('package\tselected_version\tinstalled_version\tstatus\n')
    for row in sorted(rows):
        fh.write('\t'.join(row) + '\n')
if missing or mismatch:
    raise SystemExit(f'selected closure install mismatch: missing={len(missing)} version_mismatch={len(mismatch)}')
print(f'AURORA_KSQ_1_KWALLET_SELECTED_INSTALL_VERIFIED={len(rows)}')
print(f'AURORA_KSQ_1_KWALLET_INSTALLED_TOTAL_PACKAGES={len(installed)}')
PYVERIFY
SELECTED_INSTALL_VERIFIED="$(awk -F '\t' 'NR > 1 && $4 == "PASS" {n++} END {print n+0}' "${EVIDENCE}/selected-install-verification.tsv")"
[[ "${SELECTED_INSTALL_VERIFIED}" -eq 375 ]] || fail "not all 375 solver-selected packages were installed"
INSTALLED_TOTAL_PACKAGES="$(wc -l < "${EVIDENCE}/installed-all-packages.tsv")"
printf 'AURORA_KSQ_1_KWALLET_SELECTED_INSTALL_VERIFIED=%s\nAURORA_KSQ_1_KWALLET_INSTALLED_TOTAL_PACKAGES=%s\nAURORA_KSQ_1_KWALLET_INSTALL_RECOMMENDS=true\n' \
  "${SELECTED_INSTALL_VERIFIED}" "${INSTALLED_TOTAL_PACKAGES}" > "${EVIDENCE}/selected-install-status.env"

'''
patched = patched.replace(installed_versions_marker, verify_block + installed_versions_marker, 1)

target.write_text(patched)
PY

chmod 0755 "${TMP}"
bash -n "${TMP}"
trap 'rm -f "${TMP}"' EXIT
bash "${TMP}"
