#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
c=load('manifests/kde-tier1-package-campaign-batch11.json')
a=load('manifests/kde-tier1-package-batch11-attempts.json')
t=load('manifests/kde-frameworks-tier1.json')
d=load('manifests/kde-dag.json')
g=load('manifests/kde-tier1-global-discovery.json')
req(c.get('schema')==2 and c.get('batch')=='tier1-batch-11' and c.get('lane')=='multi-surface-optional','Batch11 identity')
req(c.get('state')=='PASS','Batch11 campaign must be PASS')
req(c.get('canonical_snapshot',{}).get('tier1')=='27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED after Batch 10 canonical promotion','historical pre-Batch11 snapshot')
req(c.get('canonical_promotion')=={'status':'promoted','tier1':'29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED','dag_nodes':['kuserfeedback','prison']},'Batch11 canonical promotion')
incidents=c.get('promotion_validation_incidents',[])
req(len(incidents)==1,'Batch11 promotion validation incident ledger must contain exactly one incident')
if incidents:
    inc=incidents[0]
    req(inc.get('workflow_run')==35491700804 and inc.get('job_id')==106027643479 and inc.get('commit')=='4385e7193d75bf158b7a2798d644d8c3f726671e','Batch11 promotion validation incident identity mismatch')
    req(inc.get('classification')=='INFRA' and inc.get('package_state_effect')=='none' and inc.get('package_attempted') is False,'Batch11 promotion validation incident semantics mismatch')
    req(inc.get('failed_gate')=='validate_kde_tier1_packaging_reference.py','Batch11 promotion validation failed gate mismatch')
pre=c.get('promotion_precheck',{})
req(pre.get('repository_policy')=={'workflow_run':35489771248,'job_id':106022596719,'result':'PASS'},'promotion Repository Policy evidence')
req(pre.get('pr_ci')=={'workflow_run':35489771315,'commit':'69d271891f96f75ada404623611ffa42bc061090','result':'PASS'},'promotion PR CI evidence')
expected={
 'kuserfeedback':('6.30.0-0supralinux5',35489771315,106022610412,10597923863,'0a057d591a198f74cf6eee24d3b1ef4355f2a0d6073d48de8e220ac37f0a38b7','8b5518bea1704ffb9830b4d9a3259e2655ca69efb6dff108b9a9709e66d87e39','15/15 PASS',['libKF6UserFeedbackCore.so.6','libKF6UserFeedbackWidgets.so.6']),
 'prison':('6.30.0-0supralinux1',35488901554,106020266290,10597829797,'f0074c8da29cfda08018fa568fce9cabbf6fc23669416caf20c714c25ff7773f','a1ae6cb653ec18a6dba7142f4ee5acd94210076a9adba23d9d67d03ac03885e7','9/9 PASS',['libKF6Prison.so.6','libKF6PrisonScanner.so.6'])
}
tier={x['id']:x for x in t['nodes']}
for node,(ver,run,job,artifact,digest,rootfs,tests,sonames) in expected.items():
    n=c['nodes'][node]
    req(n.get('state')=='PASS' and n.get('last_result')=='PASS' and n.get('downstream_eligible') is True,f'{node}: campaign PASS')
    pe=n.get('pass_evidence',{})
    req(pe.get('workflow_run')==run and pe.get('job_id')==job and pe.get('artifact_id')==artifact and pe.get('artifact_sha256')==digest and pe.get('rootfs_sha256')==rootfs,f'{node}: pass evidence')
    req(pe.get('package_version')==ver and pe.get('tests')==tests and pe.get('lintian')=='PASS-errors' and pe.get('abi_contract')=='PASS' and pe.get('apt_check')=='PASS' and pe.get('qml_import_smoke')=='PASS' and pe.get('consumer_smoke')=='PASS' and pe.get('development_contract')=='PASS',f'{node}: final gates')
    cn=tier[node]
    req(cn.get('state')=='PASS' and cn.get('packaging',{}).get('state')=='PASS' and cn['packaging'].get('package_version')==ver and cn['packaging'].get('downstream_eligible') is True,f'{node}: Tier1 promotion')
    ev=[x for x in cn['packaging'].get('evidence',[]) if x.get('result')=='PASS']
    req(len(ev)==1 and ev[0].get('workflow_run')==run and ev[0].get('artifact_id')==artifact and ev[0].get('artifact_sha256')==digest and ev[0].get('abi_sonames')==sonames,f'{node}: canonical evidence')
    dn=d.get('nodes',{}).get(node,{})
    req(dn.get('state')=='PASS' and dn.get('package_version')==ver and dn.get('downstream_eligible') is True and dn.get('abi_sonames')==sonames,f'{node}: DAG promotion')
    req(dn.get('pass_files',{}).get('rootfs_sha256')==rootfs,f'{node}: DAG rootfs')
req(sum(x.get('state')=='PASS' for x in t['nodes'])==29 and sum(x.get('state')=='pending' for x in t['nodes'])==0,'canonical Tier1 counts')
req(len(d.get('nodes',{}))==30,'canonical DAG must contain ECM + 29 Tier1')
req(g.get('nodes')=={},'global discovery must be empty')
req(g.get('lanes',{}).get('multi-surface-optional',{}).get('status')=='completed','Batch11 lane must be completed')
req((g.get('promoted_snapshot',{}).get('pass'),g.get('promoted_snapshot',{}).get('pending'))==(29,0),'global promoted snapshot')
kuf=[x for x in a.get('real_attempts',{}).get('kuserfeedback',[]) if x.get('result')=='PASS']
pr=[x for x in a.get('real_attempts',{}).get('prison',[]) if x.get('result')=='PASS']
req(len(kuf)==1 and kuf[0].get('attempt')==5 and kuf[0].get('artifact_id')==10597923863,'KUserFeedback retained PASS attempt')
req(len(pr)==1 and pr[0].get('attempt')==1 and pr[0].get('artifact_id')==10597829797,'Prison retained PASS attempt')
doc=(ROOT/'docs/kde-tier1-package-batch11.md').read_text()
for token in ('29 PASS / 0 pending','10597923863','10597829797','15/15','9/9','does not publish packages'):
    req(token in doc,f'Batch11 doc missing {token}')
if errors:
    for e in errors: print('ERROR:',e,file=sys.stderr)
    raise SystemExit(1)
print('KDE Tier 1 Batch 11 canonical promotion: PASS')
print('Canonical Tier 1: 29 PASS / 0 pending / 0 FAIL / 0 BLOCKED')
