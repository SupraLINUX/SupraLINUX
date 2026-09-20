#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS="${ROOT}/manifests/kde-frameworks-tier2-dependencies.json"
PLAN="${ROOT}/manifests/kde-tier2-campaign-plan.json"
TIER1_REGISTRY="${ROOT}/manifests/kde-frameworks-tier1-dependencies.json"
TIER1="${ROOT}/manifests/kde-frameworks-tier1.json"
DESKTOP="${ROOT}/manifests/desktop-stack.json"
EVIDENCE="${ROOT}/evidence/kde-tier2-provider-audit"

rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/provider-audit.log") 2>&1

echo "KDE Frameworks Tier 2 provider audit"
echo "This proves provider availability/profile compatibility only; it is not a package PASS."

. /etc/os-release
if [[ "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04, got ${PRETTY_NAME}" >&2
    exit 1
fi

python3 "${ROOT}/scripts/validate_kde_tier2_provider_audit.py"
sha256sum "${DEPS}" "${PLAN}" "${TIER1_REGISTRY}" "${TIER1}" "${DESKTOP}" > "${EVIDENCE}/inputs.sha256"
{
    printf 'PRETTY_NAME=%s\n' "${PRETTY_NAME}"
    printf 'VERSION_ID=%s\n' "${VERSION_ID}"
    uname -a
} > "${EVIDENCE}/host.txt"

python3 - "${DEPS}" "${PLAN}" "${TIER1_REGISTRY}" "${TIER1}" "${EVIDENCE}" <<'PY'
import json
import pathlib
import sys
deps = json.loads(pathlib.Path(sys.argv[1]).read_text())
plan = json.loads(pathlib.Path(sys.argv[2]).read_text())
registry = json.loads(pathlib.Path(sys.argv[3]).read_text())
tier1 = json.loads(pathlib.Path(sys.argv[4]).read_text())
out = pathlib.Path(sys.argv[5])
batch = deps["provider_audit"]["nodes"]
audit_status = deps["provider_audit"].get("status")
if audit_status == "pending-ci":
    if batch != plan["next_provider_audit_batch"]:
        raise SystemExit("pending provider-audit batch differs from generated campaign plan")
elif audit_status == "PASS":
    if not set(batch) <= set(plan.get("package_contract_ready", [])):
        raise SystemExit("PASS provider-audit batch is not fully package-contract-ready")
else:
    raise SystemExit(f"unsupported provider-audit status: {audit_status}")
tier1_nodes = {n["id"]: n for n in tier1["nodes"]}
qt_map = registry["qt_provider_packages"]
ext = dict(registry["requirements"])
ext.update(deps["provider_registry"]["additions"])
mandatory = {"cmake", "g++", "ninja-build", "pkgconf", "python3", "python3-setuptools"}
optional = set()
per_node = {}
for node_id in batch:
    node = deps["nodes"][node_id]
    frameworks = node.get("frameworks", {})
    predecessors = list(frameworks.get("required", [])) + list(frameworks.get("provider_selected", []))
    for predecessor in predecessors:
        t1 = tier1_nodes.get(predecessor)
        if not t1 or t1.get("state") != "PASS" or not t1.get("packaging", {}).get("downstream_eligible"):
            raise SystemExit(f"{node_id}: predecessor is not retained downstream-eligible PASS: {predecessor}")
    qt = node.get("qt", {})
    for category in ("required", "provider_selected", "default_enabled", "test"):
        for component in qt.get(category, []):
            mandatory.update(qt_map[component])
    for component in qt.get("optional", []):
        optional.update(qt_map[component])
    external = node.get("external", {})
    for category in ("required", "provider_selected", "default_enabled", "test"):
        for key in external.get(category, []):
            mandatory.update(ext[key]["packages"])
    for key in external.get("optional", []):
        optional.update(ext[key]["packages"])
    per_node[node_id] = {
        "qt": qt,
        "external": external,
        "selected_linux_profile": node.get("selected_linux_profile", {}),
        "tier1_predecessors": predecessors,
    }
optional -= mandatory
(out / "mandatory-packages.txt").write_text("".join(f"{p}\n" for p in sorted(mandatory)))
(out / "optional-packages.txt").write_text("".join(f"{p}\n" for p in sorted(optional)))
(out / "selected-profiles.json").write_text(json.dumps(per_node, indent=2) + "\n")
PY

sudo apt-get update

candidate_for() {
    local package_name="$1" policy
    policy="$(apt-cache policy "${package_name}")"
    awk '/Candidate:/ {print $2}' <<<"${policy}"
}

: > "${EVIDENCE}/apt-candidates.tsv"
declare -a mandatory_packages=()
while IFS= read -r package_name; do
    [[ -n "${package_name}" ]] || continue
    candidate="$(candidate_for "${package_name}")"
    printf 'mandatory\t%s\t%s\n' "${package_name}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
    if [[ -z "${candidate}" || "${candidate}" == "(none)" ]]; then
        echo "Mandatory provider package has no Resolute candidate: ${package_name}" >&2
        exit 1
    fi
    mandatory_packages+=("${package_name}")
done < "${EVIDENCE}/mandatory-packages.txt"

while IFS= read -r package_name; do
    [[ -n "${package_name}" ]] || continue
    candidate="$(candidate_for "${package_name}")"
    printf 'optional\t%s\t%s\n' "${package_name}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
done < "${EVIDENCE}/optional-packages.txt"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${mandatory_packages[@]}"

{
    printf 'package\tinstalled-version\n'
    for package_name in "${mandatory_packages[@]}"; do
        printf '%s\t%s\n' "${package_name}" "$(dpkg-query -W -f='${Version}' "${package_name}")"
    done
} > "${EVIDENCE}/installed-versions.tsv"

required_qt_series="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["qt"]["required_series"])' "${DESKTOP}")"
qt_version="$(dpkg-query -W -f='${Version}' qt6-base-dev | sed -E 's/^[0-9]+://' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
case "${qt_version}" in
    "${required_qt_series}".*) ;;
    *) echo "Ubuntu Qt provider ${qt_version} does not match selected series ${required_qt_series}" >&2; exit 1 ;;
