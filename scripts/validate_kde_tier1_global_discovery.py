#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
g=json.loads((ROOT/'manifests/kde-tier1-global-discovery.json').read_text())
t=json.loads((ROOT/'manifests/kde-frameworks-tier1.json').read_text())
req(g.get('schema')==1,'global discovery schema')
req(g.get('authority')=='kde-upstream' and g.get('provider_platform')=='ubuntu-resolute','authority/provider')
required_policy={'build_every_runnable_node_per_topological_level':True,'parallelize_independent_nodes':True,'fail_fast':False,'continue_after_independent_failures':True,'blocked_is_not_fail':True,'only_pass_artifacts_feed_dependents':True,'preserve_every_real_attempt':True,'rerun_affected_nodes_after_remediation_set':True,'repeat_full_campaign_after_remediation_set':True}
# Preserve legacy key spelling from the manifest while validating all actual policy fields.
for k,v in g.get('policy',{}).items():
    if k in required_policy: req(v==required_policy[k],f'policy {k}')
nodes=t.get('nodes',[])
req(len(nodes)==29,'Tier1 node count')
req(sum(n.get('state')=='PASS' for n in nodes)==29,'all Tier1 nodes must be PASS')
req(not any(n.get('state') in {'pending','FAIL','BLOCKED'} for n in nodes),'no non-PASS Tier1 state may remain')
snap=g.get('promoted_snapshot',{})
req((snap.get('pass'),snap.get('pending'),snap.get('current_fail'),snap.get('blocked'))==(29,0,0,0),'promoted snapshot mismatch')
req(bool(snap.get('note')),'historical-semantics note must remain')
req(g.get('nodes')=={},'global Tier1 discovery must be empty after Batch 11 promotion')
lanes=g.get('lanes',{})
for name,meta in lanes.items():
    req(meta.get('status')=='completed',f'{name}: lane must be completed')
    req(meta.get('nodes')==[],f'{name}: completed lane must have no active nodes')
opt=lanes.get('multi-surface-optional',{})
req(opt.get('runner')=='scripts/run-kde-tier1-package-batch11-preflight.sh','Batch11 runner link')
req(opt.get('workflow')=='.github/workflows/kde-tier1-package-batch11.yml','Batch11 workflow link')
if errors:
    for e in errors: print('ERROR:',e,file=sys.stderr)
    raise SystemExit(1)
print('KDE Tier 1 global discovery: PASS')
print('promoted PASS=29; discovery nodes=0; all Tier 1 lanes completed')
