#!/usr/bin/env python3
import json
import re
import sys
import time
from pathlib import Path

from kde_plasma_provider_index import apt_file_search_many, apt_source_many

if len(sys.argv)!=2:
    raise SystemExit("usage: run-kde-plasma-provider-resolution-preflight.py <provider-inventory.json>")

inv=json.loads(Path(sys.argv[1]).read_text())
out=Path("evidence/kde-plasma-provider-resolution-preflight")
out.mkdir(parents=True,exist_ok=True)

cmake_other=inv["cmake_categories"].get("other-cmake",[])[:18]
pkg=inv["pkg_config_requirements"][:12]
qml=inv["qml_requirements"][:6]

patterns=[
    r"/Qt6Config\.cmake$",
    r"/ECMConfig\.cmake$",
    r"/pkgconfig/libpipewire-0\.3\.pc$",
]
patterns += [rf"/{re.escape(x)}Config\.cmake$" for x in cmake_other]
patterns += [rf"/pkgconfig/{re.escape(re.split(r'[<>=]',x,1)[0].strip())}\.pc$" for x in pkg]
patterns += [rf"/qml/{re.escape(x.replace('.','/'))}/qmldir$" for x in qml]

start=time.monotonic()
hits=apt_file_search_many(patterns,chunk_size=12)
apt_file_seconds=time.monotonic()-start

source_sample=[
    "kdecoration","kpipewire","kwayland","layer-shell-qt","libkscreen","libksysguard",
    "libplasma","plasma-activities","plasma-workspace","plasma-desktop","kwin","kwin-x11",
]
start=time.monotonic()
sources=apt_source_many(source_sample)
showsrc_seconds=time.monotonic()-start

anchors={
    "Qt6Config":hits.get(r"/Qt6Config\.cmake$",[]),
    "ECMConfig":hits.get(r"/ECMConfig\.cmake$",[]),
    "pipewire-pc":hits.get(r"/pkgconfig/libpipewire-0\.3\.pc$",[]),
}
if not anchors["Qt6Config"]:
    raise SystemExit("preflight: Qt6Config provider anchor missing")
if not anchors["ECMConfig"]:
    raise SystemExit("preflight: ECMConfig provider anchor missing")
if not anchors["pipewire-pc"]:
    raise SystemExit("preflight: libpipewire pkg-config provider anchor missing")
if apt_file_seconds > 180:
    raise SystemExit(f"preflight: apt-file chunked index too slow: {apt_file_seconds:.2f}s")
if showsrc_seconds > 60:
    raise SystemExit(f"preflight: batched apt-cache showsrc too slow: {showsrc_seconds:.2f}s")
if not any(v["available"] for v in sources.values()):
    raise SystemExit("preflight: no Ubuntu source references available in sample")

result={
    "schema":1,
    "node":"plasma-provider-resolution-infrastructure-preflight",
    "state":"PASS",
    "run_kind":"infrastructure-preflight",
    "authoritative":False,
    "package_execution_started":False,
    "consumes_package_attempt":False,
    "canonical_package_state_effect":"none",
    "mechanism":"apt-file-chunked-regex-plus-batched-apt-cache-showsrc",
    "apt_file_pattern_count":len(patterns),
    "apt_file_chunk_size":12,
    "apt_file_seconds":round(apt_file_seconds,3),
    "showsrc_source_count":len(source_sample),
    "showsrc_seconds":round(showsrc_seconds,3),
    "anchors":anchors,
    "available_source_references":sum(1 for v in sources.values() if v["available"]),
    "next_gate":"resume-plasma-provider-resolution",
}
(out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
(out/"sample-hits.json").write_text(json.dumps(hits,indent=2,sort_keys=True)+"\n")
(out/"sample-sources.json").write_text(json.dumps(sources,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2))
