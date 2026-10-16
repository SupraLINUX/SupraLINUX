#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${ROOT}/.work/diagnostic-infrastructure-preflight"
ROOTFS_DIR="${WORK}/rootfs"
SRCROOT="${WORK}/source"
OUT="${WORK}/out"
EVIDENCE="${ROOT}/evidence/diagnostic-infrastructure-preflight"
RESULT="${EVIDENCE}/result.json"
SBUILD_LOG="${EVIDENCE}/sbuild.log"
CONFIG="${WORK}/sbuild-config.pl"
HOOK="${WORK}/preflight-hook.sh"
STATE=INFRA_INVALID
STAGE=initialization
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${ROOTFS_DIR}" "${SRCROOT}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

# shellcheck disable=SC2329
write_result() {
  local rc="$1" finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p,state,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
  "schema":1,
  "scope":"diagnostic-infrastructure-preflight",
  "result":state,
  "exit_code":int(rc),
  "stage":stage,
  "started_at":started,
  "finished_at":finished,
  "authoritative":False,
  "package_attempted":False,
  "canonical_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
}
trap 'write_result "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3" zip
  mkdir -p "${dest}"
  zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" \
    -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=host-contract
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  curl dpkg-dev perl python3 sbuild uidmap unzip xz-utils
sbuild --version | tee "${EVIDENCE}/sbuild-version.txt"
grep -F '0.91.2ubuntu3' "${EVIDENCE}/sbuild-version.txt"
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true

STAGE=rootfs
download_artifact 10904512642 d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe "${ROOTFS_DIR}"
ROOTFS_TAR="$(find "${ROOTFS_DIR}" -type f -name 'resolute-amd64.tar' -print -quit)"
ROOTFS_SHA="$(find "${ROOTFS_DIR}" -type f -name 'rootfs.sha256' -print -quit)"
[[ -n "${ROOTFS_TAR}" && -s "${ROOTFS_TAR}" && -n "${ROOTFS_SHA}" && -s "${ROOTFS_SHA}" ]]
expected="$(awk '{print $1}' "${ROOTFS_SHA}")"
actual="$(sha256sum "${ROOTFS_TAR}" | awk '{print $1}')"
[[ "${expected}" == "${actual}" ]]
printf '%s\n' "${actual}" > "${EVIDENCE}/rootfs-tar.sha256"
SBUILD_CACHE="${HOME}/.cache/sbuild"
mkdir -p "${SBUILD_CACHE}"
ln -sfn "${ROOTFS_TAR}" "${SBUILD_CACHE}/resolute-amd64.tar"

STAGE=synthetic-source
PKG="${SRCROOT}/supralinux-diagnostic-preflight-1.0"
mkdir -p "${PKG}/debian/source"
cat > "${PKG}/debian/changelog" <<'EOF'
supralinux-diagnostic-preflight (1.0) resolute; urgency=medium

  * Synthetic diagnostic infrastructure probe.

 -- SupraLINUX CI <build@supralinux.invalid>  Sat, 26 Sep 2026 00:00:00 +0000
EOF
cat > "${PKG}/debian/control" <<'EOF'
Source: supralinux-diagnostic-preflight
Section: devel
Priority: optional
Maintainer: SupraLINUX CI <build@supralinux.invalid>
Standards-Version: 4.7.2
Build-Depends: dpkg-dev

Package: supralinux-diagnostic-preflight
Architecture: all
Description: SupraLINUX synthetic diagnostic infrastructure preflight
 This package must never reach dpkg-buildpackage. It exists only to certify
 sbuild diagnostic transport and lifecycle semantics.
EOF
cat > "${PKG}/debian/source/format" <<'EOF'
3.0 (native)
EOF
cat > "${PKG}/debian/rules" <<'EOF'
#!/usr/bin/make -f
%:
	@echo "ERROR: package build unexpectedly reached target $@" >&2
	@exit 99
EOF
chmod 0755 "${PKG}/debian/rules"
(
  cd "${SRCROOT}"
  dpkg-source -b "$(basename "${PKG}")"
)
DSC="$(find "${SRCROOT}" -maxdepth 1 -type f -name '*.dsc' -print -quit)"
[[ -n "${DSC}" && -s "${DSC}" ]]
sha256sum "${DSC}" > "${EVIDENCE}/synthetic-source.sha256"

