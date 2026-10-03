#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

from kde_plasma_provider_index import apt_source_many, build_dep_packages, apt_policy_many

if len(sys.argv)!=2:
    raise SystemExit("usage: run-kde-plasma-provider-resolution-preflight.py <provider-inventory.json>")

Path(sys.argv[1]).read_text()  # prove promoted input is readable
out=Path("evidence/kde-plasma-provider-resolution-preflight")
out.mkdir(parents=True,exist_ok=True)

source_sample=[
    "kdecoration","kpipewire","kwayland","layer-shell-qt","libkscreen","libksysguard",
    "libplasma","plasma-activities","plasma-workspace","plasma-desktop","kwin","kwin-x11",
]

start=time.monotonic()
sources=apt_source_many(source_sample)
showsrc_seconds=time.monotonic()-start
available={name:data for name,data in sources.items() if data["available"]}
if len(available) < 6:
    raise SystemExit(f"preflight: too few Ubuntu source references available: {len(available)}/12")
if showsrc_seconds > 30:
    raise SystemExit(f"preflight: batched apt-cache showsrc too slow: {showsrc_seconds:.2f}s")

build_deps=set()
for data in available.values():
    build_deps.update(build_dep_packages(data))

anchors=["qt6-base-dev","extra-cmake-modules","libpipewire-0.3-dev"]
start=time.monotonic()
policies=apt_policy_many(sorted(build_deps | set(anchors)))
policy_seconds=time.monotonic()-start

missing_anchors=[pkg for pkg in anchors if not policies.get(pkg)]
if missing_anchors:
    raise SystemExit("preflight: provider anchors missing candidates: "+",".join(missing_anchors))
if policy_seconds > 30:
    raise SystemExit(f"preflight: batched apt-cache policy too slow: {policy_seconds:.2f}s")

result={
    "schema":1,
    "node":"plasma-provider-resolution-infrastructure-preflight",
    "state":"PASS",
    "run_kind":"infrastructure-preflight",
    "authoritative":False,
    "package_execution_started":False,
    "consumes_package_attempt":False,
    "canonical_package_state_effect":"none",
    "mechanism":"batched-apt-cache-showsrc-plus-policy",
    "source_sample_count":len(source_sample),
    "available_source_references":len(available),
    "build_dep_package_count":len(build_deps),
    "showsrc_seconds":round(showsrc_seconds,3),
    "policy_seconds":round(policy_seconds,3),
    "anchors":{pkg:policies[pkg] for pkg in anchors},
    "next_gate":"resume-plasma-provider-resolution",
}
(out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
(out/"sample-sources.json").write_text(json.dumps(sources,indent=2,sort_keys=True)+"\n")
(out/"sample-policy.json").write_text(json.dumps({p:policies[p] for p in sorted(policies)},indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2))
