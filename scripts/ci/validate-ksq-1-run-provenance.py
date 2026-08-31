#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NoReturn

EXPECTED_REPOSITORY = "SupraLINUX/SupraLINUX"
EXPECTED_BRANCH = "feature/kde-stack-qualification"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

FULL_ARTIFACTS = {
    "aurora-ksq-1-debs-001-020",
    "aurora-ksq-1-debs-021-040",
    "aurora-ksq-1-debs-041-060",
    "aurora-ksq-1-debs-061-080",
    "aurora-ksq-1-debs-081-101",
    "aurora-ksq-1-evidence-001-020",
    "aurora-ksq-1-evidence-021-040",
    "aurora-ksq-1-evidence-041-060",
    "aurora-ksq-1-evidence-061-080",
    "aurora-ksq-1-evidence-081-101",
    "aurora-ksq-1-kwallet-pam-validation",
    "aurora-ksq-1-full-build-validation",
}

REPRO_ARTIFACTS = {
    "aurora-ksq-1-repro-order-29",
    "aurora-ksq-1-repro-order-68",
    "aurora-ksq-1-repro-order-81",
    "aurora-ksq-1-repro-order-99",
    "aurora-ksq-1-repro-order-100",
    "aurora-ksq-1-repro-order-101",
    "aurora-ksq-1-reproducibility-validation",
}

RUN_SPECS: dict[str, dict[str, Any]] = {
    "candidate": {
        "selector": "AURORA_KSQ_1_CANDIDATE_RUN_ID",
        "name": "Aurora KSQ-1 full source builds",
        "path": ".github/workflows/ksq-1-full-builds.yml",
        "artifacts": FULL_ARTIFACTS,
    },
    "reference": {
        "selector": "AURORA_KSQ_1_REFERENCE_RUN_ID",
        "name": "Aurora KSQ-1 full source builds",
        "path": ".github/workflows/ksq-1-full-builds.yml",
        "artifacts": FULL_ARTIFACTS,
    },
    "reproducibility": {
        "selector": "AURORA_KSQ_1_REPRO_RUN_ID",
        "name": "Aurora KSQ-1 reproducibility qualification",
        "path": ".github/workflows/ksq-1-reproducibility.yml",
        "artifacts": REPRO_ARTIFACTS,
    },
    "ksq0_closure": {
        "selector": "AURORA_KSQ_1_KSQ0_CLOSURE_RUN_ID",
        "name": "Aurora KSQ-0 source and dependency qualification",
        "path": ".github/workflows/ksq-0-dependency-closure.yml",
        "artifacts": {"aurora-ksq-0-dependency-closure"},
    },
    "ksq0_inventory": {
        "selector": "AURORA_KSQ_1_KSQ0_INVENTORY_RUN_ID",
        "name": "Aurora KSQ-0 source inventory",
        "path": ".github/workflows/ksq-0-source-inventory.yml",
        "artifact_prefix": "aurora-ksq-0-source-inventory-",
    },
}


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_RUN_PROVENANCE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"selector file missing: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"selector contains malformed line: {raw!r}")
        key, value = line.split("=", 1)
        if key in values:
            fail(f"selector contains duplicate key: {key}")
        values[key] = value
    return values


