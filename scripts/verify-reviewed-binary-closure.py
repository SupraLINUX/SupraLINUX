#!/usr/bin/env python3
"""Reject incomplete reviewed local binary closures before creating an authoritative VM."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
ALT_RE = re.compile(
    r"^\s*([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9-]+)?"
    r"(?:\s*\((<<|<=|=|>=|>>)\s*([^()]+?)\))?"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_stanzas(text: str):
    stanzas = []
    current = {}
    key = None
    for raw in text.splitlines():
        if not raw:
            if current:
                stanzas.append(current)
                current = {}
                key = None
            continue
        if raw[:1].isspace():
            if key is None:
                raise AssertionError("Malformed Packages continuation.")
            current[key] += "\n" + raw[1:]
            continue
        if ":" not in raw:
            raise AssertionError(f"Malformed Packages field: {raw!r}")
        key, value = raw.split(":", 1)
        current[key] = value.lstrip()
    if current:
        stanzas.append(current)
    return stanzas


def split_top(value: str, separator: str):
    result, start = [], 0
    round_depth = square_depth = angle_depth = 0
    for index, char in enumerate(value):
        if char == "(":
            round_depth += 1
        elif char == ")":
            round_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif char == "<":
            angle_depth += 1
        elif char == ">":
            angle_depth = max(0, angle_depth - 1)
        elif (
            char == separator
            and round_depth == 0
            and square_depth == 0
            and angle_depth == 0
        ):
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return [item for item in result if item]


def parse_relation(value: str):
    groups = []
    for group in split_top(value.replace("\n", " "), ","):
        alternatives = []
        for alt in split_top(group, "|"):
            match = ALT_RE.match(alt)
            if not match:
                raise AssertionError(f"Unsupported Debian dependency relation: {alt!r}")
            name, operator, version = match.groups()
            alternatives.append(
                {
                    "name": name,
                    "operator": operator,
                    "version": version.strip() if version else None,
                    "raw": alt,
                }
            )
        groups.append({"raw": group, "alternatives": alternatives})
    return groups


def version_satisfies(actual: str, operator, required) -> bool:
    if operator is None:
        return True
    completed = subprocess.run(
        ["dpkg", "--compare-versions", actual, operator, required],
        check=False,
    )
    return completed.returncode == 0


def source_name(stanza):
    source = stanza.get("Source", stanza["Package"]).split()[0]
    assert PACKAGE_RE.fullmatch(source), source
    return source


def support_providers(root: Path, support_manifest: dict):
    providers = {}
    for node, record in sorted(support_manifest.get("nodes", {}).items()):
        assert record.get("state") == "PASS" and record.get("downstream_eligible") is True
        evidence = record["evidence"]
        proof_path = root / evidence["path"]
        assert proof_path.is_file(), proof_path
        assert sha256(proof_path) == evidence["sha256"], f"Support proof drift: {node}"
        proof = json.loads(proof_path.read_text())
        assert proof["node"] == node and proof["state"] == "PASS"
        assert proof["offline_restore_verified"] is True
        for binary in proof["inspection"]["binaries"]:
            if not binary["file"].endswith(".deb"):
                continue
            package = binary["package"]
            previous = providers.setdefault(
                package,
                {
                    "node": node,
                    "source_package": proof["source_package"],
                    "version": binary["version"],
                    "architecture": binary["architecture"],
                },
            )
            assert previous["node"] == node, f"Ambiguous support provider: {package}"
    return providers


def repair_providers(root: Path, repairs_manifest: dict):
    providers = {}
    for node, record in sorted(repairs_manifest.get("nodes", {}).items()):
        if record.get("state") != "PASS":
            continue
        assert record.get("downstream_eligible") is True
        evidence = record["evidence"]
        proof_path = root / evidence["path"]
        assert proof_path.is_file(), proof_path
        assert sha256(proof_path) == evidence["sha256"], f"Repair proof drift: {node}"
        proof = json.loads(proof_path.read_text())
        assert proof["state"] == "PASS" and proof["node"] == node
        assert proof["offline_restore_verified"] is True
        for binary in record["binaries"]:
            package = binary["package"]
            previous = providers.setdefault(
                package,
                {
                    "node": node,
                    "source_package": record["source_package"],
                    "version": binary["version"],
                    "architecture": binary["architecture"],
                },
            )
            assert previous["node"] == node, f"Ambiguous repair provider: {package}"
    return providers


def selected_inputs(record):
    selected = {}
    for node, predecessor in record.get("frameworks_predecessors", {}).items():
        for binary in predecessor.get("binaries", []):
            package = binary["package"]
            assert package not in selected, f"Duplicate selected predecessor binary: {package}"
            selected[package] = {
                "node": node,
                "source_package": predecessor["source_package"],
                "version": predecessor["version"],
                "architecture": binary["architecture"],
            }
    return selected


def verify(
    root: Path,
    campaign: dict,
    node: str,
    packages_text: str,
    dag: dict,
    support: dict,
    repairs: dict,
):
    assert node in campaign["nodes"], f"Unknown package node: {node}"
    record = campaign["nodes"][node]
    selected = selected_inputs(record)
    stanzas = parse_stanzas(packages_text)
    by_identity = {}
    milestone_names = set()
    milestone_source = {}
    for stanza in stanzas:
        package = stanza.get("Package")
        version = stanza.get("Version")
        architecture = stanza.get("Architecture")
        if not package or not version or not architecture:
            raise AssertionError("Incomplete milestone Packages stanza.")
        key = (package, version, architecture)
        assert key not in by_identity, f"Duplicate milestone package identity: {key}"
        by_identity[key] = stanza
        milestone_names.add(package)
        milestone_source.setdefault(package, source_name(stanza))

    support_by_package = support_providers(root, support)
    repair_by_package = repair_providers(root, repairs)
    overlap = set(support_by_package) & set(repair_by_package)
    assert not overlap, f"Ambiguous retained/revalidated providers: {sorted(overlap)!r}"
    external_by_package = {**support_by_package, **repair_by_package}
    local_names = milestone_names | set(external_by_package)
    node_by_source = {}
    for dag_node, dag_record in dag.get("nodes", {}).items():
        source = dag_record.get("source_package")
        if source:
            node_by_source.setdefault(source, dag_node)

    missing_metadata = []
    selected_stanzas = []
    for package, item in sorted(selected.items()):
        if package in external_by_package:
            provider = external_by_package[package]
            assert provider["node"] == item["node"], (
                f"Selected external provider mismatch: {package}: "
                f"{provider['node']} != {item['node']}"
            )
            assert provider["source_package"] == item["source_package"]
            assert provider["version"] == item["version"]
            assert provider["architecture"] == item["architecture"]
            continue
        key = (package, item["version"], item["architecture"])
        stanza = by_identity.get(key)
        if stanza is None and item["architecture"] == "amd64":
            stanza = by_identity.get((package, item["version"], "all"))
        if stanza is None:
            missing_metadata.append(
                {
                    "package": package,
                    "version": item["version"],
                    "architecture": item["architecture"],
                    "provider_node": item["node"],
                }
            )
        else:
            selected_stanzas.append(stanza)

    missing_relations = []
    for stanza in selected_stanzas:
        for field in ("Pre-Depends", "Depends"):
            value = stanza.get(field)
            if not value:
                continue
            for group in parse_relation(value):
                satisfied = False
                local_alternatives = []
                external_alternative = False
                for alt in group["alternatives"]:
                    name = alt["name"]
                    if name not in local_names:
                        external_alternative = True
                        continue
                    local_alternatives.append(name)
                    chosen = selected.get(name)
                    if chosen and version_satisfies(
                        chosen["version"], alt["operator"], alt["version"]
                    ):
                        satisfied = True
                        break
                if satisfied or external_alternative or not local_alternatives:
                    continue
                providers = []
                for package in local_alternatives:
                    if package in external_by_package:
                        provider = external_by_package[package]
                        providers.append(
                            {
                                "package": package,
                                "provider_node": provider["node"],
                                "source_package": provider["source_package"],
                                "version": provider["version"],
                            }
                        )
                    else:
                        source = milestone_source[package]
                        providers.append(
                            {
                                "package": package,
                                "provider_node": node_by_source.get(source),
                                "source_package": source,
                            }
                        )
                missing_relations.append(
                    {
                        "consumer_package": stanza["Package"],
                        "field": field,
                        "relation": group["raw"],
                        "providers": providers,
                    }
                )

    state = "PASS" if not missing_metadata and not missing_relations else "BLOCKED"
    return {
        "schema": 1,
        "kind": "reviewed-binary-closure-fast-rejection",
        "state": state,
        "node": node,
        "package_attempt_consumed": False,
        "vm_created": False,
        "packages_index_sha256": hashlib.sha256(packages_text.encode()).hexdigest(),
        "selected_binary_count": len(selected),
        "selected_packages": sorted(selected),
        "external_selected_packages": sorted(
            package for package in selected if package in external_by_package
        ),
        "missing_selected_metadata": missing_metadata,
        "missing_local_relations": missing_relations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dag", type=Path, default=ROOT / "manifests/kde-dag.json")
    parser.add_argument(
        "--support",
        type=Path,
        default=ROOT / "manifests/frameworks-support-inputs.json",
    )
    parser.add_argument(
        "--repairs",
        type=Path,
        default=ROOT / "manifests/package-revalidation.json",
    )
    args = parser.parse_args()
    campaign_bytes = args.campaign.read_bytes()
    result = verify(
        ROOT,
        json.loads(campaign_bytes),
        args.node,
        args.packages.read_text(),
        json.loads(args.dag.read_text()),
        json.loads(args.support.read_text()),
        json.loads(args.repairs.read_text()),
    )
    result["source_commit"] = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    result["campaign_manifest"] = str(args.campaign.resolve().relative_to(ROOT.resolve()))
    result["campaign_manifest_sha256"] = hashlib.sha256(campaign_bytes).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result["state"] != "PASS":
        for missing in result["missing_selected_metadata"]:
            print(
                f"BLOCKED: selected reviewed input is absent from both the milestone "
                f"and retained/revalidated providers: {missing['package']} "
                f"{missing['version']} {missing['architecture']} "
                f"({missing['provider_node']})",
                file=__import__("sys").stderr,
            )
        for missing in result["missing_local_relations"]:
            providers = ", ".join(
                f"{item['package']} ({item.get('provider_node') or item['source_package']})"
                for item in missing["providers"]
            )
            print(
                f"BLOCKED: {missing['consumer_package']} {missing['field']} "
                f"{missing['relation']} requires missing reviewed local input: {providers}",
                file=__import__("sys").stderr,
            )
        raise SystemExit(3)
    print(
        "Reviewed binary closure fast rejection: PASS; "
        f"{result['selected_binary_count']} selected binaries"
    )


if __name__ == "__main__":
    main()
