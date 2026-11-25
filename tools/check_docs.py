from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
required = ["README.md", "AGENTS.md", "docs/MIGRATION.md", "docs/distribution/README.md", "docs/distribution/VALIDATION.md", "docs/distribution/PROTOTYPE_GATES.md", "docs/decisions/README.md"]
errors = [f"missing: {p}" for p in required if not (root/p).is_file()]
for p in root.rglob("*.md"):
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", p.read_text(encoding="utf-8")):
        if ":" in target or target.startswith("#"):
            continue
        if not (p.parent / target.split("#",1)[0]).exists():
            errors.append(f"{p.relative_to(root)}: {target}")
if errors:
    raise SystemExit("\n".join(errors))
print("Documentation paths OK")
