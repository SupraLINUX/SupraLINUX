#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT="${ROOT}/manifests/kde-tier3-provider-audit.json"
TIER3="${ROOT}/manifests/kde-frameworks-tier3.json"
DEPS="${ROOT}/manifests/kde-frameworks-tier3-dependencies.json"
OUT="${ROOT}/evidence/kde-tier3-provider-audit"

rm -rf "${OUT}"
mkdir -p "${OUT}"
exec > >(tee "${OUT}/provider-audit.log") 2>&1

echo "KDE Frameworks Tier 3 provider audit"
echo "KDE upstream selects version 6.30.0; Ubuntu Resolute is evaluated only as provider."
echo "This is not a package PASS and has package_state_effect=none."

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || {
  echo "Expected Ubuntu 26.04, got ${PRETTY_NAME}" >&2
  exit 1
}

python3 "${ROOT}/scripts/validate_kde_tier3_provider_audit.py"
sha256sum "${AUDIT}" "${TIER3}" "${DEPS}" > "${OUT}/inputs.sha256"
{
  printf 'PRETTY_NAME=%s\n' "${PRETTY_NAME}"
  printf 'VERSION_ID=%s\n' "${VERSION_ID}"
  uname -a
} > "${OUT}/host.txt"

sudo tee /etc/apt/sources.list.d/supralinux-tier3-provider-src.sources >/dev/null <<'EOF'
Types: deb-src
URIs: http://archive.ubuntu.com/ubuntu
Suites: resolute resolute-updates
Components: main universe
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb-src
URIs: http://security.ubuntu.com/ubuntu
Suites: resolute-security
Components: main universe
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   cmake dpkg-dev g++ ninja-build qt6-base-dev

# Prove source indexes are actually usable before interpreting a missing package
# as a legitimate "SupraLINUX required" provider decision.
apt-cache showsrc kf6-kcoreaddons > "${OUT}/source-index-baseline.txt"
grep -q '^Version:' "${OUT}/source-index-baseline.txt"

probe="$(mktemp -d)"
trap 'rm -rf "${probe}"' EXIT
cat > "${probe}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier3ProviderAudit LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Core)
message(STATUS "Qt6_VERSION=${Qt6_VERSION}")
CMAKE
cmake -S "${probe}" -B "${probe}/build" -GNinja |& tee "${OUT}/qt-provider-probe.log"
qt_version="$(grep -Eo 'Qt6_VERSION=[0-9]+\.[0-9]+\.[0-9]+' "${OUT}/qt-provider-probe.log" | tail -1 | cut -d= -f2)"
[[ -n "${qt_version}" ]] || { echo "Unable to prove Qt >=6.9 provider" >&2; exit 1; }
printf '%s\n' "${qt_version}" > "${OUT}/qt-version.txt"

python3 - "${AUDIT}" "${OUT}" "${qt_version}" <<'PY'
import json,re,subprocess,sys
from pathlib import Path

manifest=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])
qt_version=sys.argv[3]

def version_gt(a,b):
    return subprocess.run(["dpkg","--compare-versions",a,"gt",b]).returncode==0

def source_versions(source):
    p=subprocess.run(["apt-cache","showsrc",source],text=True,capture_output=True)
    text=p.stdout if p.returncode==0 else ""
    versions=[]
    package=None
    version=None
    for line in text.splitlines()+[""]:
        if not line.strip():
            if package==source and version:
                versions.append(version)
            package=version=None
            continue
        if line.startswith("Package: "):
            package=line.split(":",1)[1].strip()
        elif line.startswith("Version: "):
            version=line.split(":",1)[1].strip()
    return versions

def highest(versions):
    best=None
    for v in versions:
        if best is None or version_gt(v,best):
            best=v
    return best

def upstream(version):
    if not version:
        return None
    m=re.search(r"(\d+\.\d+\.\d+)",version)
    return m.group(1) if m else None

results={}
for node,c in manifest["components"].items():
    src=c["ubuntu_source_package"]
    versions=source_versions(src)
    candidate=highest(versions)
    ubuntu_upstream=upstream(candidate)
    required=c["required_upstream_version"]
    compatible=bool(candidate and ubuntu_upstream==required)
    decision="ubuntu-compatible" if compatible else "supralinux-required"
    reason=("exact-upstream-version-match" if compatible else
            "ubuntu-source-missing" if candidate is None else
            f"ubuntu-upstream-{ubuntu_upstream}-does-not-match-{required}")
    results[node]={
        "ubuntu_source_package":src,
        "candidate":candidate,
        "ubuntu_upstream_version":ubuntu_upstream,
        "required_upstream_version":required,
        "ubuntu_available":candidate is not None,
        "provider_decision":decision,
        "reason":reason,
    }

result={
    "schema":1,
    "result":"PASS",
    "claim":"framework-provider-selection-only",
    "authoritative_package_build":False,
    "package_state_effect":"none",
    "provider_platform":"ubuntu-resolute",
    "frameworks_series":"6.30.0",
    "qt_provider_version":qt_version,
    "nodes":results,
}
payload=json.dumps(result,indent=2,sort_keys=True)+"\n"
(out/"result.json").write_text(payload)
(out/"provider-decisions.tsv").write_text(
    "node\tsource\tcandidate\tubuntu-upstream\trequired\tdecision\treason\n"+
    "".join(
        f"{node}\t{r['ubuntu_source_package']}\t{r['candidate'] or '<missing>'}\t{r['ubuntu_upstream_version'] or '<missing>'}\t{r['required_upstream_version']}\t{r['provider_decision']}\t{r['reason']}\n"
        for node,r in sorted(results.items())
    )
)
summary={
    "ubuntu-compatible":sum(r["provider_decision"]=="ubuntu-compatible" for r in results.values()),
    "supralinux-required":sum(r["provider_decision"]=="supralinux-required" for r in results.values()),
    "missing":sum(not r["ubuntu_available"] for r in results.values()),
}
(out/"decision-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
PY

sha256sum "${OUT}/result.json" > "${OUT}/result.sha256"
echo "KDE Frameworks Tier 3 provider audit: PASS"
echo "package-state-effect=none"
