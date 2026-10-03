#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT="${ROOT}/manifests/kde-tier3-support-provider-audit.json"
DEPS="${ROOT}/manifests/kde-frameworks-tier3-dependencies.json"
T1="${ROOT}/manifests/kde-frameworks-tier1.json"
T2="${ROOT}/manifests/kde-frameworks-tier2.json"
DESKTOP="${ROOT}/manifests/desktop-stack.json"
OUT="${ROOT}/evidence/kde-tier3-support-provider-audit"

rm -rf "${OUT}"
mkdir -p "${OUT}"
exec > >(tee "${OUT}/provider-audit.log") 2>&1

echo "KDE Frameworks Tier 3 support provider audit"
echo "This selects providers only; it is not a package PASS."

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }

python3 "${ROOT}/scripts/validate_kde_tier3_support_provider_audit.py"
sha256sum "${AUDIT}" "${DEPS}" "${T1}" "${T2}" "${DESKTOP}" > "${OUT}/inputs.sha256"

sudo apt-get update

mapfile -t external_packages < <(python3 - "${AUDIT}" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
pkgs=set()
for c in m["components"].values():
    pkgs.update(c.get("external_requirements",[]))
for p in sorted(pkgs):
    print(p)
PY
)

: > "${OUT}/external-candidates.tsv"
for package_name in "${external_packages[@]}"; do
    candidate="$(apt-cache policy "${package_name}" | awk '/Candidate:/ {print $2}')"
    printf '%s\t%s\n' "${package_name}" "${candidate:-<missing>}" | tee -a "${OUT}/external-candidates.tsv"
    [[ -n "${candidate}" && "${candidate}" != "(none)" ]] || { echo "Missing external provider: ${package_name}" >&2; exit 1; }
done

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${external_packages[@]}"

python3 - <<'PY' > "${OUT}/python-provider.txt"
import lxml
print("python3-lxml=PASS")
PY

pkg-config --exists libxml-2.0
pkg-config --exists libxslt
printf 'libxml2\t%s\nlibxslt\t%s\n' "$(pkg-config --modversion libxml-2.0)" "$(pkg-config --modversion libxslt)" > "${OUT}/pkg-config-versions.tsv"

test -d /usr/share/xml/docbook/schema/dtd/4.5 || find /usr/share/xml -path '*docbook*4.5*' -print -quit | grep .
find /usr/share/xml -path '*docbook*xsl*' -print -quit | grep .

probe="$(mktemp -d)"
trap 'rm -rf "${probe}"' EXIT
cat > "${probe}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier3SupportProviderAudit LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Core Gui DBus Widgets)
CMAKE
cmake -S "${probe}" -B "${probe}/build" -GNinja |& tee "${OUT}/qt-provider-probe.log"

python3 - "${AUDIT}" "${OUT}" <<'PY'
import json,re,subprocess,sys
from pathlib import Path

manifest=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])
results={}
for node,c in manifest["components"].items():
    pkg=c["ubuntu_probe_package"]
    policy=subprocess.check_output(["apt-cache","policy",pkg],text=True)
    candidate=None
    for line in policy.splitlines():
        if line.strip().startswith("Candidate:"):
            candidate=line.split(":",1)[1].strip()
            break
    if not candidate or candidate=="(none)":
        raise SystemExit(f"{node}: Ubuntu probe package missing: {pkg}")
    m=re.search(r"(\d+\.\d+\.\d+)",candidate)
    if not m:
        raise SystemExit(f"{node}: cannot extract upstream version from {candidate}")
    ubuntu_upstream=m.group(1)
    required=c["required_upstream_version"]
    decision="ubuntu-compatible" if ubuntu_upstream==required else "supralinux-required"
    results[node]={
        "probe_package":pkg,
        "candidate":candidate,
        "ubuntu_upstream_version":ubuntu_upstream,
        "required_upstream_version":required,
        "provider_decision":decision,
    }

result={
    "schema":1,
    "result":"PASS",
    "claim":"provider-selection-only",
    "authoritative_package_build":False,
    "package_state_effect":"none",
    "components":results,
}
(out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
(out/"provider-decisions.tsv").write_text("".join(
    f"{node}\t{r['probe_package']}\t{r['candidate']}\t{r['required_upstream_version']}\t{r['provider_decision']}\n"
    for node,r in sorted(results.items())
))
print(json.dumps(result,indent=2))
PY

echo "Tier 3 support provider audit: PASS"
echo "package-state-effect=none"
