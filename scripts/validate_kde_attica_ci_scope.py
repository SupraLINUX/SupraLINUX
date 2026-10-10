#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCOPE = ROOT / "scripts" / "kde-attica-package-preflight-needed.sh"
REFERENCE_SCOPE = ROOT / "scripts" / "kde-attica-packaging-reference-needed.sh"
PACKAGE_WORKFLOW = ROOT / ".github" / "workflows" / "kde-attica-package-preflight.yml"
REFERENCE_WORKFLOW = ROOT / ".github" / "workflows" / "kde-attica-packaging-reference.yml"

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


package_scope = read(PACKAGE_SCOPE)
reference_scope = read(REFERENCE_SCOPE)
package_workflow = read(PACKAGE_WORKFLOW)
reference_workflow = read(REFERENCE_WORKFLOW)

for name, scope in (("package", package_scope), ("reference", reference_scope)):
    require('git diff --name-only "${BEFORE}" "${AFTER}" --' in scope, f"Attica {name} scope must compare the actual event delta")
    require('git cat-file -e "${sha}^{commit}"' in scope, f"Attica {name} scope must verify both event commits exist")
    require("exit 1" in scope, f"Attica {name} scope must use exit 1 for intentional skip")
    require("docs/" not in scope, f"Attica {name} scope must not rebuild merely for documentation changes")
    require("manifests/" not in scope, f"Attica {name} scope must not rebuild merely for manifest/evidence changes")

for token in (
    "packages/kde/attica/*",
    "scripts/run-kde-attica-package-preflight.sh",
    "scripts/kde-attica-package-preflight-needed.sh",
    ".github/workflows/kde-attica-package-preflight.yml",
):
    require(token in package_scope, f"Attica package scope must track real package input {token}")

for token in (
    "scripts/run-kde-attica-packaging-reference.sh",
    "scripts/kde-attica-packaging-reference-needed.sh",
    ".github/workflows/kde-attica-packaging-reference.yml",
):
    require(token in reference_scope, f"Attica reference scope must track real capture input {token}")
require("packages/kde/attica/" not in reference_scope, "Attica distro-reference capture must not rerun for SupraLINUX package-only changes")

for name, workflow, scope_script in (
    ("package", package_workflow, "scripts/kde-attica-package-preflight-needed.sh"),
    ("reference", reference_workflow, "scripts/kde-attica-packaging-reference-needed.sh"),
):
    require("fetch-depth: 0" in workflow, f"Attica {name} workflow must fetch enough history for event-delta comparison")
    require(scope_script in workflow, f"Attica {name} workflow must execute its delta-scope helper")
    require("github.event.action" in workflow and "synchronize" in workflow, f"Attica {name} workflow must use before/after for synchronize events")
    require("github.event.before" in workflow and "github.event.after" in workflow, f"Attica {name} workflow must bind synchronize delta exactly")
    require("github.event.pull_request.base.sha" in workflow and "github.event.pull_request.head.sha" in workflow, f"Attica {name} workflow must handle opened/reopened PR events")
    require("paths:" not in workflow, f"Attica {name} workflow must not rely on PR-wide paths filtering")
    require("steps.scope.outputs.run == 'true'" in workflow, f"Attica {name} expensive steps must be scope-gated")
    require("steps.scope.outputs.run != 'true'" in workflow, f"Attica {name} workflow must report intentional skips")

for token in (
    "Download retained ECM PASS artifact",
    "Download retained Attica packaging-reference artifact",
    "Build and validate Attica 6.30 in clean Resolute sbuild",
    "Upload Attica package evidence",
):
    require(token in package_workflow, f"Attica package workflow lost step {token}")
require(package_workflow.count("steps.scope.outputs.run == 'true'") >= 4, "All expensive Attica package steps must be gated")

for token in (
    "Capture pinned Ubuntu/Debian packaging trees",
    "Upload Attica packaging-reference evidence",
):
    require(token in reference_workflow, f"Attica reference workflow lost step {token}")
require(reference_workflow.count("steps.scope.outputs.run == 'true'") >= 2, "All expensive Attica reference steps must be gated")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Attica CI event-delta scope validation: PASS")
print("Documentation/manifest-only synchronize events: expensive package/reference work must skip")
print("Package inputs and reference-capture inputs remain independently scoped")
