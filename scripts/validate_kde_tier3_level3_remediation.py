#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

closure=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_attempt1_closure.py")])
if closure.returncode:
    raise SystemExit(closure.returncode)

c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
t=load("manifests/kde-frameworks-tier3.json")
l3=load("manifests/kde-tier3-build-level3.json")
a=load("manifests/kde-tier3-build-level3-attempts.json")
support=load("manifests/kde-tier3-support-build-level1.json")

# Closed Attempt 3 source materialization: validate immutable Attempts 1/2, then the new source-only evidence.
_phase=t.get("level3_remediation",{}).get("status")
_trigger=t.get("level3_remediation",{}).get("trigger",{})
if _phase=="materialization-PASS-pending-attempt3-planning-validation" and _trigger.get("attempt")==2:
    closure2=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_attempt2_closure.py")])
    if closure2.returncode:
        raise SystemExit(closure2.returncode)

    T3=["ktexteditor","purpose"]
    V3={"ktexteditor":"6.30.0-0supralinux3","purpose":"6.30.0-0supralinux3"}
    BASE={"ktexteditor":"6.30.0-0supralinux2","purpose":"6.30.0-0supralinux2"}
    SNAP3="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
    NEXT3="tier3-build-level3-attempt3-planning-validation"
    ART3={
      "ktexteditor":{"workflow_run":36643423967,"job_id":109661057170,"artifact_id":11066929892,"artifact_sha256":"74afd833bcd1f35571e59a9983e5fa56bb8b774eff4210df9c4a5b6a93a321b5","commit":"91a493ffe10620d00350c404f37c13baa9fdbd45","package_version":"6.30.0-0supralinux3"},
      "purpose":{"workflow_run":36643423967,"job_id":109661057232,"artifact_id":11067860328,"artifact_sha256":"988a4d2f21d152a938e17b802026a9c950fd2a91351ab2fbee6ae1300720945f","commit":"91a493ffe10620d00350c404f37c13baa9fdbd45","package_version":"6.30.0-0supralinux3"},
    }
    campaign=load("manifests/kde-tier3-build-campaign.json")

    req(c.get("level3_remediation",{}).get("status")=="materialization-PASS-pending-attempt3-planning-validation","Attempt3 contracts materialization closure")
    req(c.get("level3_remediation",{}).get("materialization_authorized") is False and c.get("level3_remediation",{}).get("package_build_authorized") is False,"Attempt3 contracts execution boundary")
    req(c.get("level3_remediation",{}).get("source_materialization_complete") is True and c.get("level3_remediation",{}).get("next_gate")==NEXT3,"Attempt3 contracts next gate")
    req(c.get("level3_remediation",{}).get("materialization_evidence",{}).get("artifacts")==ART3,"Attempt3 contracts artifact pins")

    req(m.get("state")=="PASS" and m.get("remediation_queue")==[] and m.get("package_attempted") is False and m.get("package_state_effect")=="none","Attempt3 materialization closed source-only PASS")
    mr=m.get("level3_remediation",{})
    req(mr.get("status")=="materialization-PASS" and mr.get("materialization_authorized") is False and mr.get("package_execution_authorized") is False,"Attempt3 materialization execution boundary")
    req(mr.get("source_materialization_complete") is True and mr.get("next_gate")==NEXT3,"Attempt3 materialization next gate")
    req(mr.get("materialization_evidence",{}).get("artifacts")==ART3,"Attempt3 materialization artifact pins")

    req(t.get("discovery_policy",{}).get("phase")=="build-level3-remediation-planning","Attempt3 canonical remediation phase")
    req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-remediation-materialized-pending-attempt3-planning-validation","Attempt3 canonical planning gate")
    req(t.get("discovery_policy",{}).get("remediation")=="level3-attempt2-remediation-materialized","Attempt3 canonical remediation marker")
    req(t.get("build_level3",{}).get("status")=="attempt2-closed-FAIL-remediation-materialized-pending-attempt3-activation","Attempt3 canonical binary lifecycle")
    req(t.get("build_level3",{}).get("execution_authorized") is False and t.get("build_level3",{}).get("current_attempt")==2 and t.get("build_level3",{}).get("next_attempt")==3 and t.get("build_level3",{}).get("next_gate")==NEXT3,"Attempt3 canonical binary pause/gate")
    tr=t.get("level3_remediation",{})
    req(tr.get("status")=="materialization-PASS-pending-attempt3-planning-validation" and tr.get("materialization_authorized") is False and tr.get("package_execution_authorized") is False,"Attempt3 canonical materialization closure")
    req(tr.get("canonical_snapshot")==SNAP3 and tr.get("source_materialization_complete") is True and tr.get("materialization_evidence",{}).get("artifacts")==ART3,"Attempt3 canonical source evidence")

    req(l3.get("state")=="remediation-materialized-pending-activation" and l3.get("execution_authorized") is False,"Attempt3 Level3 package execution paused")
    req(l3.get("current_attempt")==2 and l3.get("next_attempt")==3 and l3.get("next_gate")==NEXT3 and l3.get("canonical_snapshot")==SNAP3,"Attempt3 Level3 planning markers")
    lr=l3.get("level3_remediation",{})
    req(lr.get("status")=="materialization-PASS-pending-attempt3-planning-validation" and lr.get("materialization_authorized") is False and lr.get("package_execution_authorized") is False,"Attempt3 Level3 remediation closure")
    req(lr.get("materialization_evidence",{}).get("artifacts")==ART3,"Attempt3 Level3 artifact pins")

    tn={x["id"]:x for x in t.get("nodes",[])}
    for node in T3:
        mm=m["nodes"][node]
        ev=mm.get("evidence",{})
        req(mm.get("state")=="materialized" and mm.get("package_version")==V3[node] and mm.get("candidate_package_version")==V3[node],node+": Attempt3 materialized version")
        req(ev.get("workflow_run")==ART3[node]["workflow_run"] and ev.get("job_id")==ART3[node]["job_id"] and ev.get("artifact_id")==ART3[node]["artifact_id"] and ev.get("artifact_sha256")==ART3[node]["artifact_sha256"],node+": Attempt3 materialization evidence")
        req(ev.get("result")=="PASS" and ev.get("stage")=="complete" and ev.get("exit_code")==0 and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none",node+": Attempt3 source-only PASS")
        hist=mm.get("evidence_history",[])
        req(any(x.get("package_version")=="6.30.0-0supralinux1" for x in hist) and any(x.get("package_version")==BASE[node] for x in hist),node+": previous materialization history retained")
        prev=mm.get("retained_previous_evidence",{})
        req(prev.get("package_version")==BASE[node] and prev.get("result")=="PASS" and prev.get("package_attempted") is False,node+": immediate previous materialization retained")

        ln=l3["nodes"][node]
        req(ln.get("state")=="remediation-pending-build" and ln.get("package_version")==V3[node],node+": Attempt3 prepared package identity")
        req(ln.get("materialization")=={k:ART3[node][k] for k in ("workflow_run","job_id","artifact_id","artifact_sha256")},node+": Attempt3 Level3 materialization pin")
        cp=campaign.get("nodes",{}).get(node,{})
        req(cp.get("package_version")==V3[node] and cp.get("materialization")==ln.get("materialization"),node+": generated campaign Attempt3 pin")

        can=tn.get(node,{})
        pkg=can.get("packaging",{})
        req(can.get("state")=="FAIL" and pkg.get("state")=="FAIL" and pkg.get("package_version")==BASE[node] and pkg.get("downstream_eligible") is False,node+": canonical Attempt2 FAIL retained until Attempt3 package result")

    req(len(a.get("campaign_history",[]))==2 and all(len(a.get("nodes",{}).get(x,[]))==2 for x in T3),"Attempt3 source closure consumed no Package Attempt")
    if errors:
        for e in errors: print("ERROR:",e,file=sys.stderr)
        raise SystemExit(1)
    print("KDE Tier 3 Level 3 Attempt 3 source materialization closure: PASS")
    print("materialization=ktexteditor,purpose; version=6.30.0-0supralinux3")
    print("package-execution-authorized=false")
    raise SystemExit(0)

# Attempt 3 source remediation is a new live lifecycle over immutable Attempts 1/2.
_phase=t.get("level3_remediation",{}).get("status")
_trigger=t.get("level3_remediation",{}).get("trigger",{})
if _phase=="materialization-pending-ci" and _trigger.get("attempt")==2:
    closure2=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_attempt2_closure.py")])
    if closure2.returncode:
        raise SystemExit(closure2.returncode)

    T3=["ktexteditor","purpose"]
    V3={"ktexteditor":"6.30.0-0supralinux3","purpose":"6.30.0-0supralinux3"}
    BASE={"ktexteditor":"6.30.0-0supralinux2","purpose":"6.30.0-0supralinux2"}
    SNAP3="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
    GATE3="tier3-level3-attempt3-remediation-materialization-evidence"
    TRIGGER3={"attempt":2,"workflow_run":36639418961,"commit":"9fd5041053a176fdafcb3939e57a0ff2dd26d91e","failed_nodes":T3,"rootfs_artifact_id":11066320451,"rootfs_artifact_sha256":"d6ec90546a42d24d6561e49c9684ca03716b9c0ce4b98d7d95415571e3f4bb85"}
    MAT2={
      "ktexteditor":(36637751833,109643132222,11064709291,"606f9e22f162382f60b9499654248ebb8ac9e7970f47934b11457757a832becf"),
      "purpose":(36614234522,109563580375,11054941469,"b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7"),
    }

    for obj,name in ((c.get("level3_remediation",{}),"contracts"),(m.get("level3_remediation",{}),"materialization"),(t.get("level3_remediation",{}),"canonical"),(l3.get("level3_remediation",{}),"level3")):
        req(obj.get("status")=="materialization-pending-ci",name+": Attempt3 remediation status")
        req(obj.get("trigger")==TRIGGER3,name+": Attempt3 remediation trigger")
        req(obj.get("candidate_package_versions")==V3,name+": Attempt3 candidate versions")
        req(obj.get("package_attempted") in {None,False},name+": Attempt3 has no package attempt")

    req(c["level3_remediation"].get("materialization_authorized") is True and c["level3_remediation"].get("package_build_authorized") is False,"Attempt3 contract source-only authorization")
    req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==T3,"Attempt3 materialization queue")
    req(m.get("package_attempted") is False and m.get("package_state_effect")=="none","Attempt3 materialization has no package state effect")
    req(m["level3_remediation"].get("materialization_authorized") is True and m["level3_remediation"].get("package_execution_authorized") is False,"Attempt3 materialization execution boundary")
    req(t.get("discovery_policy",{}).get("phase")=="build-level3-remediation-planning","Attempt3 canonical remediation phase")
    req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-attempt3-remediation-pending-materialization","Attempt3 canonical materialization gate")
    req(t.get("discovery_policy",{}).get("remediation")=="level3-attempt2-remediation-materialization","Attempt3 canonical remediation marker")
    req(t.get("build_level3",{}).get("status")=="attempt2-closed-FAIL" and t.get("build_level3",{}).get("execution_authorized") is False,"Attempt2 binary closure retained")
    req(t.get("build_level3",{}).get("current_attempt")==2 and t.get("build_level3",{}).get("next_attempt")==3 and t.get("build_level3",{}).get("next_gate")==GATE3,"Attempt3 canonical live gate")
    req(l3.get("state")=="FAIL" and l3.get("execution_authorized") is False and l3.get("current_attempt")==2 and l3.get("next_attempt")==3 and l3.get("next_gate")==GATE3,"Attempt3 package execution remains paused")
    req(l3.get("canonical_snapshot")==SNAP3,"Attempt3 canonical snapshot")
    req(len(a.get("campaign_history",[]))==2 and all(len(a.get("nodes",{}).get(x,[]))==2 for x in T3),"Attempts 1/2 ledger remains immutable")

    tn={x["id"]:x for x in t.get("nodes",[])}
    for node in T3:
        mm=m["nodes"][node]
        run,job,artifact,digest=MAT2[node]
        ev=mm.get("evidence",{})
        req(mm.get("state")=="remediation-pending" and mm.get("package_version")==BASE[node] and mm.get("candidate_package_version")==V3[node],node+": Attempt3 materialization candidate")
        req(ev.get("workflow_run")==run and ev.get("job_id")==job and ev.get("artifact_id")==artifact and ev.get("artifact_sha256")==digest,node+": retained Attempt2 source materialization")
        req(ev.get("result")=="PASS" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none",node+": retained source-only PASS")
        can=tn.get(node,{})
        pkg=can.get("packaging",{})
        req(can.get("state")=="FAIL" and pkg.get("state")=="FAIL" and pkg.get("package_version")==BASE[node] and pkg.get("downstream_eligible") is False,node+": canonical Attempt2 FAIL retained")
        ln=l3["nodes"][node]
        req(ln.get("state")=="FAIL" and ln.get("package_version")==BASE[node],node+": Level3 Attempt2 FAIL retained")

    kt=c["nodes"]["ktexteditor"]
    req(kt.get("package_version_candidate")==V3["ktexteditor"],"Attempt3 KTextEditor revision")
    req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tdh_auto_test --no-parallel" and x.get("expected_count")==1 for x in kt.get("rules_text_replacements",[])),"Attempt3 KTextEditor serialized full suite retained")
    ksp=kt.get("supralinux_source_patches",[])
    req(len(ksp)==1 and ksp[0].get("name")=="supralinux-test-abouttosave-self-contained-fixture.patch" and ksp[0].get("target")=="autotests/src/katedocument_test.cpp","Attempt3 KTextEditor self-contained fixture patch")
    if ksp:
        req(ksp[0].get("expected_patch_sha256")=="b4d9868777b7da55bf92b4196aa948671629f42c8827bade013f4a56926635b5","Attempt3 KTextEditor patch digest")
        req(ksp[0].get("expected_source_sha256")=="7d1de51198c26826007b21b03b42e0c6509cc50c2ea1715d8513fdef529ebe6d","Attempt3 KTextEditor source digest")

    pu=c["nodes"]["purpose"]
    req(pu.get("package_version_candidate")==V3["purpose"],"Attempt3 Purpose revision")
    req(any(x.get("action")=="ensure" and x.get("relation")=="kio6 (>= 6.30.0~) <!nocheck>" for x in pu.get("source_build_relation_overrides",[])),"Attempt3 Purpose KIO worker provider retained")
    req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tQT_QPA_PLATFORM=offscreen dh_auto_test" and x.get("expected_count")==1 for x in pu.get("rules_text_replacements",[])),"Attempt3 Purpose offscreen environment retained")
    psp={x.get("name"):x for x in pu.get("supralinux_source_patches",[])}
    req(set(psp)=={"supralinux-purpose-runjob-local-source.patch","supralinux-purpose-menutest-local-source.patch"},"Attempt3 Purpose local-source patch set")
    if "supralinux-purpose-runjob-local-source.patch" in psp:
        x=psp["supralinux-purpose-runjob-local-source.patch"]
        req(x.get("target")=="autotests/alternativesmodeltest.cpp" and x.get("expected_patch_sha256")=="888db6f1c73a9bfbc007050baa9cc697b85a98079cd0e51279ca4b70cb58369a" and x.get("expected_source_sha256")=="e6c414e12136a2805bb3309abf7e83c2f046e79ed5998bca87b306930891394c","Attempt3 Purpose AlternativesModel patch hashes")
    if "supralinux-purpose-menutest-local-source.patch" in psp:
        x=psp["supralinux-purpose-menutest-local-source.patch"]
        req(x.get("target")=="autotests/menutest.cpp" and x.get("expected_patch_sha256")=="9013b6add8307ae55c407005ae7a79621aa381926d73874d4bf0283403dbde2b" and x.get("expected_source_sha256")=="50bcd5f12061e25e0ed1b5b4dbe45c581a4ee2699aa238b6a84c07c8bac153f8","Attempt3 Purpose Menu patch hashes")

    req(c.get("stable_promotion_requires_explicit_user_approval") is True,"Attempt3 stable approval contract")
    req(m.get("stable_promotion_requires_explicit_user_approval") is True,"Attempt3 stable approval materialization")
    if errors:
        for e in errors: print("ERROR:",e,file=sys.stderr)
        raise SystemExit(1)
    print("KDE Tier 3 Level 3 Attempt 3 remediation definition: PASS")
    print("source-rematerialization=ktexteditor,purpose; candidate=6.30.0-0supralinux3")
    print("package-execution-authorized=false")
    raise SystemExit(0)

if t.get("level3_remediation",{}).get("status") in {"attempt2-active","attempt2-closed-FAIL-pending-remediation-definition","attempt3-active"}:
    # Source-remediation evidence is closed. The current binary lifecycle is
    # authoritative from this point forward; do not constrain it with the
    # historical materialization-planning state.
    raise SystemExit(subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_build_level3.py")]).returncode)

T=["ktexteditor","purpose"]
VERS={"ktexteditor":"6.30.0-0supralinux2","purpose":"6.30.0-0supralinux2"}
SNAP="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
TRIGGER={"attempt":1,"workflow_run":36607647059,"commit":"2692489bdb861520181df486c524efb9cdf47d60","failed_nodes":T,"rootfs_artifact_id":11051807633,"rootfs_artifact_sha256":"08eb26b3d264c79e26dd0f5e1cb6fe543a16e1f2be0f713bab5fee45cabdbd83"}
PENDING="materialization-pending-ci"
FINAL="materialization-PASS-pending-attempt2-planning-validation"
phase=t.get("level3_remediation",{}).get("status")
finalized=phase==FINAL
req(phase in {PENDING,FINAL},"canonical Level3 remediation lifecycle")

for obj,name in ((c.get("level3_remediation",{}),"contracts"),(m.get("level3_remediation",{}),"materialization"),(t.get("level3_remediation",{}),"canonical"),(l3.get("level3_remediation",{}),"level3")):
    expected="materialization-PASS" if finalized and name=="materialization" else phase
    req(obj.get("status")==expected,name+": Level3 remediation status")
    req(obj.get("trigger")==TRIGGER,name+": Level3 remediation trigger")
    req(obj.get("candidate_package_versions")==VERS,name+": candidate versions")
    req(obj.get("package_attempted") in {None,False},name+": no package attempt")

req(m.get("package_attempted") is False and m.get("package_state_effect")=="none","materialization has no package state effect")
req(t["level3_remediation"].get("canonical_snapshot")==SNAP and t["level3_remediation"].get("current_attempt")==1 and t["level3_remediation"].get("next_attempt")==2,"canonical snapshot/attempt markers")
req(len(a.get("campaign_history",[]))==1 and all(len(a.get("nodes",{}).get(x,[]))==1 for x in T),"Attempt2 has not consumed package execution")

if not finalized:
    req(c["level3_remediation"].get("materialization_authorized") is True and c["level3_remediation"].get("package_build_authorized") is False,"contract materialization/package authorization")
    req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==["ktexteditor"],"Level3 remediation materialization queue")
    req(m["level3_remediation"].get("materialization_authorized") is True and m["level3_remediation"].get("package_execution_authorized") is False,"materialization execution boundary")
    req(t.get("discovery_policy",{}).get("phase")=="build-level3-remediation-planning","canonical remediation phase")
    req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-remediation-pending-materialization","canonical materialization gate")
    req(t.get("discovery_policy",{}).get("remediation")=="level3-attempt1-remediation-materialization","canonical remediation marker")
    req(t.get("build_level3",{}).get("status")=="attempt1-closed-FAIL" and t.get("build_level3",{}).get("execution_authorized") is False,"binary Level3 remains closed")
    req(t["level3_remediation"].get("materialization_authorized") is True and t["level3_remediation"].get("package_execution_authorized") is False,"canonical source-only authorization")
    req(l3.get("state")=="FAIL" and l3.get("execution_authorized") is False and l3.get("current_attempt")==1 and l3.get("next_attempt")==2,"Level3 package execution remains paused")
    req(l3.get("canonical_snapshot")==SNAP and l3.get("next_gate")=="tier3-level3-remediation-materialization-evidence","Level3 remediation next gate")

    progress=m.get("level3_remediation",{}).get("materialization_progress",{})
    req(progress.get("workflow_run")==36614234522 and progress.get("result")=="PARTIAL","Level3 partial materialization evidence")
    req(progress.get("PASS")==["purpose"] and progress.get("INFRA_INVALID")==["ktexteditor"] and progress.get("package_attempted") is False,"Level3 partial materialization classification")
    inc=progress.get("infrastructure_incident",{})
    req(inc.get("classification")=="INFRA_INVALID" and inc.get("node")=="ktexteditor" and inc.get("job_id")==109563580419 and inc.get("artifact_id")==11055071212 and inc.get("package_attempted") is False,"KTextEditor materialization infrastructure incident")

    ktm=m["nodes"]["ktexteditor"]
    req(ktm.get("state")=="remediation-pending" and ktm.get("candidate_package_version")==VERS["ktexteditor"],"KTextEditor materialization remains pending")
    req(ktm.get("retained_previous_evidence",{}).get("result")=="PASS" and ktm.get("materialization_incident",{}).get("classification")=="INFRA_INVALID","KTextEditor retained source/incident")
else:
    req(c["level3_remediation"].get("materialization_authorized") is False and c["level3_remediation"].get("package_build_authorized") is False,"final contract execution boundary")
    req(m.get("state")=="PASS" and m.get("remediation_queue")==[],"Level3 remediation materialization closed PASS")
    req(m["level3_remediation"].get("source_materialization_complete") is True and m["level3_remediation"].get("materialization_authorized") is False and m["level3_remediation"].get("package_execution_authorized") is False,"final materialization execution boundary")
    req(t.get("discovery_policy",{}).get("phase")=="build-level3-remediation-planning","canonical remediation planning phase")
    req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-remediation-materialized-pending-attempt2-planning-validation","canonical Attempt2 planning gate")
    req(t.get("discovery_policy",{}).get("remediation")=="level3-attempt1-remediation-materialized","canonical remediation materialized marker")
    req(t.get("build_level3",{}).get("status")=="attempt1-closed-FAIL-remediation-materialized-pending-attempt2-activation" and t.get("build_level3",{}).get("execution_authorized") is False,"binary Level3 Attempt2 remains paused")
    req(t["level3_remediation"].get("materialization_authorized") is False and t["level3_remediation"].get("package_execution_authorized") is False,"canonical final source-only boundary")
    req(l3.get("state")=="remediation-materialized-pending-activation" and l3.get("execution_authorized") is False and l3.get("current_attempt")==1 and l3.get("next_attempt")==2,"Level3 Attempt2 planning state")
    req(l3.get("canonical_snapshot")==SNAP and l3.get("next_gate")=="tier3-build-level3-attempt2-planning-validation","Level3 Attempt2 planning next gate")

    ev=m["level3_remediation"].get("materialization_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","final materialization evidence result")
    arts=ev.get("artifacts",{})
    req(arts.get("ktexteditor",{}).get("workflow_run")==36637751833 and arts.get("ktexteditor",{}).get("job_id")==109643132222 and arts.get("ktexteditor",{}).get("artifact_id")==11064709291 and arts.get("ktexteditor",{}).get("artifact_sha256")=="606f9e22f162382f60b9499654248ebb8ac9e7970f47934b11457757a832becf","KTextEditor final materialization artifact")
    req(arts.get("purpose",{}).get("workflow_run")==36614234522 and arts.get("purpose",{}).get("job_id")==109563580375 and arts.get("purpose",{}).get("artifact_id")==11054941469 and arts.get("purpose",{}).get("artifact_sha256")=="b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7","Purpose final materialization artifact")

    for node,run,job,artifact,digest in (
        ("ktexteditor",36637751833,109643132222,11064709291,"606f9e22f162382f60b9499654248ebb8ac9e7970f47934b11457757a832becf"),
        ("purpose",36614234522,109563580375,11054941469,"b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7"),
    ):
        mm=m["nodes"][node]; mev=mm.get("evidence",{})
        req(mm.get("state")=="materialized" and mm.get("package_version")==VERS[node] and mm.get("candidate_package_version")==VERS[node],node+": final materialized version")
        req(mev.get("workflow_run")==run and mev.get("job_id")==job and mev.get("artifact_id")==artifact and mev.get("artifact_sha256")==digest,node+": final materialization evidence")
        req(mev.get("result")=="PASS" and mev.get("package_attempted") is False and mev.get("package_state_effect")=="none",node+": final source-only PASS")

        ln=l3["nodes"][node]
        req(ln.get("state")=="remediation-pending-build" and ln.get("package_version")==VERS[node],node+": Attempt2 prepared package identity")
        req(ln.get("materialization")=={"workflow_run":run,"job_id":job,"artifact_id":artifact,"artifact_sha256":digest},node+": Attempt2 materialization pin")

pum=m["nodes"]["purpose"]; pev=pum.get("evidence",{})
req(pum.get("state")=="materialized" and pum.get("package_version")==VERS["purpose"] and pum.get("candidate_package_version")==VERS["purpose"],"Purpose remediation materialized")
req(pev.get("workflow_run")==36614234522 and pev.get("job_id")==109563580375 and pev.get("artifact_id")==11054941469 and pev.get("artifact_sha256")=="b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7","Purpose materialization artifact")
req(pev.get("result")=="PASS" and pev.get("package_attempted") is False and pev.get("package_state_effect")=="none","Purpose source-only materialization PASS")
req(pev.get("package_version")==VERS["purpose"] and pev.get("materialized_tree_sha256")=="b320bfaaba55b2a76adbfd2b4f5354b4315de6926672eafcf239d4ad348020bc","Purpose materialized version/tree")
req(pum.get("retained_previous_evidence",{}).get("result")=="PASS","Purpose previous materialization retained")

for x in T:
    node=next(n for n in t["nodes"] if n["id"]==x)
    req(node.get("state")=="FAIL" and node.get("packaging",{}).get("state")=="FAIL" and node.get("packaging",{}).get("downstream_eligible") is False,x+": canonical FAIL retained")

kt=c["nodes"]["ktexteditor"]
req(kt.get("package_version_candidate")==VERS["ktexteditor"],"KTextEditor revision")
rr=kt.get("rules_text_replacements",[])
req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tdh_auto_test --no-parallel" and x.get("expected_count")==1 for x in rr),"KTextEditor serialized full test suite")
sp=kt.get("supralinux_source_patches",[])
req(len([x for x in sp if x.get("name")=="supralinux-test-abouttosave-writable-copy.patch"])==1,"KTextEditor writable-save test patch")
kp=next((x for x in sp if x.get("name")=="supralinux-test-abouttosave-writable-copy.patch"),{})
req(kp.get("target")=="autotests/src/katedocument_test.cpp","KTextEditor test-only patch target")
req(kp.get("expected_patch_sha256")=="4ea0fea28a883661eb59bf6cf516e88cf7f623341218821dc2c6460206c07443","KTextEditor patch digest")
req(kp.get("expected_source_sha256")=="2d09ae4a05f7c0934a9a181998ff7be151eec0b78642103ddb617c56bc3bf538","KTextEditor patched source digest")

pu=c["nodes"]["purpose"]
req(pu.get("package_version_candidate")==VERS["purpose"],"Purpose revision")
rels=pu.get("source_build_relation_overrides",[])
req(any(x.get("action")=="ensure" and x.get("relation")=="kio6 (>= 6.30.0~) <!nocheck>" for x in rels),"Purpose KIO worker runtime provider")
prr=pu.get("rules_text_replacements",[])
req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tQT_QPA_PLATFORM=offscreen dh_auto_test" and x.get("expected_count")==1 for x in prr),"Purpose headless Qt test environment")

kded=support.get("nodes",{}).get("kded",{})
pev=kded.get("pass_evidence",{})
expected_kded={"version":"6.30.0-0supralinux1","workflow_run":35721085911,"artifact_id":10691372157,"artifact_sha256":"ff8756cf6efb4746568fa032cfb17cdf5c6b47bc31f532130936536aecb7c5c9","expected_binary_packages":["kded6","kded6-dev"],"dev_package":"kded6-dev","provenance":"tier3-support-level1-pass"}
req(kded.get("state")=="PASS" and kded.get("downstream_eligible") is True,"KDED support PASS")
req(pev.get("workflow_run")==35721085911 and pev.get("artifact_id")==10691372157 and pev.get("artifact_sha256")==expected_kded["artifact_sha256"],"KDED support evidence")
req(l3.get("support_predecessors",{}).get("kded")==expected_kded,"Level3 exact KDED support pin")
for x in T:
    req(l3["nodes"][x].get("support_input_ids")==["breeze-icons","kdoctools","kded"],x+": complete support solver closure")

req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval contract")
req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval materialization")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 remediation definition: PASS")
print("source-rematerialization=ktexteditor,purpose; candidate=6.30.0-0supralinux2")
print("package-execution-authorized=false")