STAGE=hook-definition
cat > "${HOOK}" <<'HOOK'
#!/usr/bin/env bash
set -Eeuo pipefail
PKGDIR="${1:?missing package build directory}"
EXPECTED=/build/reproducible-path/supralinux-diagnostic-preflight-1.0
EVIDENCE=/tmp/supralinux-diagnostic-preflight-evidence
rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}"
[[ "$(id -u)" -eq 0 ]]
[[ "${PKGDIR}" == "${EXPECTED}" ]]
[[ -d "${PKGDIR}" ]]
getent passwd sbuild > "${EVIDENCE}/sbuild-passwd.txt"
id sbuild > "${EVIDENCE}/sbuild-id.txt"
runuser -p -u sbuild -- id -un | grep -Fx sbuild > "${EVIDENCE}/runuser-sbuild.txt"
printf '%s\n' "${PKGDIR}" > "${EVIDENCE}/pkgbuild-dir.txt"
printf '%s\n' "PASS" > "${EVIDENCE}/status.txt"
touch "${EVIDENCE}/hook-complete"
printf '%s\n' 'SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_BEGIN'
tar -C "${EVIDENCE}" -czf - . | base64 -w0
printf '\n%s\n' 'SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_END'
exit 86
HOOK
chmod 0755 "${HOOK}"
bash -n "${HOOK}"

STAGE=sbuild-config
python3 - "${CONFIG}" "${HOOK}" <<'PY'
import shlex,sys
from pathlib import Path
path,hook=sys.argv[1:]
host_hook=shlex.quote(hook)
copy=f"cat {host_hook} | %SBUILD_CHROOT_EXEC sh -c 'cat > /tmp/supralinux-diagnostic-preflight-hook.sh && chmod 0755 /tmp/supralinux-diagnostic-preflight-hook.sh'"
text="""$chroot_mode = 'unshare';
$unshare_mmdebstrap_auto_create = 0;
$run_lintian = 0;
$run_autopkgtest = 0;
$run_piuparts = 0;
$log_external_command_output = 1;
$log_external_command_error = 1;
$external_commands = {
  'pre-build-commands' => [ __COPY__ ],
  'starting-build-commands' => [ [ '/bin/bash', '/tmp/supralinux-diagnostic-preflight-hook.sh', '%p' ] ],
};
1;
"""
Path(path).write_text(text.replace("__COPY__",repr(copy)))
PY
cp "${CONFIG}" "${EVIDENCE}/sbuild-config.pl"
perl -c "${CONFIG}" |& tee "${EVIDENCE}/sbuild-config-check.txt"
grep -F "%SBUILD_CHROOT_EXEC" "${CONFIG}" >/dev/null
grep -F "starting-build-commands" "${CONFIG}" >/dev/null

STAGE=sbuild-transport
set +e
SBUILD_CONFIG="${CONFIG}" sbuild \
  --verbose \
  --chroot-mode=unshare \
  --dist=resolute \
  --arch=amd64 \
  --arch-all \
  --no-run-lintian \
  --no-run-autopkgtest \
  --no-run-piuparts \
  --build-dir="${OUT}" \
  "${DSC}" |& tee "${SBUILD_LOG}"
SBUILD_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${SBUILD_RC}" > "${EVIDENCE}/sbuild-exit-code.txt"
(( SBUILD_RC != 0 ))

STAGE=evidence-recovery
python3 - "${SBUILD_LOG}" "${EVIDENCE}" <<'PY'
import base64,io,re,sys,tarfile
from pathlib import Path
text=Path(sys.argv[1]).read_text(errors="replace")
out=Path(sys.argv[2])
begin="SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_BEGIN"
end="SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_END"
match=re.search(re.escape(begin)+r"\s*([A-Za-z0-9+/=]+)\s*"+re.escape(end),text,re.S)
if not match:
    raise SystemExit("diagnostic preflight evidence markers missing")
raw=base64.b64decode(match.group(1),validate=True)
(out/"chroot-evidence.tar.gz").write_bytes(raw)
dest=out/"chroot"
dest.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as tf:
    for m in tf.getmembers():
        p=Path(m.name)
        if p.is_absolute() or ".." in p.parts:
            raise SystemExit(f"unsafe evidence member: {m.name}")
    tf.extractall(dest)
PY

STAGE=assertions
[[ "$(cat "${EVIDENCE}/chroot/status.txt")" == PASS ]]
[[ -f "${EVIDENCE}/chroot/hook-complete" ]]
[[ "$(cat "${EVIDENCE}/chroot/pkgbuild-dir.txt")" == /build/reproducible-path/supralinux-diagnostic-preflight-1.0 ]]
[[ "$(cat "${EVIDENCE}/chroot/runuser-sbuild.txt")" == sbuild ]]
if grep -Fq 'Command: dpkg-buildpackage' "${SBUILD_LOG}"; then
  echo "dpkg-buildpackage was reached; preflight invalid" >&2
  exit 83
fi
if find "${OUT}" -type f \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then
  echo "package artifacts were produced; preflight invalid" >&2
  exit 84
fi

STATE=PASS
STAGE=complete
