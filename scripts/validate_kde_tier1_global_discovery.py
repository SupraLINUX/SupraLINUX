#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fail(m): raise SystemExit(m)
def load(p):
 try:return json.loads(p.read_text())
 except Exception as e: fail(f"cannot parse {p.relative_to(ROOT)}: {e}")
c=load(ROOT/'manifests/kde-tier1-global-discovery.json'); t=load(ROOT/'manifests/kde-frameworks-tier1.json')
if c.get('schema')!=1 or c.get('strategy')!='dag-global-discovery': fail('global discovery identity mismatch')
if c.get('authority')!='kde-upstream' or c.get('provider_platform')!='ubuntu-resolute': fail('authority/provider separation regressed')
required_policy={'build_every_runnable_node_per_topological_level':True,'parallelize_independent_nodes':True,'fail_fast':False,'continue_after_independent_failures':True,'blocked_is_not_fail':True,'only_pass_artifacts_feed_dependents':True,'preserve_every_real_attempt':True,'rerun_affected_nodes_after_remediation':True,'repeat_full_campaign_after_remediation_set':True}
if c.get('policy')!=required_policy: fail('global discovery policy changed')
nodes=c.get('nodes',{}); lanes=c.get('lanes',{}); expected={'kconfig','ki18n','sonnet','kirigami','kquickcharts','kuserfeedback','prison'}
if set(nodes)!=expected: fail(f"unexpected post-Batch8 discovery set: {sorted(set(nodes)^expected)}")
for node,meta in nodes.items():
 if meta.get('readiness') not in {'runnable','lane-pending','dependency-blocked'}: fail(f'{node}: invalid readiness')
 lane=meta.get('lane')
 if lane not in lanes or node not in lanes[lane].get('nodes',[]): fail(f'{node}: lane membership mismatch')
lane_members=[n for m in lanes.values() for n in m.get('nodes',[])]
if len(lane_members)!=len(set(lane_members)) or set(lane_members)!=expected: fail('lane membership must cover each discovery node exactly once')
state_by_id={n['id']:n.get('state') for n in t.get('nodes',[])}; nonpass={n for n,s in state_by_id.items() if s!='PASS'}; passed={n for n,s in state_by_id.items() if s=='PASS'}
if nonpass!=expected or len(passed)!=22 or len(nonpass)!=7: fail(f'canonical promotion mismatch PASS={len(passed)} non-PASS={len(nonpass)}')
s=c.get('promoted_snapshot',{})
if (s.get('pass'),s.get('pending'),s.get('current_fail'),s.get('blocked'))!=(22,7,0,0): fail('promoted snapshot mismatch')
ready={n for n,m in nodes.items() if m['readiness']=='runnable'}; blocked={n for n,m in nodes.items() if m['readiness']=='dependency-blocked'}; pending={n for n,m in nodes.items() if m['readiness']=='lane-pending'}
if ready!={'kconfig','ki18n','sonnet'}: fail(f'multi-ABI runnable set mismatch: {sorted(ready)}')
if blocked: fail(f'no discovery node should be dependency-blocked: {sorted(blocked)}')
if pending!={'kirigami','kquickcharts','kuserfeedback','prison'}: fail(f'lane-pending set mismatch: {sorted(pending)}')
ma=lanes['multi-abi']
if ma.get('status')!='implementation-ready' or ma.get('runner')!='scripts/run-kde-tier1-package-batch9-preflight.sh' or ma.get('workflow')!='.github/workflows/kde-tier1-package-batch9.yml': fail('Batch 9 multi-ABI lane implementation contract mismatch')
for lane in ('qml-multisurface','multi-surface-optional'):
 if lanes[lane].get('status')!='implementation-pending': fail(f'{lane}: must remain implementation-pending')
for lane,runner in [('single-abi-python','scripts/run-kde-tier1-package-batch7-preflight.sh'),('local-predecessor','scripts/run-kde-tier1-package-batch8-preflight.sh')]:
 if lanes[lane].get('status')!='completed' or lanes[lane].get('nodes')!=[] or lanes[lane].get('runner')!=runner: fail(f'{lane}: completed lane contract mismatch')
print('KDE Tier 1 global discovery policy: PASS')
print('promoted PASS=22; discovery nodes=7; runnable=3; lane-pending=4; dependency-blocked=0')