esac

for package_name in libshiboken6-dev libpyside6-dev; do
    version="$(dpkg-query -W -f='${Version}' "${package_name}" | sed -E 's/^[0-9]+://' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
    if [[ "${version}" != "${qt_version}" ]]; then
        echo "Qt/PySide provider skew: ${package_name}=${version}, qt6-base-dev=${qt_version}" >&2
        exit 1
    fi
done

pkg-config --exists libcanberra
printf 'libcanberra\t%s\n' "$(pkg-config --modversion libcanberra)" > "${EVIDENCE}/pkg-config-versions.tsv"

python3 - <<'PY' > "${EVIDENCE}/python-binding-providers.txt"
import build
import importlib.metadata
import setuptools.build_meta
print("build_import=PASS")
print("build_version=" + getattr(build, "__version__", "unknown"))
print("setuptools_backend=PASS")
print("setuptools_version=" + importlib.metadata.version("setuptools"))
PY

probe="$(mktemp -d)"
trap 'rm -rf "${probe}"' EXIT
cat > "${probe}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier2ProviderAudit LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Core Gui Test Widgets DBus Network Xml)
find_package(X11 REQUIRED)
find_package(Python3 3.9 REQUIRED COMPONENTS Interpreter Development)
find_package(Shiboken6 REQUIRED CONFIG)
find_package(PySide6 REQUIRED CONFIG)
CMAKE
cmake -S "${probe}" -B "${probe}/build" -GNinja 2>&1 | tee "${EVIDENCE}/cmake-provider-probe.log"

python3 - "${DEPS}" "${PLAN}" "${EVIDENCE}" "${VERSION_ID}" "${qt_version}" <<'PY'
import json
import pathlib
import sys
deps = json.loads(pathlib.Path(sys.argv[1]).read_text())
plan = json.loads(pathlib.Path(sys.argv[2]).read_text())
out = pathlib.Path(sys.argv[3])
result = {
    "schema": 1,
    "result": "PASS",
    "claim": "provider-availability-and-selected-profile-only",
    "authoritative_package_build": False,
    "ubuntu_version": sys.argv[4],
    "qt_upstream": sys.argv[5],
    "batch": deps["provider_audit"]["batch"],
    "nodes": deps["provider_audit"]["nodes"],
    "campaign_snapshot": plan["canonical_snapshot"],
    "package_state_effect": "none",
}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
PY

{
    echo "result=PASS"
    echo "claim=provider-availability-and-selected-profile-only"
    echo "package_state_effect=none"
    echo "qt_upstream=${qt_version}"
    echo "batch=tier2-provider-audit-1"
} > "${EVIDENCE}/summary.env"

echo "KDE Tier 2 provider audit: PASS"
echo "package-state-effect=none"
