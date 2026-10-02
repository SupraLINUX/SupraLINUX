#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

plasma = json.loads((ROOT / "manifests/kde-plasma.json").read_text())
deps = json.loads((ROOT / "manifests/kde-plasma-dependencies.json").read_text())
desktop = json.loads((ROOT / "manifests/desktop-stack.json").read_text())
cert = json.loads((ROOT / "manifests/authoritative-kvm-certification.json").read_text())

release = plasma.get("release", {})
req(release.get("version") == "6.7.5", "Plasma canonical stable version")
req(release.get("status") == "stable", "Plasma release must be stable")
req(release.get("selection_policy") == "latest-official-stable-compatible", "Plasma selection policy")
req(release.get("rejected_noncanonical_release") == "6.8 beta", "Plasma 6.8 beta must remain noncanonical")
req(release.get("source_count") == 75, "Plasma 6.7.5 upstream source count")
req(release.get("signing_fingerprint") == "0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D", "Plasma release signing fingerprint")

requirements = plasma.get("requirements", {})
req(requirements.get("qt_minimum") == "6.10", "Plasma 6.7 Qt requirement")
req(requirements.get("frameworks_minimum") == "6.26", "Plasma 6.7 Frameworks requirement")
req(requirements.get("supralinux_qt_candidate") == "6.10.2+dfsg-7", "SupraLINUX Qt candidate")
req(requirements.get("supralinux_frameworks") == "6.30.0", "SupraLINUX Frameworks provider")

sources = plasma.get("sources", [])
ids = [node.get("id") for node in sources]
req(len(sources) == 75 and len(set(ids)) == 75, "Plasma source inventory must contain 75 unique nodes")
for node in sources:
    node_id = node.get("id", "")
    sha = node.get("source_sha256", "")
    req(node.get("version") == "6.7.5", f"{node_id}: source version")
    req(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"{node_id}: source SHA-256")
    req(node.get("source_url") == f"https://download.kde.org/stable/plasma/6.7.5/{node_id}-6.7.5.tar.xz", f"{node_id}: source URL")

for critical in ("kwin", "kwin-x11", "plasma-workspace", "plasma-desktop", "libplasma", "kscreenlocker", "kwayland-integration"):
    req(critical in ids, f"Plasma critical source present: {critical}")

planning = plasma.get("planning", {})
req(planning.get("phase") == "dag-candidate-review", "Plasma planning phase")
req(planning.get("status") == "dag-candidate-review-pending", "Plasma DAG candidate review live status")
req(planning.get("execution_authorized") is False, "DAG review must not authorize execution")
req(planning.get("package_execution_authorized") is False, "DAG review must not authorize package execution")
req(planning.get("consumes_package_attempt") is False, "DAG review must not consume package Attempt")
req(planning.get("canonical_package_state_effect") == "none", "Plasma DAG review canonical package state effect")
req(planning.get("runner_scope") == "github-hosted-ubuntu-26.04-non-authoritative-preflight", "Plasma DAG review runner scope")
req(planning.get("next_gate") == "plasma-dag-candidate-review", "Plasma DAG review next gate")

req(deps.get("state") == "discovery-evidence-promoted", "Plasma dependency discovery evidence promotion")
req(deps.get("discovery", {}).get("result") == "PASS", "Plasma dependency discovery PASS")
req(deps.get("discovery", {}).get("parser_revision") == 4, "Plasma dependency parser revision")
req(deps.get("discovery", {}).get("canonical_dag_effect") == "candidate-only-pending-review", "Plasma dependency candidate evidence boundary")
req(set(deps.get("nodes", {})) == set(ids), "Plasma dependency manifest node set")

stack = desktop.get("desktop", {})
req(stack.get("plasma", {}).get("version") == "6.7.5", "desktop-stack Plasma version")
req(stack.get("frameworks", {}).get("version") == "6.30.0", "desktop-stack Frameworks version")
qt = desktop.get("qt", {})
req(qt.get("required_series") == "6.10", "desktop-stack Qt requirement")
req(qt.get("provider", {}).get("candidate_version") == "6.10.2+dfsg-7", "desktop-stack Qt provider candidate")
runner = desktop.get("ci", {}).get("authoritative_runner", {})
req(runner.get("status") == "certified", "authoritative runner certification precondition")
req(runner.get("desktop_release_relevant_authorized") is True, "release-relevant desktop must be unlocked")

req(cert.get("next_gate") == "certification-complete", "authoritative KVM certification complete")
release_state = cert.get("release_relevant_desktop", {})
req(release_state.get("status") == "unlocked", "release-relevant desktop certification state")
req(release_state.get("plasma_authorized") is True and release_state.get("kwin_authorized") is True and release_state.get("session_authorized") is True, "Plasma/KWin/session authorizations")
req(cert.get("stable_publication_authorized") is False, "Plasma planning must not authorize stable publication")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Plasma 6.7.5 planning validation: PASS")
print(f"Sources: {len(sources)} official upstream tarballs")
print("Next gate: plasma-dependency-discovery-evidence")
