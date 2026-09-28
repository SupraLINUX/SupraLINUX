#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
M=load("manifests/kde-tier3-kio-attempt10-remediation.json")
T=load("manifests/kde-frameworks-tier3.json"); L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json"); MAT=load("manifests/kde-tier3-materialization.json")
A9=load("manifests/kde-tier3-kio-attempt9-remediation.json")
DOC=(ROOT/"docs/kde-tier3-kio-attempt10-remediation.md").read_text()
OLD="6.30.0-0supralinux9"; NEW="6.30.0-0supralinux10"; NEXT="tier3-attempt10-kio-symbol-metadata-materialization-evidence"
req(M.get("schema")==1 and M.get("node")=="kio" and M.get("attempt")==10,"Attempt10 identity")
req(M.get("status")=="definition-pending-ci" and M.get("candidate_package_version")==NEW and M.get("previous_package_version")==OLD,"Attempt10 versions/status")
req(subprocess.run(["dpkg","--compare-versions",NEW,"gt",OLD]).returncode==0,"Attempt10 Debian version increment")
req(M.get("package_revision_bump_required") is True and M.get("source_rematerialization_required") is True,"Attempt10 rematerialization/revision")
req(M.get("materialization_authorized") is True and M.get("package_execution_authorized") is False and M.get("level1_execution_authorized") is False,"Attempt10 authorization boundary")
p=M.get("predecessor_attempt9",{})
req(p.get("workflow_run")==36416891314 and p.get("commit")=="e7dfc689bf18aea5ed194df03f31e9c74627ead0" and p.get("result")=="MIXED" and p.get("kio_tests")=="69/69 PASS","Attempt9 predecessor")
req(A9.get("status")=="attempt9-closed-mixed" and A9.get("attempt9_result",{}).get("functional_remediation_result")=="PASS","Attempt9 historical closure retained")
func=M.get("retained_functional_remediation",{})
req(func.get("krecent_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Attempt10 exact KRecent patch")
req(func.get("patched_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","Attempt10 exact patched source")
req(func.get("test_home")=="debian/supralinux-test-home/sbuild" and func.get("source_code_change_from_attempt9") is False,"Attempt10 functional source unchanged")
sm=M.get("symbol_metadata_remediation",{})
req(sm.get("total_symbols")==34 and sm.get("minimal_version")=="6.30.0" and sm.get("tags")==["optional"],"Attempt10 symbol policy")
req(sm.get("public_abi_promotion") is False and sm.get("lintian_suppression") is False,"Attempt10 ABI/Lintian policy")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")==NEW,"KIO contract -10")
adds=kc.get("symbol_template_additions",[])
req(len(adds)==34,"KIO 34 symbol additions")
req(sum(1 for x in adds if x.get("package")=="libkf6kiocore6")==1,"KIOCore private symbol count")
req(sum(1 for x in adds if x.get("package")=="libkf6kiogui6")==33,"KIOGui test-only symbol count")
for x in adds:
    req(x.get("minimal_version")=="6.30.0" and x.get("tags")==["optional"],"symbol optional upstream baseline: "+str(x.get("symbol")))
    req("-0supralinux" not in x.get("minimal_version",""),"symbol must not use package revision: "+str(x.get("symbol")))
req(any(x.get("symbol")=="_ZN3KIO6Worker20setTestWorkerFactoryERKSt8weak_ptrINS_13WorkerFactoryEE@Base" for x in adds),"Worker test hook symbol")
# Exact GUI membership checked without coupling to ordering.
expected_gui=set(["_ZN3KIO14FilePreviewJob11canBeCachedERK7QString@Base","_ZN3KIO14FilePreviewJob11emitPreviewERK6QImage@Base","_ZN3KIO14FilePreviewJob11qt_metacallEN11QMetaObject4CallEiPPv@Base","_ZN3KIO14FilePreviewJob11qt_metacastEPKc@Base","_ZN3KIO14FilePreviewJob11slotTimeoutEv@Base","_ZN3KIO14FilePreviewJob12isCacheValidERK6QImage@Base","_ZN3KIO14FilePreviewJob12slotStatFileEP4KJob@Base","_ZN3KIO14FilePreviewJob13parentDirPathERK7QString@Base","_ZN3KIO14FilePreviewJob13slotThumbDataEPNS_3JobERK10QByteArray@Base","_ZN3KIO14FilePreviewJob15createThumbnailERK7QString@Base","_ZN3KIO14FilePreviewJob16staticMetaObjectE@Base","_ZN3KIO14FilePreviewJob17saveThumbnailDataER6QImage@Base","_ZN3KIO14FilePreviewJob20getOrCreateThumbnailEv@Base","_ZN3KIO14FilePreviewJob20loadAvailablePluginsEv@Base","_ZN3KIO14FilePreviewJob20saveThumbnailToCacheERK6QImageRK7QString@Base","_ZN3KIO14FilePreviewJob20standardThumbnailersEv@Base","_ZN3KIO14FilePreviewJob21slotStandardThumbDataEPNS_3JobERK6QImage@Base","_ZN3KIO14FilePreviewJob22createThumbnailViaFuseERK4QUrlS3_@Base","_ZN3KIO14FilePreviewJob24preparePluginForMimetypeERK7QString@Base","_ZN3KIO14FilePreviewJob24slotGetOrCreateThumbnailEP4KJob@Base","_ZN3KIO14FilePreviewJob27createThumbnailViaLocalCopyERK4QUrl@Base","_ZN3KIO14FilePreviewJob5startEv@Base","_ZN3KIO14FilePreviewJobC1ERK9KFileItemiRKNS_14PreviewOptionsERKNS_16PreviewSetupDataE@Base","_ZN3KIO14FilePreviewJobC2ERK9KFileItemiRKNS_14PreviewOptionsERKNS_16PreviewSetupDataE@Base","_ZN3KIO14FilePreviewJobD0Ev@Base","_ZN3KIO14FilePreviewJobD1Ev@Base","_ZN3KIO14FilePreviewJobD2Ev@Base","_ZNK3KIO14FilePreviewJob10metaObjectEv@Base","_ZNK3KIO14FilePreviewJob12previewImageEv@Base","_ZNK3KIO14FilePreviewJob23thumbnailWorkerMetaDataEv@Base","_ZTIN3KIO14FilePreviewJobE@Base","_ZTSN3KIO14FilePreviewJobE@Base","_ZTVN3KIO14FilePreviewJobE@Base"])
actual_gui={x.get("symbol") for x in adds if x.get("package")=="libkf6kiogui6"}
req(actual_gui==expected_gui,"FilePreviewJob symbol set")
pol=T.get("discovery_policy",{})
req(pol.get("phase")=="build-level1-planning" and pol.get("package_builds")=="tier3-level1-remediation-pending-materialization" and pol.get("remediation")=="attempt10-kio-symbol-metadata-remediation-pending-materialization","Attempt10 canonical materialization gate")
nodes={x["id"]:x for x in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")==OLD and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO FAIL/-9")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","canonical KXMLGui PASS")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"Level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="attempt10-symbol-metadata-remediation-defined-pending-materialization",name+" Attempt10 status")
    req(obj.get("candidate_package_versions",{}).get("kio")==NEW,name+" KIO candidate")
    req(obj.get("execution_authorized") is False,name+" binary execution blocked")
    req(obj.get("next_gate")==NEXT,name+" next gate")
req(L.get("state")=="attempt9-closed-mixed" and L.get("execution_authorized") is False and L.get("current_attempt")==9 and L.get("next_attempt")==10,"Level1 Attempt9 closure/Attempt10 handoff")
req(MAT.get("state")=="remediation-pending-ci" and MAT.get("remediation_queue")==["kio"],"Attempt10 materialization queue")
req(MAT.get("nodes",{}).get("kio",{}).get("state")=="remediation-pending" and MAT.get("nodes",{}).get("kio",{}).get("package_version")==NEW,"Attempt10 KIO materialization node")
req(MAT.get("nodes",{}).get("kio",{}).get("evidence",{}).get("artifact_id")==10965892140,"Attempt9 -9 source retained as baseline")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Attempt10 definition non-attempt")
req("Attempt 10 binary execution: **not authorized**" in DOC and NEW in DOC and "34" in DOC,"Attempt10 docs")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Attempt 10 symbol-metadata remediation definition: PASS")
print("candidate="+NEW+"; materialization=AUTHORIZED; binary=NOT-AUTHORIZED")
print("symbols=34 optional @ 6.30.0; functional KIO remediation retained")
