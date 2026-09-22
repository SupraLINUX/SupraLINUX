#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"manifests/kde-tier3-package-contracts.json"
DEPS=ROOT/"manifests/kde-frameworks-tier3-dependencies.json"
ART=Path(os.environ.get("PACKAGING_TREE_ARTIFACT_DIR",""))
EVIDENCE=ROOT/"evidence/kde-tier3-contract-review"

REL_FIELDS=("Depends","Pre-Depends","Recommends","Suggests","Provides","Replaces","Breaks","Conflicts","Multi-Arch")
PROMOTED_FIELDS=("source_package","source_version","tree_sha256","file_count","control_summary_sha256","packaging_files_sha256")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dep_atoms(raw):
    if not raw:
        return []
    out=[]
    for group in raw.split(","):
        alts=[]
        for alt in group.split("|"):
            alt=alt.strip()
            if not alt or alt.startswith("${"):
                continue
            m=re.match(r"([A-Za-z0-9+_.:-]+)",alt)
            if m:
                alts.append(m.group(1))
        if alts:
            out.append("|".join(alts))
    return sorted(set(out))

def load_json(path):
    return json.loads(Path(path).read_text())

def resolve_artifact_root(base):
    direct=base/"index.json"
    if direct.is_file() and (base/"result.json").is_file():
        return base
    candidates=sorted({
        p.parent
        for p in base.rglob("index.json")
        if (p.parent/"result.json").is_file() and (p.parent/"trees").is_dir()
    })
    if len(candidates)!=1:
        raise SystemExit(f"expected exactly one packaging-tree artifact root under {base}, got {len(candidates)}")
    return candidates[0]

def source_para(paras):
    xs=[p for p in paras if "Source" in p]
    if len(xs)!=1:
        raise SystemExit(f"expected exactly one source paragraph, got {len(xs)}")
    return xs[0]

def binary_map(paras):
    return {p["Package"]:p for p in paras if "Package" in p}

def file_map(rows):
    return {x["path"]:x["sha256"] for x in rows}

def subset_paths(paths,suffixes):
    return sorted(p for p in paths if p.endswith(suffixes))

