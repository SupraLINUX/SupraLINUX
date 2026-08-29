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


def snapshot_id() -> str:
    path = TESTS / "apt-metadata-snapshot.env"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("AURORA_KSQ_0_APT_SNAPSHOT="):
            value = line.split("=", 1)[1].strip()
            if re.fullmatch(r"\d{8}T\d{6}Z", value):
                return value
    die("invalid apt-metadata-snapshot.env")
    raise AssertionError


def manifest_modules(path: Path, expected_version: str) -> set[str]:
    modules: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row["version"] != expected_version:
                die(f"mixed version in {path}: {row}")
            modules.add(row["module"])
    return modules


PLASMA_MODULES = manifest_modules(TESTS / "plasma-6.7.4-sources.tsv", PLASMA_VERSION)
FRAMEWORKS_MODULES = manifest_modules(TESTS / "frameworks-6.29.0-sources.tsv", FRAMEWORKS_VERSION)


def load_overrides() -> dict[tuple[str, str], dict[str, str]]:
    path = TESTS / "ksq-0-source-overrides.tsv"
    result: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected = ["source_package", "source_version", "family", "decision", "reason"]
        if reader.fieldnames != expected:
            die(f"bad overrides header: {reader.fieldnames}")
        for row in reader:
            key = (row["source_package"], row["source_version"])
            if key in result or row["decision"] not in {"backport", "reject", "defer"} or not row["family"] or not row["reason"]:
                die(f"invalid override: {row}")
            result[key] = row
    return result


def split_relation(value: str, separator: str) -> list[str]:
    result: list[str] = []
    start = 0
    paren = bracket = profile = 0
    for index, char in enumerate(value):
        if char == "(":
            paren += 1
        elif char == ")":
            paren = max(0, paren - 1)
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket = max(0, bracket - 1)
        elif char == "<" and not paren and not bracket:
            profile += 1
        elif char == ">" and not paren and not bracket and profile:
            profile -= 1
        elif char == separator and not paren and not bracket and not profile:
            part = value[start:index].strip()
            if part:
                result.append(part)
            start = index + 1
    part = value[start:].strip()
    if part:
        result.append(part)
    return result


RELATION_RE = re.compile(
    r"^\s*([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?\s*"
    r"(?:\((<<|<=|=|>=|>>)\s*([^)]+)\))?\s*(.*)$"
)


def parse_alternative(raw: str) -> dict[str, str | None]:
    match = RELATION_RE.match(raw)
    if not match:
        die(f"cannot parse dependency: {raw}")
    return {
        "raw": raw,
        "pkg": match.group(1),
        "qual": match.group(2),
        "op": match.group(3),
        "ver": match.group(4).strip() if match.group(4) else None,
        "rest": match.group(5).strip(),
    }


