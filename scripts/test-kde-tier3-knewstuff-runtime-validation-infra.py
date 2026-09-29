#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/run-kde-tier3-knewstuff-runtime-validation.sh").read_text()

with TemporaryDirectory() as td:
    root = Path(td)
    aid = 123456
    label = "knewstuff"
    extracted = root / f"{aid}-{label}"
    extracted.mkdir()
    (root / f"{aid}-{label}.zip").write_bytes(b"synthetic zip placeholder")

    historical_matches = list(root.glob(f"{aid}-*"))
    if len(historical_matches) != 2:
        raise SystemExit("synthetic preflight failed to reproduce directory+zip ambiguity")

    selected = root / f"{aid}-{label}"
    if not selected.is_dir():
        raise SystemExit("exact artifact-directory selector did not select extracted directory")
    if selected.suffix == ".zip":
        raise SystemExit("exact artifact-directory selector selected archive instead of directory")

if 'artifact_dir=root/f"{aid}-{label}"' not in runner:
    raise SystemExit("runtime runner does not use the certified exact artifact-directory selector")
if 'root.glob(f"{aid}-*")' in runner:
    raise SystemExit("runtime runner still contains the ambiguous artifact glob")

print("KNewStuff runtime-validation infrastructure preflight: PASS")
print("historical_bug_reproduced=directory-plus-sibling-zip")
print("certified_selector=exact-extracted-directory")