def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    if not ART or not ART.is_dir():
        raise SystemExit("PACKAGING_TREE_ARTIFACT_DIR missing or invalid")
    art=resolve_artifact_root(ART)
    m=load_json(MANIFEST)
    deps=load_json(DEPS)
    capture=m.get("packaging_tree_capture",{})
    if capture.get("status")!="PASS":
        raise SystemExit("packaging-tree capture must be PASS")
    promoted=m.get("packaging_trees",{})
    selected=m.get("selected_nodes",[])
    if set(promoted)!=set(selected) or len(selected)!=20:
        raise SystemExit("promoted packaging-tree node set mismatch")

    index_path=art/"index.json"
    result_path=art/"result.json"
    if not index_path.is_file() or not result_path.is_file():
        raise SystemExit("packaging-tree artifact missing index/result")
    expected_index=capture.get("evidence",{}).get("index_sha256")
    actual_index=sha(index_path)
    if actual_index!=expected_index:
        raise SystemExit(f"packaging-tree index SHA drift: {actual_index} != {expected_index}")
    result=load_json(result_path)
    if result.get("result")!="PASS" or result.get("nodes")!=20 or result.get("sides")!=40 or result.get("index_sha256")!=actual_index:
        raise SystemExit("packaging-tree artifact result contract mismatch")
    index=load_json(index_path)
    if set(index.get("nodes",{}))!=set(selected):
        raise SystemExit("artifact index node set mismatch")

    review={
      "schema":1,
      "authority":False,
      "decision_authority":"supralinux",
      "source_authority":"kde-upstream",
      "claim":"package-contract-delta-review-evidence",
      "package_state_effect":"none",
      "packaging_tree_index_sha256":actual_index,
      "nodes":{},
    }
    summary={
      "nodes":20,
      "binary_identity_equal":0,
      "build_depends_delta":0,
      "binary_relation_delta":0,
      "rules_delta":0,
      "install_delta":0,
      "symbols_delta":0,
      "maintscripts_delta":0,
      "review_required":0,
    }
    tsv=["node\tbinary-identity\tbuild-dep-delta\tbinary-relation-delta\trules-delta\tinstall-delta\tsymbols-delta\tmaintscripts-delta\treview-required"]

    for node in selected:
        artifact_node=index["nodes"][node]
        for side in ("ubuntu","debian"):
            if side not in artifact_node:
                raise SystemExit(f"{node}: artifact missing {side}")
            p=promoted[node][side]
            a=artifact_node[side]
            for key in PROMOTED_FIELDS:
                if p.get(key)!=a.get(key):
                    raise SystemExit(f"{node}/{side}: promoted {key} drift")
        ubase=art/"trees"/"ubuntu"/node
        dbase=art/"trees"/"debian"/node
        uctrl=load_json(ubase/"control-summary.json")
        dctrl=load_json(dbase/"control-summary.json")
        upkgs=binary_map(uctrl); dpkgs=binary_map(dctrl)
        if set(upkgs)!=set(dpkgs):
            raise SystemExit(f"{node}: Ubuntu/Debian binary identity divergence")
        binary_identity=True
        summary["binary_identity_equal"]+=1

        usrc=source_para(uctrl); dsrc=source_para(dctrl)
        ub=set(dep_atoms(usrc.get("Build-Depends",""))); db=set(dep_atoms(dsrc.get("Build-Depends","")))
        ubi=set(dep_atoms(usrc.get("Build-Depends-Indep",""))); dbi=set(dep_atoms(dsrc.get("Build-Depends-Indep","")))
        build_delta={
          "build_depends":{"added_in_debian":sorted(db-ub),"removed_in_debian":sorted(ub-db),"ubuntu_raw":usrc.get("Build-Depends"),"debian_raw":dsrc.get("Build-Depends")},
          "build_depends_indep":{"added_in_debian":sorted(dbi-ubi),"removed_in_debian":sorted(ubi-dbi),"ubuntu_raw":usrc.get("Build-Depends-Indep"),"debian_raw":dsrc.get("Build-Depends-Indep")},
        }
        has_build_delta=bool((db^ub) or (dbi^ubi))
        summary["build_depends_delta"]+=int(has_build_delta)

        rel=[]
        for pkg in sorted(upkgs):
            for field in REL_FIELDS:
                uv=upkgs[pkg].get(field); dv=dpkgs[pkg].get(field)
                if uv!=dv:
                    rel.append({"package":pkg,"field":field,"ubuntu":uv,"debian":dv,
                                "ubuntu_atoms":dep_atoms(uv) if field!="Multi-Arch" else [],
                                "debian_atoms":dep_atoms(dv) if field!="Multi-Arch" else []})
        has_rel=bool(rel); summary["binary_relation_delta"]+=int(has_rel)

        upfiles=load_json(ubase/"packaging-files.json"); dpfiles=load_json(dbase/"packaging-files.json")
        um=file_map(upfiles); dm=file_map(dpfiles)
        all_paths=set(um)|set(dm)
        added=sorted(set(dm)-set(um)); removed=sorted(set(um)-set(dm)); changed=sorted(p for p in set(um)&set(dm) if um[p]!=dm[p])
        packaging_delta={"added_in_debian":added,"removed_in_debian":removed,"changed":changed}

        urules=art/"trees"/"ubuntu"/node/"debian"/"rules"
        drules=art/"trees"/"debian"/node/"debian"/"rules"
        rules_delta=(sha(urules)!=sha(drules))
        summary["rules_delta"]+=int(rules_delta)

        install_paths=subset_paths(all_paths,(".install",))
        symbol_paths=subset_paths(all_paths,(".symbols",))
        maint_paths=subset_paths(all_paths,(".maintscript",".postinst",".postrm",".preinst",".prerm",".triggers"))
        install_delta=any(p in added or p in removed or p in changed for p in install_paths)
        symbols_delta=any(p in added or p in removed or p in changed for p in symbol_paths)
        maint_delta=any(p in added or p in removed or p in changed for p in maint_paths)
        summary["install_delta"]+=int(install_delta)
        summary["symbols_delta"]+=int(symbols_delta)
        summary["maintscripts_delta"]+=int(maint_delta)

        upstream=deps.get("nodes",{}).get(node,{})
        review_required=has_build_delta or has_rel or rules_delta or install_delta or symbols_delta or maint_delta
        summary["review_required"]+=int(review_required)
        review["nodes"][node]={
          "technical_references":{
            "ubuntu":promoted[node]["ubuntu"],
            "debian":promoted[node]["debian"],
          },
          "binary_identity_equal":binary_identity,
          "build_dependency_delta":build_delta,
          "binary_relation_delta":rel,
          "packaging_file_delta":packaging_delta,
          "rules":{
            "ubuntu_sha256":sha(urules),
            "debian_sha256":sha(drules),
            "changed":rules_delta,
          },
          "install_manifests":{"paths":install_paths,"changed":install_delta},
          "symbols":{"paths":symbol_paths,"changed":symbols_delta},
          "maintscripts":{"paths":maint_paths,"changed":maint_delta},
          "kde_upstream_dependency_contract":{
            "frameworks":upstream.get("frameworks",{}),
            "tier3_edges":upstream.get("tier3_edges",{}),
          },
          "review_required":review_required,
          "contract_decision":"pending-explicit-review",
        }
        tsv.append("\t".join([
          node,"PASS" if binary_identity else "FAIL",
          str(has_build_delta).lower(),str(has_rel).lower(),str(rules_delta).lower(),
          str(install_delta).lower(),str(symbols_delta).lower(),str(maint_delta).lower(),
          str(review_required).lower()
        ]))

    review["summary"]=summary
    review_path=EVIDENCE/"review.json"
    review_path.write_text(json.dumps(review,indent=2,sort_keys=True)+"\n")
    (EVIDENCE/"summary.tsv").write_text("\n".join(tsv)+"\n")
    result={
      "result":"PASS","stage":"complete","exit_code":0,
      "claim":"package-contract-delta-review-evidence","authoritative":False,
      "decision_authority":"supralinux","package_state_effect":"none",
      "nodes":20,"review_required":summary["review_required"],
      "review_sha256":sha(review_path),
      "packaging_tree_index_sha256":actual_index,
    }
    (EVIDENCE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    print("KDE Tier 3 package-contract review capture: PASS")
    print("Differences require explicit contract decisions; no package state changed.")

if __name__=="__main__":
    try:
        main()
    except BaseException as exc:
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        result=EVIDENCE/"result.json"
        if not result.exists():
            result.write_text(json.dumps({
              "result":"INFRA",
              "stage":"contract-review-capture",
              "exit_code":1,
              "claim":"package-contract-delta-review-evidence",
              "authoritative":False,
              "decision_authority":"supralinux",
              "package_state_effect":"none",
              "error":str(exc),
            },indent=2)+"\n")
        raise