def architecture_applies(rest: str) -> bool:
    match = re.search(r"\[([^\]]+)\]", rest)
    if not match:
        return True
    terms = match.group(1).split()
    positive = [term for term in terms if not term.startswith("!")]
    negative = [term[1:] for term in terms if term.startswith("!")]

    def matches(term: str) -> bool:
        return subprocess.run(
            ["dpkg-architecture", "-aamd64", f"-i{term}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0

    return (not positive or any(matches(term) for term in positive)) and not any(matches(term) for term in negative)


def profiles_apply(rest: str) -> bool:
    groups = re.findall(r"<([^>]+)>", rest)
    if not groups:
        return True
    # Debian Policy: terms inside one <> group are AND; multiple groups are OR.
    # KSQ-0 models a normal build, so no build profiles are enabled.
    for group in groups:
        group_ok = True
        for term in group.split():
            negated = term.startswith("!")
            name = term[1:] if negated else term
            enabled = name in ACTIVE_BUILD_PROFILES
            group_ok = group_ok and ((not enabled) if negated else enabled)
        if group_ok:
            return True
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
        if query.returncode not in (0, 100):
            die(f"showsrc {profile}/{name}: {query.stderr.strip()}")
        SOURCE_CACHE[key] = paragraphs(query.stdout)
    return SOURCE_CACHE[key]


def binary_names(source_record: dict[str, str]) -> set[str]:
    return {item.strip() for item in source_record.get("Binary", "").split(",") if item.strip()}


def source_owns_binary(source_record: dict[str, str], binary: str) -> bool:
    return source_record.get("Package") == binary or binary in binary_names(source_record)


def newest(records: list[dict[str, str]]) -> dict[str, str] | None:
    if not records:
        return None
    best = records[0]
    for record in records[1:]:
        if version_compare(record["Version"], ">>", best["Version"]):
            best = record
    return best


def source_owner(profile: str, binary: str) -> tuple[dict[str, str] | None, list[str]]:
    records = [record for record in source_records(profile, binary) if source_owns_binary(record, binary)]
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
    if not raw:
        return record["Package"], record["Version"]
    match = re.match(r"^(\S+)(?:\s+\(([^)]+)\))?$", raw)
    if not match:
        die(f"cannot parse binary Source field: {raw}")
    return match.group(1), match.group(2) or record["Version"]


def load_binary_universe() -> tuple[dict[str, list[dict[str, str]]], dict[str, list[tuple[str, str, str | None]]]]:
    query = apt_cache("resolute", "dumpavail")
    binaries: dict[str, list[dict[str, str]]] = defaultdict(list)
    providers: dict[str, list[tuple[str, str, str | None]]] = defaultdict(list)
    for record in paragraphs(query.stdout):
        package = record.get("Package")
        version = record.get("Version")
        if not package or not version:
            continue
        binaries[package].append(record)
        for provided_raw in split_relation(record.get("Provides", ""), ","):
            if not provided_raw:
                continue
            provided = parse_alternative(provided_raw)
            if provided["op"] not in (None, "="):
                die(f"unexpected Provides relation: {provided_raw}")
            providers[str(provided["pkg"])].append((package, version, str(provided["ver"]) if provided["ver"] else None))
    return binaries, providers


BINARY_RECORDS, VIRTUAL_PROVIDERS = load_binary_universe()


def candidate_record(binary: str) -> dict[str, str] | None:
    version = candidate(binary)
    if not version:
        return None
    matches = [record for record in BINARY_RECORDS.get(binary, []) if record.get("Version") == version]
    return matches[0] if matches else None


def resolute_source_for_binary(binary: str) -> tuple[str, str] | None:
    record = candidate_record(binary)
    if not record:
        return None
    return parse_source_field(record)


def direct_satisfied(alternative: dict[str, str | None]) -> tuple[bool, str, str]:
    package = str(alternative["pkg"])
    record = candidate_record(package)
    version = candidate(package)
    if record and version:
        qualifier = alternative["qual"]
        if qualifier == "any" and record.get("Multi-Arch") != "allowed":
            pass
        elif version_satisfies(version, alternative["op"], alternative["ver"]):
            return True, package, f"{package}={version}"

    for provider, provider_version, provided_version in VIRTUAL_PROVIDERS.get(package, []):
        selected = candidate(provider)
        if selected != provider_version:
            continue
        if alternative["op"] and (not provided_version or not version_satisfies(provided_version, alternative["op"], alternative["ver"])):
            continue
        detail = f"{provider}={selected} provides {package}"
        if provided_version:
            detail += f"={provided_version}"
        return True, provider, detail
    return False, "-", "not-satisfied"


def relation_satisfied(group: str) -> tuple[bool, str, str]:
    alternatives = [parse_alternative(part) for part in split_relation(group, "|")]
    applicable = [alt for alt in alternatives if architecture_applies(str(alt["rest"])) and profiles_apply(str(alt["rest"]))]
    if not applicable:
        return True, "-", "not-applicable-amd64-default-profiles"
    for alternative in applicable:
        ok, binary, detail = direct_satisfied(alternative)
        if ok:
            return True, binary, detail
    return False, "-", "not-satisfied"


def build_dependencies(source_record: dict[str, str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for field in ("Build-Depends", "Build-Depends-Arch", "Build-Depends-Indep"):
        for group in split_relation(source_record.get(field, "").replace("\n", " "), ","):
            if group:
                result.append((field, group))
    return result


def module_name(source: str) -> str:
    return source[4:] if source.startswith("kf6-") else source


def upstream_version_matches(packaging_version: str, upstream_version: str) -> bool:
    without_epoch = packaging_version.split(":", 1)[-1]
    return bool(re.match(rf"^{re.escape(upstream_version)}(?:$|[-+~])", without_epoch))


def classify_source(source: str, version: str) -> tuple[str, str, str]:
    module = module_name(source)
    if module in PLASMA_MODULES:
        decision = "rebuild" if upstream_version_matches(version, PLASMA_VERSION) else "packaging-version-mismatch"
        return "plasma-6.7.4", module, decision
    if module in FRAMEWORKS_MODULES:
        decision = "rebuild" if upstream_version_matches(version, FRAMEWORKS_VERSION) else "packaging-version-mismatch"
        return "frameworks-6.29.0", module, decision
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
    overrides = load_overrides()

    for required in ("resolute.sources", "stonking.sources", "resolute-lists", "stonking-lists", "empty-status"):
        if not (APT / required).exists():
            die(f"missing prepared APT metadata: {required}")

    with (TESTS / "aurora-package-roots.tsv").open(newline="", encoding="utf-8") as handle:
        roots = list(csv.DictReader(handle, delimiter="\t"))

    selected: dict[str, tuple[str, str, str, str]] = {}
    records: dict[str, dict[str, str]] = {}
    required_by: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque()
    root_rows: list[list[str]] = []
    edges: list[list[str]] = []
    ubuntu_rows: list[list[str]] = []
    unresolved_rows: list[list[str]] = []
    decision_rows: list[list[str]] = []
    graph: dict[str, set[str]] = defaultdict(set)

    def unresolved(source: str, version: str, field: str, relation: str, reason: str, candidate_name: str = "-", candidate_version: str = "-") -> None:
        unresolved_rows.append([source, version, field, relation, reason, candidate_name, candidate_version])

    def select(record: dict[str, str], family: str, module: str, decision: str, reason: str) -> bool:
        source = record["Package"]
        version = record["Version"]
        value = (version, family, module, decision)
        if source in selected and selected[source] != value:
            unresolved(source, selected[source][0], "-", "-", "source-selection-conflict", source, f"{selected[source][0]}|{version}")
            return False
        if source not in selected:
            selected[source] = value
            records[source] = record
            queue.append(source)
        required_by[source].add(reason)
        return True

    for root in roots:
        binary = root["binary_package"]
        action = root["ksq_action"]
        family = root["candidate_family"]
        if action == "rebuild":
            source_record, names = source_owner("stonking", binary)
            if not source_record:
                unresolved("ROOT", "-", "-", binary, "source-owner-missing-or-ambiguous", ",".join(names) or "-")
                root_rows.append([binary, action, family, "-", "-", f"stonking@{snapshot}", "UNRESOLVED"])
                continue
            detected_family, module, decision = classify_source(source_record["Package"], source_record["Version"])
            if detected_family != family or module != root["upstream_module"] or decision != "rebuild":
                unresolved("ROOT", "-", "-", binary, "root-packaging-mismatch", source_record["Package"], source_record["Version"])
                root_rows.append([binary, action, family, source_record["Package"], source_record["Version"], f"stonking@{snapshot}", "UNRESOLVED"])
                continue
            select(source_record, detected_family, module, "rebuild", f"root:{binary}")
            root_rows.append([binary, action, family, source_record["Package"], source_record["Version"], f"stonking@{snapshot}", "rebuild"])
        elif action in ("keep-ubuntu", "compat-test"):
            version = candidate(binary)
            owner = resolute_source_for_binary(binary)
            if not version or not owner:
                unresolved("ROOT", "-", "-", binary, "missing-resolute-root")
                root_rows.append([binary, action, family, "-", "-", f"resolute@{snapshot}", "UNRESOLVED"])
            else:
                root_rows.append([binary, action, family, owner[0], owner[1], f"resolute@{snapshot}", f"{binary}={version}"])
        elif action == "defer-gear":
            root_rows.append([binary, action, family, "-", "-", "deferred", "gear-review"])
        elif action == "retain":
            root_rows.append([binary, action, family, "supralinux-settings", "-", "repository", "retain"])
        else:
            unresolved("ROOT", "-", "-", binary, f"unknown-root-action:{action}")

    processed: set[str] = set()
    while queue:
        source = queue.popleft()
        if source in processed:
            continue
        processed.add(source)
        source_version = selected[source][0]

        for field, relation in build_dependencies(records[source]):
            satisfied, chosen_binary, detail = relation_satisfied(relation)
            if satisfied:
                owner_source = owner_version = "-"
                if chosen_binary != "-":
                    owner = resolute_source_for_binary(chosen_binary)
                    if owner:
                        owner_source, owner_version = owner
                    else:
                        unresolved(source, source_version, field, relation, "resolute-provider-owner-missing", chosen_binary)
                edges.append([source, source_version, field, relation, chosen_binary, owner_source, owner_version, "ubuntu-satisfied", detail])
                ubuntu_rows.append([source, field, relation, chosen_binary, owner_source, owner_version, detail])
                continue

            alternatives = [parse_alternative(part) for part in split_relation(relation, "|")]
            applicable = [alt for alt in alternatives if architecture_applies(str(alt["rest"])) and profiles_apply(str(alt["rest"]))]
            if not applicable:
                edges.append([source, source_version, field, relation, "-", "-", "-", "ignored", "not-applicable"])
                continue

            mapped: dict[tuple[str, str], tuple[dict[str, str | None], dict[str, str]]] = {}
            for alternative in applicable:
                source_record, _ = source_owner("stonking", str(alternative["pkg"]))
                if source_record and version_satisfies(source_record["Version"], alternative["op"], alternative["ver"]):
                    mapped[(source_record["Package"], source_record["Version"])] = (alternative, source_record)

            if not mapped:
                unresolved(source, source_version, field, relation, "no-stonking-source-candidate")
                edges.append([source, source_version, field, relation, "-", "-", "-", "unresolved", "no-source-candidate"])
                continue
            if len(mapped) > 1:
                candidates = ",".join(f"{name}={version}" for name, version in sorted(mapped))
                unresolved(source, source_version, field, relation, "alternative-needs-decision", candidates)
                edges.append([source, source_version, field, relation, "-", "-", "-", "unresolved", candidates])
                continue

            (dependency_source, dependency_version), (chosen, dependency_record) = next(iter(mapped.items()))
            family, module, decision = classify_source(dependency_source, dependency_version)
            if decision == "packaging-version-mismatch":
                unresolved(source, source_version, field, relation, "kde-packaging-base-version-mismatch", dependency_source, dependency_version)
                decision_rows.append([dependency_source, dependency_version, family, decision, source, field, relation])
                edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, "unresolved", decision])
                continue
            if decision == "needs-decision":
                override = overrides.get((dependency_source, dependency_version))
                if not override or override["decision"] != "backport":
                    reason = "external-source-needs-decision" if not override else f"external-source-{override['decision']}"
                    unresolved(source, source_version, field, relation, reason, dependency_source, dependency_version)
                    decision_rows.append([dependency_source, dependency_version, "external", reason, source, field, relation])
                    edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, "unresolved", reason])
                    continue
                family, module, decision = override["family"], "-", "backport"

            if select(dependency_record, family, module, decision, f"{source}:{field}:{relation}"):
                graph[source].add(dependency_source)
                edges.append([source, source_version, field, relation, str(chosen["pkg"]), dependency_source, dependency_version, family, decision])

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
        node = ready.popleft()
        order.append(node)
        for next_node in sorted(outgoing[node]):
            indegree[next_node] -= 1
            if not indegree[next_node]:
                ready.append(next_node)
    cycles = sorted(nodes - set(order))
    if cycles:
        unresolved("DAG", "-", "-", "-", "dependency-cycle", ",".join(cycles))

    write_tsv(OUT / "root-source-owners.tsv", ["binary_root", "ksq_action", "candidate_family", "source_package", "source_version", "metadata_origin", "result"], sorted(root_rows))
    write_tsv(OUT / "source-closure.tsv", ["source_package", "packaging_version", "candidate_family", "upstream_module", "packaging_base", "decision", "required_by"], [[name, *selected[name][:3], f"ubuntu-stonking@{snapshot}:{selected[name][0]}", selected[name][3], " ; ".join(sorted(required_by[name]))] for name in sorted(selected)])
    write_tsv(OUT / "build-dependency-edges.tsv", ["from_source", "from_version", "field", "relation", "chosen_binary", "to_source", "to_version", "classification", "detail"], edges)
    write_tsv(OUT / "ubuntu-satisfied-build-deps.tsv", ["from_source", "field", "relation", "chosen_binary", "resolute_source", "resolute_source_version", "solver_detail"], ubuntu_rows)
    write_tsv(OUT / "source-decision-candidates.tsv", ["source_package", "source_version", "detected_family", "reason", "required_by_source", "field", "relation"], sorted(set(map(tuple, decision_rows))))
    write_tsv(OUT / "unresolved.tsv", ["from_source", "from_version", "field", "relation", "reason", "candidate", "candidate_version"], unresolved_rows)
    write_tsv(OUT / "build-order.tsv", ["order", "source_package", "packaging_version", "candidate_family", "decision"], [[str(index), name, selected[name][0], selected[name][1], selected[name][3]] for index, name in enumerate(order, 1)] + [["UNRESOLVED", name, selected[name][0], selected[name][1], selected[name][3]] for name in cycles])

    with (OUT / "selected-source-records.txt").open("w", encoding="utf-8") as handle:
        for name in sorted(records):
            handle.write(f"### {name} {records[name].get('Version', '-')}\n")
            for key in sorted(records[name]):
                handle.write(f"{key}: {records[name][key]}\n")
            handle.write("\n")

    counts: dict[str, int] = defaultdict(int)
    for value in selected.values():
        counts[value[1]] += 1
    lines = [
        f"AURORA_KSQ_0_APT_SNAPSHOT={snapshot}",
        f"AURORA_KSQ_0_CLOSURE_STATUS={'COMPLETE' if not unresolved_rows else 'INCOMPLETE'}",
        f"AURORA_KSQ_0_CLOSURE_SOURCES={len(selected)}",
        f"AURORA_KSQ_0_CLOSURE_UNRESOLVED={len(unresolved_rows)}",
        f"AURORA_KSQ_0_CLOSURE_BUILD_ORDERED={len(order)}",
    ]
    lines.extend(f"AURORA_KSQ_0_CLOSURE_{family.upper().replace('-', '_').replace('.', '_')}={counts[family]}" for family in sorted(counts))
    status = "\n".join(lines) + "\n"
    (OUT / "closure-status.env").write_text(status, encoding="utf-8")
    print(status, end="")
    return 0 if args.allow_unresolved or not unresolved_rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