def api_get(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SupraLINUX-KSQ-1-provenance-validator",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"GitHub API {url} returned HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed for {url}: {exc}")


def validate_run(run: dict[str, Any], label: str, spec: dict[str, Any], run_id: int) -> None:
    expected = {
        "id": run_id,
        "name": spec["name"],
        "path": spec["path"],
        "head_branch": EXPECTED_BRANCH,
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    for key, value in expected.items():
        if run.get(key) != value:
            fail(f"{label} run {run_id}: {key}={run.get(key)!r}, expected {value!r}")
    repository = run.get("repository") or {}
    head_repository = run.get("head_repository") or {}
    if repository.get("full_name") != EXPECTED_REPOSITORY:
        fail(f"{label} run {run_id}: unexpected repository {repository.get('full_name')!r}")
    if head_repository.get("full_name") != EXPECTED_REPOSITORY:
        fail(f"{label} run {run_id}: unexpected head repository {head_repository.get('full_name')!r}")
    head_sha = run.get("head_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        fail(f"{label} run {run_id}: invalid head SHA {head_sha!r}")
    attempt = run.get("run_attempt")
    if not isinstance(attempt, int) or attempt < 1:
        fail(f"{label} run {run_id}: invalid run attempt {attempt!r}")


def validate_artifacts(
    payload: dict[str, Any], label: str, run_id: int, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    artifacts = payload.get("artifacts")
    total_count = payload.get("total_count")
    if not isinstance(artifacts, list) or not isinstance(total_count, int):
        fail(f"{label} run {run_id}: malformed artifact response")
    if total_count != len(artifacts):
        fail(f"{label} run {run_id}: artifact response was paginated/truncated ({len(artifacts)}/{total_count})")

    by_name: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        name = artifact.get("name")
        if not isinstance(name, str) or not name:
            fail(f"{label} run {run_id}: artifact without a valid name")
        if name in by_name:
            fail(f"{label} run {run_id}: duplicate artifact name {name}")
        by_name[name] = artifact

    required: set[str]
    if "artifacts" in spec:
        required = set(spec["artifacts"])
        missing = sorted(required - set(by_name))
        if missing:
            fail(f"{label} run {run_id}: missing required artifacts: {missing}")
    else:
        prefix = str(spec["artifact_prefix"])
        matches = sorted(name for name in by_name if name.startswith(prefix))
        if len(matches) != 1:
            fail(f"{label} run {run_id}: expected exactly one artifact with prefix {prefix!r}, got {matches}")
        required = set(matches)

    selected: list[dict[str, Any]] = []
    for name in sorted(required):
        artifact = by_name[name]
        if artifact.get("expired") is not False:
            fail(f"{label} run {run_id}: artifact {name} is expired or has invalid expiry state")
        digest = artifact.get("digest")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            fail(f"{label} run {run_id}: artifact {name} has invalid SHA-256 digest {digest!r}")
        workflow_run = artifact.get("workflow_run") or {}
        if workflow_run.get("id") != run_id:
            fail(f"{label} run {run_id}: artifact {name} is associated with run {workflow_run.get('id')!r}")
        artifact_id = artifact.get("id")
        size = artifact.get("size_in_bytes")
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            fail(f"{label} run {run_id}: artifact {name} has invalid id {artifact_id!r}")
        if not isinstance(size, int) or size <= 0:
            fail(f"{label} run {run_id}: artifact {name} has invalid size {size!r}")
        selected.append(
            {
                "id": artifact_id,
                "name": name,
                "size_in_bytes": size,
                "digest": digest,
                "created_at": artifact.get("created_at"),
                "expires_at": artifact.get("expires_at"),
            }
        )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY))
    parser.add_argument("--selector", type=Path, default=Path(".github/ksq-1-acceptance-runs.env"))
    parser.add_argument("--output-dir", type=Path, default=Path("build/ksq-1/technical-acceptance"))
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        fail("GITHUB_TOKEN is required")
    if args.repository != EXPECTED_REPOSITORY:
        fail(f"repository {args.repository!r} != expected {EXPECTED_REPOSITORY!r}")

    selector = args.selector.resolve()
    values = read_env(selector)
    if values.get("AURORA_KSQ_1_ACCEPTANCE_RUNS_STATUS") != "ACTIVE":
        fail("acceptance run selector is not ACTIVE")

    ids: dict[str, int] = {}
    for label, spec in RUN_SPECS.items():
        key = str(spec["selector"])
        raw = values.get(key, "")
        if not raw.isdigit():
            fail(f"selector {key} is not numeric: {raw!r}")
        ids[label] = int(raw)
    if len(set(ids.values())) != len(ids):
        fail(f"selected run IDs are not unique: {ids}")

    api_root = f"https://api.github.com/repos/{args.repository}"
    provenance_runs: dict[str, Any] = {}
    artifact_count = 0

    for label, spec in RUN_SPECS.items():
        run_id = ids[label]
        run = api_get(f"{api_root}/actions/runs/{run_id}", token)
        validate_run(run, label, spec, run_id)
        artifact_payload = api_get(f"{api_root}/actions/runs/{run_id}/artifacts?per_page=100", token)
        artifacts = validate_artifacts(artifact_payload, label, run_id, spec)
        artifact_count += len(artifacts)
        provenance_runs[label] = {
            "id": run_id,
            "name": run.get("name"),
            "path": run.get("path"),
            "event": run.get("event"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "head_branch": run.get("head_branch"),
            "head_sha": run.get("head_sha"),
            "run_number": run.get("run_number"),
            "run_attempt": run.get("run_attempt"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "html_url": run.get("html_url"),
            "actor": (run.get("actor") or {}).get("login"),
            "triggering_actor": (run.get("triggering_actor") or {}).get("login"),
            "required_artifacts": artifacts,
        }

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    provenance = output / "run-provenance.json"
    payload = {
        "schema": "aurora.ksq1.run-provenance.v1",
        "repository": args.repository,
        "branch": EXPECTED_BRANCH,
        "selector": {
            "path": str(selector),
            "sha256": sha256(selector),
        },
        "runs": provenance_runs,
    }
    provenance.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    provenance_sha = output / "run-provenance.sha256"
    provenance_sha.write_text(f"{sha256(provenance)}  run-provenance.json\n", encoding="utf-8")

    status = output / "run-provenance-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_RUN_PROVENANCE_STATUS=PASS",
                f"AURORA_KSQ_1_RUN_PROVENANCE_RUNS={len(provenance_runs)}",
                f"AURORA_KSQ_1_RUN_PROVENANCE_ARTIFACTS={artifact_count}",
                "AURORA_KSQ_1_RUN_PROVENANCE_ARTIFACT_DIGESTS=sha256",
                "AURORA_KSQ_1_RUN_PROVENANCE_EVENT=push",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_RUN_PROVENANCE_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
