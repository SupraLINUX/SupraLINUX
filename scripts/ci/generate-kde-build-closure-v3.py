#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/ksq-0"
APT = OUT / "apt"
TESTS = ROOT / "tests/kde-stack"
PLASMA_VERSION = "6.7.4"
FRAMEWORKS_VERSION = "6.29.0"
ACTIVE_BUILD_PROFILES: set[str] = set()


def die(message: str) -> None:
    print(f"AURORA_KSQ_0_CLOSURE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode:
        die(f"{' '.join(args)}\n{proc.stderr.strip()}")
    return proc


def apt_opts(profile: str) -> list[str]:
    return [
        "-o", f"Dir::Etc::sourcelist={APT / (profile + '.sources')}",
        "-o", "Dir::Etc::sourceparts=-",
        "-o", f"Dir::State::lists={APT / (profile + '-lists')}",
        "-o", f"Dir::State::status={APT / 'empty-status'}",
        "-o", f"Dir::Cache={APT / (profile + '-cache')}",
        "-o", "APT::Architecture=amd64",
        "-o", "APT::Architectures=amd64",
        "-o", "Acquire::Languages=none",
    ]


def apt_cache(profile: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["apt-cache", *apt_opts(profile), *args], check=check)


def paragraphs(text: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    current: dict[str, str] = {}
    key: str | None = None
    for line in text.splitlines() + [""]:
        if not line.strip():
            if current:
                result.append(current)
            current = {}
            key = None
        elif line[0].isspace() and key:
            current[key] += "\n" + line.strip()
        elif ":" in line:
            key, value = line.split(":", 1)
            current[key] = value.strip()
    return result


def read_tsv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != fields:
            die(f"bad header in {path}: {reader.fieldnames}")
        return list(reader)


def snapshot_id() -> str:
    for line in (TESTS / "apt-metadata-snapshot.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("AURORA_KSQ_0_APT_SNAPSHOT="):
            value = line.split("=", 1)[1].strip()
            if re.fullmatch(r"\d{8}T\d{6}Z", value):
                return value
    die("invalid apt-metadata-snapshot.env")
    raise AssertionError


def manifest_modules(path: Path, version: str) -> set[str]:
    rows = read_tsv(path, ["module", "version", "url", "sha256"])
    for row in rows:
        if row["version"] != version:
            die(f"mixed version in {path}: {row}")
    return {row["module"] for row in rows}


PLASMA_MODULES = manifest_modules(TESTS / "plasma-6.7.4-sources.tsv", PLASMA_VERSION)
FRAMEWORKS_MODULES = manifest_modules(TESTS / "frameworks-6.29.0-sources.tsv", FRAMEWORKS_VERSION)


def split_relation(value: str, separator: str) -> list[str]:
    result: list[str] = []
    start = 0
    paren = bracket = profile = 0
    for index, char in enumerate(value):
        if char == "(": paren += 1
        elif char == ")": paren = max(0, paren - 1)
        elif char == "[": bracket += 1
        elif char == "]": bracket = max(0, bracket - 1)
        elif char == "<" and not paren and not bracket: profile += 1
        elif char == ">" and not paren and not bracket and profile: profile -= 1
        elif char == separator and not paren and not bracket and not profile:
            part = value[start:index].strip()
            if part: result.append(part)
            start = index + 1
    part = value[start:].strip()
    if part: result.append(part)
    return result


RELATION_RE = re.compile(r"^\s*([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?\s*(?:\((<<|<=|=|>=|>>)\s*([^)]+)\))?\s*(.*)$")


def parse_alternative(raw: str) -> dict[str, str | None]:
    match = RELATION_RE.match(raw)
    if not match:
        die(f"cannot parse dependency: {raw}")
    return {"raw": raw, "pkg": match.group(1), "qual": match.group(2), "op": match.group(3), "ver": match.group(4).strip() if match.group(4) else None, "rest": match.group(5).strip()}


def architecture_applies(rest: str) -> bool:
    match = re.search(r"\[([^\]]+)\]", rest)
    if not match: return True
    terms = match.group(1).split()
    positive = [term for term in terms if not term.startswith("!")]
    negative = [term[1:] for term in terms if term.startswith("!")]
    def matches(term: str) -> bool:
        return subprocess.run(["dpkg-architecture", "-aamd64", f"-i{term}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    return (not positive or any(matches(term) for term in positive)) and not any(matches(term) for term in negative)


def profiles_apply(rest: str) -> bool:
    groups = re.findall(r"<([^>]+)>", rest)
    if not groups: return True
    for group in groups:
        ok = True
        for term in group.split():
            negated = term.startswith("!")
            name = term[1:] if negated else term
            enabled = name in ACTIVE_BUILD_PROFILES
            ok = ok and ((not enabled) if negated else enabled)
        if ok: return True
    return False


def version_compare(left: str, operator: str, right: str) -> bool:
    return subprocess.run(["dpkg", "--compare-versions", left, operator, right]).returncode == 0


def version_satisfies(version: str, operator: str | None, required: str | None) -> bool:
    return True if not operator else bool(required and version_compare(version, operator, required))


SOURCE_CACHE: dict[tuple[str, str], list[dict[str, str]]] = {}
POLICY_CACHE: dict[str, str | None] = {}


def source_records(profile: str, name: str) -> list[dict[str, str]]:
    key = (profile, name)
    if key not in SOURCE_CACHE:
        query = apt_cache(profile, "showsrc", name, check=False)
        if query.returncode not in (0, 100): die(f"showsrc {profile}/{name}: {query.stderr.strip()}")
        SOURCE_CACHE[key] = paragraphs(query.stdout)
    return SOURCE_CACHE[key]


def binary_names(record: dict[str, str]) -> set[str]:
    return {item.strip() for item in record.get("Binary", "").split(",") if item.strip()}


def owns_binary(record: dict[str, str], binary: str) -> bool:
    return record.get("Package") == binary or binary in binary_names(record)


def newest(records: list[dict[str, str]]) -> dict[str, str] | None:
    if not records: return None
    best = records[0]
    for record in records[1:]:
        if version_compare(record["Version"], ">>", best["Version"]): best = record
    return best


def source_owner(profile: str, binary: str) -> tuple[dict[str, str] | None, list[str]]:
    records = [record for record in source_records(profile, binary) if owns_binary(record, binary)]
    names = {record.get("Package", "") for record in records}
    return (newest(records), sorted(names)) if len(names) == 1 else (None, sorted(names))


def candidate(binary: str) -> str | None:
    if binary not in POLICY_CACHE:
        query = apt_cache("resolute", "policy", binary, check=False)
        value: str | None = None
        for line in query.stdout.splitlines():
            if line.strip().startswith("Candidate:"):
                raw = line.split(":", 1)[1].strip()
                value = None if raw == "(none)" else raw
                break
        POLICY_CACHE[binary] = value
    return POLICY_CACHE[binary]


def parse_source_field(record: dict[str, str]) -> tuple[str, str]:
    raw = record.get("Source", "").strip()
    if not raw: return record["Package"], record["Version"]
    match = re.match(r"^(\S+)(?:\s+\(([^)]+)\))?$", raw)
    if not match: die(f"cannot parse binary Source field: {raw}")
    return match.group(1), match.group(2) or record["Version"]


def load_binary_universe() -> tuple[dict[str, list[dict[str, str]]], dict[str, list[tuple[str, str, str | None]]]]:
    binaries: dict[str, list[dict[str, str]]] = defaultdict(list)
    providers: dict[str, list[tuple[str, str, str | None]]] = defaultdict(list)
    for record in paragraphs(apt_cache("resolute", "dumpavail").stdout):
        package, version = record.get("Package"), record.get("Version")
        if not package or not version: continue
        binaries[package].append(record)
        for provided_raw in split_relation(record.get("Provides", ""), ","):
            provided = parse_alternative(provided_raw)
            if provided["op"] not in (None, "="): die(f"unexpected Provides relation: {provided_raw}")
            providers[str(provided["pkg"])].append((package, version, str(provided["ver"]) if provided["ver"] else None))
    return binaries, providers


BINARY_RECORDS, VIRTUAL_PROVIDERS = load_binary_universe()


def candidate_record(binary: str) -> dict[str, str] | None:
    version = candidate(binary)
    if not version: return None
    matches = [record for record in BINARY_RECORDS.get(binary, []) if record.get("Version") == version]
    return matches[0] if matches else None


def resolute_source_for_binary(binary: str) -> tuple[str, str] | None:
    record = candidate_record(binary)
    return parse_source_field(record) if record else None


def direct_satisfied(alternative: dict[str, str | None]) -> tuple[bool, str, str]:
    package = str(alternative["pkg"])
    record = candidate_record(package)
    version = candidate(package)
    if record and version:
        if alternative["qual"] != "any" or record.get("Multi-Arch") == "allowed":
            if version_satisfies(version, alternative["op"], alternative["ver"]): return True, package, f"{package}={version}"
    for provider, provider_version, provided_version in VIRTUAL_PROVIDERS.get(package, []):
        selected = candidate(provider)
        if selected != provider_version: continue
        if alternative["op"] and (not provided_version or not version_satisfies(provided_version, alternative["op"], alternative["ver"])): continue
        detail = f"{provider}={selected} provides {package}" + (f"={provided_version}" if provided_version else "")
        return True, provider, detail
    return False, "-", "not-satisfied"


def relation_satisfied(group: str) -> tuple[bool, str, str]:
    applicable = [alt for alt in (parse_alternative(part) for part in split_relation(group, "|")) if architecture_applies(str(alt["rest"])) and profiles_apply(str(alt["rest"]))]
    if not applicable: return True, "-", "not-applicable-amd64-default-profiles"
    for alternative in applicable:
        ok, binary, detail = direct_satisfied(alternative)
        if ok: return True, binary, detail
    return False, "-", "not-satisfied"


def module_name(source: str) -> str:
    return source[4:] if source.startswith("kf6-") else source


def upstream_version_matches(packaging_version: str, upstream_version: str) -> bool:
    return bool(re.match(rf"^{re.escape(upstream_version)}(?:$|[-+~])", packaging_version.split(":", 1)[-1]))


def classify_source(source: str, version: str) -> tuple[str, str, str]:
    module = module_name(source)
    if module in PLASMA_MODULES: return "plasma-6.7.4", module, "rebuild" if upstream_version_matches(version, PLASMA_VERSION) else "packaging-version-mismatch"
    if module in FRAMEWORKS_MODULES: return "frameworks-6.29.0", module, "rebuild" if upstream_version_matches(version, FRAMEWORKS_VERSION) else "packaging-version-mismatch"
    return "external", "-", "needs-decision"


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-unresolved", action="store_true")
    args = parser.parse_args()
    snapshot = snapshot_id()
    selections_rows = read_tsv(TESTS / "ksq-0-source-selections.tsv", ["binary_package", "source_package", "source_version", "origin", "candidate_family", "decision", "build_depends", "reason"])
    overrides_rows = read_tsv(TESTS / "ksq-0-build-dep-overrides.tsv", ["source_package", "source_version", "field", "from_relation", "to_relation", "reason"])
    selections = {row["binary_package"]: row for row in selections_rows}
    overrides = {(row["source_package"], row["source_version"], row["field"], row["from_relation"]): row for row in overrides_rows}
    if len(selections) != len(selections_rows) or len(overrides) != len(overrides_rows): die("duplicate source selection or build-dependency override")
    if any(row["decision"] != "backport" for row in selections_rows): die("KSQ-0 source selections currently accept only explicit backport decisions")

    for required in ("resolute.sources", "stonking.sources", "resolute-lists", "stonking-lists", "empty-status"):
        if not (APT / required).exists(): die(f"missing prepared APT metadata: {required}")

    roots = read_tsv(TESTS / "aurora-package-roots.tsv", ["binary_package", "relation", "candidate_family", "upstream_module", "ksq_action"])
    selected: dict[str, tuple[str, str, str, str]] = {}
    records: dict[str, dict[str, str]] = {}
    origins: dict[str, str] = {}
    required_by: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque()
    root_rows: list[list[str]] = []
    edges: list[list[str]] = []
    ubuntu_rows: list[list[str]] = []
    unresolved_rows: list[list[str]] = []
    decision_rows: list[list[str]] = []
    applied_selection_rows: list[list[str]] = []
    applied_override_rows: list[list[str]] = []
    graph: dict[str, set[str]] = defaultdict(set)
    used_selections: set[str] = set()
    used_overrides: set[tuple[str, str, str, str]] = set()

    def unresolved(source: str, version: str, field: str, relation: str, reason: str, candidate_name: str = "-", candidate_version: str = "-") -> None:
        unresolved_rows.append([source, version, field, relation, reason, candidate_name, candidate_version])

    def select(record: dict[str, str], family: str, module: str, decision: str, reason: str, origin: str) -> bool:
        source, version = record["Package"], record["Version"]
        value = (version, family, module, decision)
        if source in selected and selected[source] != value:
            unresolved(source, selected[source][0], "-", "-", "source-selection-conflict", source, f"{selected[source][0]}|{version}")
            return False
        if source not in selected:
            selected[source], records[source], origins[source] = value, record, origin
            queue.append(source)
        elif origins[source] != origin:
            unresolved(source, version, "-", "-", "source-origin-conflict", origins[source], origin)
            return False
        required_by[source].add(reason)
        return True

    def exact_selected_record(binary: str, alternative: dict[str, str | None]) -> tuple[dict[str, str] | None, dict[str, str] | None, str]:
        row = selections.get(binary)
        if not row: return None, None, "no-selection"
        if not version_satisfies(row["source_version"], alternative["op"], alternative["ver"]): return None, row, "selection-version-does-not-satisfy"
        if row["origin"] == "ubuntu-stonking-snapshot":
            matches = [record for record in source_records("stonking", binary) if record.get("Package") == row["source_package"] and record.get("Version") == row["source_version"] and owns_binary(record, binary)]
            if len(matches) != 1: return None, row, "selected-stonking-source-not-unique"
            return matches[0], row, "selected"
        if row["origin"] == "debian-source":
            if row["build_depends"] in ("", "-"): return None, row, "selected-debian-source-missing-build-depends"
            return {"Package": row["source_package"], "Version": row["source_version"], "Binary": binary, "Build-Depends": row["build_depends"]}, row, "selected"
        return None, row, "unknown-selection-origin"

    def build_dependencies(record: dict[str, str]) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        source, version = record["Package"], record["Version"]
        for field in ("Build-Depends", "Build-Depends-Arch", "Build-Depends-Indep"):
            for raw_group in split_relation(record.get(field, "").replace("\n", " "), ","):
                group = raw_group
                key = (source, version, field, raw_group)
                if key in overrides:
                    row = overrides[key]
                    group = row["to_relation"]
                    used_overrides.add(key)
                    applied_override_rows.append([source, version, field, raw_group, group, row["reason"]])
                if group: result.append((field, group))
        return result

    for root in roots:
        binary, action, family = root["binary_package"], root["ksq_action"], root["candidate_family"]
        if action == "rebuild":
            record, names = source_owner("stonking", binary)
            if not record:
                unresolved("ROOT", "-", "-", binary, "source-owner-missing-or-ambiguous", ",".join(names) or "-")
                root_rows.append([binary, action, family, "-", "-", f"stonking@{snapshot}", "UNRESOLVED"])
                continue
            detected_family, module, decision = classify_source(record["Package"], record["Version"])
            if detected_family != family or module != root["upstream_module"] or decision != "rebuild":
                unresolved("ROOT", "-", "-", binary, "root-packaging-mismatch", record["Package"], record["Version"])
                root_rows.append([binary, action, family, record["Package"], record["Version"], f"stonking@{snapshot}", "UNRESOLVED"])
                continue
            select(record, detected_family, module, "rebuild", f"root:{binary}", f"ubuntu-stonking@{snapshot}")
            root_rows.append([binary, action, family, record["Package"], record["Version"], f"stonking@{snapshot}", "rebuild"])
        elif action in ("keep-ubuntu", "compat-test"):
            version = candidate(binary)
            owner = resolute_source_for_binary(binary)
            if not version or not owner:
                unresolved("ROOT", "-", "-", binary, "missing-resolute-root")
                root_rows.append([binary, action, family, "-", "-", f"resolute@{snapshot}", "UNRESOLVED"])
            else:
                root_rows.append([binary, action, family, owner[0], owner[1], f"resolute@{snapshot}", f"{binary}={version}"])
        elif action == "defer-gear": root_rows.append([binary, action, family, "-", "-", "deferred", "gear-review"])
        elif action == "retain": root_rows.append([binary, action, family, "supralinux-settings", "-", "repository", "retain"])
        else: unresolved("ROOT", "-", "-", binary, f"unknown-root-action:{action}")

    processed: set[str] = set()
    while queue:
        source = queue.popleft()
        if source in processed: continue
        processed.add(source)
        source_version = selected[source][0]
        for field, relation in build_dependencies(records[source]):
            satisfied, chosen_binary, detail = relation_satisfied(relation)
            if satisfied:
                owner_source = owner_version = "-"
                if chosen_binary != "-":
                    owner = resolute_source_for_binary(chosen_binary)
                    if owner: owner_source, owner_version = owner
                    else: unresolved(source, source_version, field, relation, "resolute-provider-owner-missing", chosen_binary)
                edges.append([source, source_version, field, relation, chosen_binary, owner_source, owner_version, "ubuntu-satisfied", detail])
                ubuntu_rows.append([source, field, relation, chosen_binary, owner_source, owner_version, detail])
                continue

            applicable = [alt for alt in (parse_alternative(part) for part in split_relation(relation, "|")) if architecture_applies(str(alt["rest"])) and profiles_apply(str(alt["rest"]))]
            if not applicable:
                edges.append([source, source_version, field, relation, "-", "-", "-", "ignored", "not-applicable"])
                continue

            explicit_matches: list[tuple[dict[str, str | None], dict[str, str], dict[str, str]]] = []
            explicit_errors: list[str] = []
            for alternative in applicable:
                binary = str(alternative["pkg"])
                if binary not in selections: continue
                record, row, result = exact_selected_record(binary, alternative)
                if record and row: explicit_matches.append((alternative, record, row))
                else: explicit_errors.append(f"{binary}:{result}")
            if explicit_matches or explicit_errors:
                if len(explicit_matches) != 1 or explicit_errors:
                    unresolved(source, source_version, field, relation, "explicit-source-selection-failed", ",".join(explicit_errors) or "multiple-explicit-matches")
                    edges.append([source, source_version, field, relation, "-", "-", "-", "unresolved", ",".join(explicit_errors)])
                    continue
                chosen, dependency_record, row = explicit_matches[0]
                dependency_source, dependency_version = dependency_record["Package"], dependency_record["Version"]
                if select(dependency_record, row["candidate_family"], "-", row["decision"], f"{source}:{field}:{relation}", row["origin"]):
                    graph[source].add(dependency_source)
                used_selections.add(row["binary_package"])
                applied_selection_rows.append([row["binary_package"], dependency_source, dependency_version, row["origin"], row["candidate_family"], row["decision"], row["reason"]])
                edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, row["candidate_family"], row["decision"]])
                continue

            mapped: dict[tuple[str, str], tuple[dict[str, str | None], dict[str, str]]] = {}
            for alternative in applicable:
                record, _ = source_owner("stonking", str(alternative["pkg"]))
                if record and version_satisfies(record["Version"], alternative["op"], alternative["ver"]): mapped[(record["Package"], record["Version"])] = (alternative, record)
            if not mapped:
                unresolved(source, source_version, field, relation, "no-stonking-source-candidate")
                edges.append([source, source_version, field, relation, "-", "-", "-", "unresolved", "no-source-candidate"])
                continue
            if len(mapped) > 1:
                candidate_text = ",".join(f"{name}={version}" for name, version in sorted(mapped))
                unresolved(source, source_version, field, relation, "alternative-needs-decision", candidate_text)
                edges.append([source, source_version, field, relation, "-", "-", "-", "unresolved", candidate_text])
                continue
            (dependency_source, dependency_version), (chosen, dependency_record) = next(iter(mapped.items()))
            family, module, decision = classify_source(dependency_source, dependency_version)
            if decision == "packaging-version-mismatch":
                unresolved(source, source_version, field, relation, "kde-packaging-base-version-mismatch", dependency_source, dependency_version)
                decision_rows.append([dependency_source, dependency_version, family, decision, source, field, relation])
                edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, "unresolved", decision])
                continue
            if decision == "needs-decision":
                unresolved(source, source_version, field, relation, "external-source-needs-explicit-selection", dependency_source, dependency_version)
                decision_rows.append([dependency_source, dependency_version, "external", "needs-explicit-selection", source, field, relation])
                edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, "unresolved", "needs-explicit-selection"])
                continue
            if select(dependency_record, family, module, decision, f"{source}:{field}:{relation}", f"ubuntu-stonking@{snapshot}"):
                graph[source].add(dependency_source)
            edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, family, decision])

    for row in selections_rows:
        if row["binary_package"] not in used_selections: unresolved("POLICY", "-", "-", row["binary_package"], "declared-source-selection-not-used", row["source_package"], row["source_version"])
    for row in overrides_rows:
        key = (row["source_package"], row["source_version"], row["field"], row["from_relation"])
        if key not in used_overrides: unresolved("POLICY", "-", row["field"], row["from_relation"], "declared-build-dep-override-not-used", row["source_package"], row["source_version"])

    nodes = set(selected)
    outgoing = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for depender, dependencies in graph.items():
        for dependency in dependencies:
            if dependency != depender and dependency in nodes and depender not in outgoing[dependency]:
                outgoing[dependency].add(depender)
                indegree[depender] += 1
    ready = deque(sorted(node for node in nodes if not indegree[node]))
    order: list[str] = []
    while ready:
        node = ready.popleft(); order.append(node)
        for next_node in sorted(outgoing[node]):
            indegree[next_node] -= 1
            if not indegree[next_node]: ready.append(next_node)
    cycles = sorted(nodes - set(order))
    if cycles: unresolved("DAG", "-", "-", "-", "dependency-cycle", ",".join(cycles))

    write_tsv(OUT / "root-source-owners.tsv", ["binary_root", "ksq_action", "candidate_family", "source_package", "source_version", "metadata_origin", "result"], sorted(root_rows))
    write_tsv(OUT / "source-closure.tsv", ["source_package", "packaging_version", "candidate_family", "upstream_module", "packaging_base", "decision", "required_by"], [[name, *selected[name][:3], origins[name], selected[name][3], " ; ".join(sorted(required_by[name]))] for name in sorted(selected)])
    write_tsv(OUT / "build-dependency-edges.tsv", ["from_source", "from_version", "field", "relation", "chosen_binary", "to_source", "to_version", "classification", "detail"], edges)
    write_tsv(OUT / "ubuntu-satisfied-build-deps.tsv", ["from_source", "field", "relation", "chosen_binary", "resolute_source", "resolute_source_version", "solver_detail"], ubuntu_rows)
    write_tsv(OUT / "source-decision-candidates.tsv", ["source_package", "source_version", "detected_family", "reason", "required_by_source", "field", "relation"], sorted(set(map(tuple, decision_rows))))
    write_tsv(OUT / "source-selections-applied.tsv", ["binary_package", "source_package", "source_version", "origin", "candidate_family", "decision", "reason"], sorted(set(map(tuple, applied_selection_rows))))
    write_tsv(OUT / "build-dep-overrides-applied.tsv", ["source_package", "source_version", "field", "from_relation", "to_relation", "reason"], sorted(set(map(tuple, applied_override_rows))))
    write_tsv(OUT / "unresolved.tsv", ["from_source", "from_version", "field", "relation", "reason", "candidate", "candidate_version"], unresolved_rows)
    write_tsv(OUT / "build-order.tsv", ["order", "source_package", "packaging_version", "candidate_family", "decision"], [[str(index), name, selected[name][0], selected[name][1], selected[name][3]] for index, name in enumerate(order, 1)] + [["UNRESOLVED", name, selected[name][0], selected[name][1], selected[name][3]] for name in cycles])
    with (OUT / "selected-source-records.txt").open("w", encoding="utf-8") as handle:
        for name in sorted(records):
            handle.write(f"### {name} {records[name].get('Version', '-')} origin={origins[name]}\n")
            for key in sorted(records[name]): handle.write(f"{key}: {records[name][key]}\n")
            handle.write("\n")
    counts: dict[str, int] = defaultdict(int)
    for value in selected.values(): counts[value[1]] += 1
    lines = [f"AURORA_KSQ_0_APT_SNAPSHOT={snapshot}", f"AURORA_KSQ_0_CLOSURE_STATUS={'COMPLETE' if not unresolved_rows else 'INCOMPLETE'}", f"AURORA_KSQ_0_CLOSURE_SOURCES={len(selected)}", f"AURORA_KSQ_0_CLOSURE_UNRESOLVED={len(unresolved_rows)}", f"AURORA_KSQ_0_CLOSURE_BUILD_ORDERED={len(order)}"]
    lines.extend(f"AURORA_KSQ_0_CLOSURE_{family.upper().replace('-', '_').replace('.', '_')}={counts[family]}" for family in sorted(counts))
    status = "\n".join(lines) + "\n"
    (OUT / "closure-status.env").write_text(status, encoding="utf-8")
    print(status, end="")
    return 0 if args.allow_unresolved or not unresolved_rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
