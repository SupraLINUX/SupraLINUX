#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, re, subprocess, sys
from collections import defaultdict, deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'build/ksq-0'; APT=OUT/'apt'; T=ROOT/'tests/kde-stack'
PV,FV='6.7.4','6.29.0'

def die(s): print('AURORA_KSQ_0_CLOSURE_FAILURE:',s,file=sys.stderr); raise SystemExit(1)
def run(a,check=True):
 p=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if check and p.returncode: die(f"{' '.join(a)}\n{p.stderr.strip()}")
 return p
def opts(p): return ['-o',f'Dir::Etc::sourcelist={APT/(p+".sources")}','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={APT/(p+"-lists")}','-o',f'Dir::State::status={APT/"empty-status"}','-o',f'Dir::Cache={APT/(p+"-cache")}','-o','APT::Architecture=amd64','-o','APT::Architectures=amd64','-o','Acquire::Languages=none']
def ac(p,*a,check=True): return run(['apt-cache',*opts(p),*a],check)
def ag(p,*a,check=True): return run(['apt-get',*opts(p),*a],check)
def paras(text):
 out=[]; d={}; cur=None
 for line in text.splitlines()+['']:
  if not line.strip():
   if d: out.append(d); d={}; cur=None
  elif line[0].isspace() and cur: d[cur]+='\n'+line.strip()
  elif ':' in line: cur,val=line.split(':',1); d[cur]=val.strip()
 return out
def snap():
 p=T/'apt-metadata-snapshot.env'
 for l in p.read_text().splitlines():
  if l.startswith('AURORA_KSQ_0_APT_SNAPSHOT='):
   v=l.split('=',1)[1].strip()
   if re.fullmatch(r'\d{8}T\d{6}Z',v): return v
 die('invalid apt-metadata-snapshot.env')
def manifest(path,ver):
 with path.open(newline='',encoding='utf-8') as f:
  r=csv.DictReader(f,delimiter='\t'); s=set()
  for x in r:
   if x['version']!=ver: die(f'mixed version in {path}: {x}')
   s.add(x['module'])
 return s
PM,FM=manifest(T/'plasma-6.7.4-sources.tsv',PV),manifest(T/'frameworks-6.29.0-sources.tsv',FV)
def overrides():
 p=T/'ksq-0-source-overrides.tsv'; out={}
 with p.open(newline='',encoding='utf-8') as f:
  r=csv.DictReader(f,delimiter='\t'); exp=['source_package','source_version','family','decision','reason']
  if r.fieldnames!=exp: die(f'bad overrides header: {r.fieldnames}')
  for x in r:
   k=(x['source_package'],x['source_version'])
   if k in out or x['decision'] not in {'backport','reject','defer'} or not x['family'] or not x['reason']: die(f'invalid override: {x}')
   out[k]=x
 return out

def splitrel(s,sep):
 out=[]; st=0; par=br=prof=0
 for i,ch in enumerate(s):
  if ch=='(': par+=1
  elif ch==')': par=max(0,par-1)
  elif ch=='[': br+=1
  elif ch==']': br=max(0,br-1)
  elif ch=='<' and not par and not br: prof+=1
  elif ch=='>' and not par and not br and prof: prof-=1
  elif ch==sep and not par and not br and not prof:
   if s[st:i].strip(): out.append(s[st:i].strip())
   st=i+1
 if s[st:].strip(): out.append(s[st:].strip())
 return out
RX=re.compile(r'^\s*([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?\s*(?:\((<<|<=|=|>=|>>)\s*([^)]+)\))?\s*(.*)$')
def alt(raw):
 m=RX.match(raw)
 if not m: die('cannot parse dependency: '+raw)
 return {'raw':raw,'pkg':m.group(1),'qual':m.group(2),'op':m.group(3),'ver':m.group(4).strip() if m.group(4) else None,'rest':m.group(5).strip()}
def archok(rest):
 m=re.search(r'\[([^\]]+)\]',rest)
 if not m:return True
 pos=[x for x in m.group(1).split() if not x.startswith('!')]; neg=[x[1:] for x in m.group(1).split() if x.startswith('!')]
 def mt(x): return subprocess.run(['dpkg-architecture','-aamd64',f'-i{x}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
 return (not pos or any(mt(x) for x in pos)) and not any(mt(x) for x in neg)
def profile(rest): return '<' in re.sub(r'\[[^\]]+\]','',rest) or '>' in re.sub(r'\[[^\]]+\]','',rest)
def vc(a,op,b): return subprocess.run(['dpkg','--compare-versions',a,op,b]).returncode==0
def satver(v,op,need): return True if not op else bool(need and vc(v,op,need))
SRC={}; POL={}; PROV={}
def src(p,n):
 k=(p,n)
 if k not in SRC:
  q=ac(p,'showsrc',n,check=False)
  if q.returncode not in (0,100): die(f'showsrc {p}/{n}: {q.stderr.strip()}')
  SRC[k]=paras(q.stdout)
 return SRC[k]
def bins(r): return {x.strip() for x in r.get('Binary','').split(',') if x.strip()}
def owns(r,b): return r.get('Package')==b or b in bins(r)
def best(rr):
 rr=list(rr)
 if not rr:return None
 b=rr[0]
 for r in rr[1:]:
  if vc(r['Version'],'>>',b['Version']): b=r
 return b
def owner(p,b):
 rr=[r for r in src(p,b) if owns(r,b)]; names={r.get('Package') for r in rr}
 return (best(rr),sorted(names)) if len(names)==1 else (None,sorted(names))
def policy(b):
 if b not in POL:
  q=ac('resolute','policy',b,check=False); v=None
  for l in q.stdout.splitlines():
   if l.strip().startswith('Candidate:'):
    x=l.split(':',1)[1].strip(); v=None if x=='(none)' else x; break
  POL[b]=v
 return POL[b]
def providers(b):
 if b in PROV:return PROV[b]
 q=ac('resolute','showpkg',b,check=False); seen=False; out=[]
 for l in q.stdout.splitlines():
  if l=='Reverse Provides:': seen=True; continue
  if seen and re.match(r'^[A-Za-z][A-Za-z ]*:$',l): break
  if seen:
   m=re.match(r'^\s*(\S+)\s+(\S+)(?:\s+\(=\s*([^)]+)\))?\s*$',l)
   if m: out.append(m.groups())
 PROV[b]=out; return out
def simple_sat(a):
 if not archok(a['rest']): return True,'-','not-applicable-amd64'
 if profile(a['rest']): return False,'-','profile'
 v=policy(a['pkg'])
 if v and satver(v,a['op'],a['ver']): return True,a['pkg'],f"{a['pkg']}={v}"
 for pp,pv,provided in providers(a['pkg']):
  cv=policy(pp)
  if not cv or (a['op'] and (not provided or not satver(provided,a['op'],a['ver']))): continue
  return True,pp,f"{pp}={cv} provides {a['pkg']}"+(f'={provided}' if provided else '')
 return False,'-','not-satisfied'
def relation_sat(g):
 aa=[alt(x) for x in splitrel(g,'|')]
 if any(profile(x['rest']) for x in aa):
  q=ag('resolute','-s','--no-remove','satisfy',g,check=False)
  return (True,'-','apt-solver-profile') if q.returncode==0 else (False,'-','profile-unsatisfied')
 for a in aa:
  ok,b,d=simple_sat(a)
  if ok:return True,b,d
 return False,'-','not-satisfied'
def deps(r):
 out=[]
 for field in ('Build-Depends','Build-Depends-Arch','Build-Depends-Indep'):
  for g in splitrel(r.get(field,'').replace('\n',' '),','):
   if g: out.append((field,g))
 return out
def mod(s): return s[4:] if s.startswith('kf6-') else s
def upmatch(v,u): return bool(re.match(rf'^{re.escape(u)}(?:$|[-+~])',v.split(':',1)[-1]))
def classify(s,v):
 m=mod(s)
 if m in PM:return ('plasma-6.7.4',m,'rebuild' if upmatch(v,PV) else 'packaging-version-mismatch')
 if m in FM:return ('frameworks-6.29.0',m,'rebuild' if upmatch(v,FV) else 'packaging-version-mismatch')
 return 'external','-','needs-decision'
def tsv(p,h,rows):
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f,delimiter='\t',lineterminator='\n'); w.writerow(h); w.writerows(rows)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--allow-unresolved',action='store_true'); a=ap.parse_args(); ss=snap(); ov=overrides()
 for p in ('resolute.sources','stonking.sources','resolute-lists','stonking-lists','empty-status'):
  if not (APT/p).exists(): die('missing prepared APT metadata: '+p)
 with (T/'aurora-package-roots.tsv').open(newline='',encoding='utf-8') as f: roots=list(csv.DictReader(f,delimiter='\t'))
 selected={}; records={}; why=defaultdict(set); q=deque(); rootsout=[]; edges=[]; ubuntu=[]; unr=[]; candidates=[]; graph=defaultdict(set)
 def unresolved(fr,fv,field,rel,reason,c='-',cv='-'): unr.append([fr,fv,field,rel,reason,c,cv])
 def select(r,fam,module,decision,reason):
  s,v=r['Package'],r['Version']; val=(v,fam,module,decision)
  if s in selected and selected[s]!=val: unresolved(s,selected[s][0],'-','-','source-selection-conflict',s,selected[s][0]+'|'+v); return False
  if s not in selected: selected[s]=val; records[s]=r; q.append(s)
  why[s].add(reason); return True
 for r in roots:
  b,act,fam=r['binary_package'],r['ksq_action'],r['candidate_family']
  if act=='rebuild':
   sr,names=owner('stonking',b)
   if not sr: unresolved('ROOT','-','-',b,'source-owner-missing-or-ambiguous',','.join(names) or '-'); rootsout.append([b,act,fam,'-','-',f'stonking@{ss}','UNRESOLVED']); continue
   df,dm,dd=classify(sr['Package'],sr['Version'])
   if df!=fam or dm!=r['upstream_module'] or dd!='rebuild': unresolved('ROOT','-','-',b,'root-packaging-mismatch',sr['Package'],sr['Version']); rootsout.append([b,act,fam,sr['Package'],sr['Version'],f'stonking@{ss}','UNRESOLVED']); continue
   select(sr,df,dm,'rebuild','root:'+b); rootsout.append([b,act,fam,sr['Package'],sr['Version'],f'stonking@{ss}','rebuild'])
  elif act in ('keep-ubuntu','compat-test'):
   v=policy(b); sr,names=owner('resolute',b)
   if not v or not sr: unresolved('ROOT','-','-',b,'missing-resolute-root',','.join(names) or '-'); rootsout.append([b,act,fam,'-','-',f'resolute@{ss}','UNRESOLVED'])
   else: rootsout.append([b,act,fam,sr['Package'],sr['Version'],f'resolute@{ss}',f'{b}={v}'])
  elif act=='defer-gear': rootsout.append([b,act,fam,'-','-','deferred','gear-review'])
  elif act=='retain': rootsout.append([b,act,fam,'supralinux-settings','-','repository','retain'])
  else: unresolved('ROOT','-','-',b,'unknown-root-action:'+act)
 done=set()
 while q:
  s=q.popleft()
  if s in done: continue
  done.add(s); sv=selected[s][0]
  for field,g in deps(records[s]):
   yes,chosen,detail=relation_sat(g)
   if yes:
    os=ovr='-'
    if chosen!='-':
     rr,names=owner('resolute',chosen)
     if rr: os,ovr=rr['Package'],rr['Version']
     elif names: unresolved(s,sv,field,g,'ambiguous-resolute-source-owner',','.join(names))
    edges.append([s,sv,field,g,chosen,os,ovr,'ubuntu-satisfied',detail]); ubuntu.append([s,field,g,chosen,os,ovr,detail]); continue
   aa=[alt(x) for x in splitrel(g,'|')]
   if any(profile(x['rest']) for x in aa): unresolved(s,sv,field,g,'unsatisfied-build-profile'); edges.append([s,sv,field,g,'-','-','-','unresolved',detail]); continue
   mapped={}
   for x in aa:
    if not archok(x['rest']): continue
    rr,names=owner('stonking',x['pkg'])
    if rr and satver(rr['Version'],x['op'],x['ver']): mapped[(rr['Package'],rr['Version'])]=(x,rr)
   if not mapped: unresolved(s,sv,field,g,'no-stonking-source-candidate'); edges.append([s,sv,field,g,'-','-','-','unresolved','no-source-candidate']); continue
   if len(mapped)>1:
    cs=','.join(f'{x}={v}' for x,v in sorted(mapped)); unresolved(s,sv,field,g,'alternative-needs-decision',cs); edges.append([s,sv,field,g,'-','-','-','unresolved',cs]); continue
   (ds,dv),(ch,dr)=next(iter(mapped.items())); df,dm,dd=classify(ds,dv)
   if dd=='packaging-version-mismatch': unresolved(s,sv,field,g,'kde-packaging-base-version-mismatch',ds,dv); candidates.append([ds,dv,df,dd,s,field,g]); edges.append([s,sv,field,g,ch['pkg'],ds,dv,'unresolved',dd]); continue
   if dd=='needs-decision':
    o=ov.get((ds,dv))
    if not o or o['decision']!='backport':
     reason='external-source-needs-decision' if not o else 'external-source-'+o['decision']; unresolved(s,sv,field,g,reason,ds,dv); candidates.append([ds,dv,'external',reason,s,field,g]); edges.append([s,sv,field,g,ch['pkg'],ds,dv,'unresolved',reason]); continue
    df,dm,dd=o['family'],'-','backport'
   if select(dr,df,dm,dd,f'{s}:{field}:{g}'): graph[s].add(ds); edges.append([s,sv,field,g,ch['pkg'],ds,dv,df,dd])
 nodes=set(selected); out={n:set() for n in nodes}; ind={n:0 for n in nodes}
 for depender,dss in graph.items():
  for d in dss:
   if d!=depender and d in nodes and depender not in out[d]: out[d].add(depender); ind[depender]+=1
 ready=deque(sorted(n for n in nodes if not ind[n])); order=[]
 while ready:
  n=ready.popleft(); order.append(n)
  for x in sorted(out[n]):
   ind[x]-=1
   if not ind[x]: ready.append(x)
 cyc=sorted(nodes-set(order))
 if cyc: unresolved('DAG','-','-','-','dependency-cycle',','.join(cyc))
 tsv(OUT/'root-source-owners.tsv',['binary_root','ksq_action','candidate_family','source_package','source_version','metadata_origin','result'],sorted(rootsout))
 tsv(OUT/'source-closure.tsv',['source_package','packaging_version','candidate_family','upstream_module','packaging_base','decision','required_by'],[[p,*selected[p][:3],f'ubuntu-stonking@{ss}:{selected[p][0]}',selected[p][3],' ; '.join(sorted(why[p]))] for p in sorted(selected)])
 tsv(OUT/'build-dependency-edges.tsv',['from_source','from_version','field','relation','chosen_binary','to_source','to_version','classification','detail'],edges)
 tsv(OUT/'ubuntu-satisfied-build-deps.tsv',['from_source','field','relation','chosen_binary','resolute_source','resolute_source_version','solver_detail'],ubuntu)
 tsv(OUT/'source-decision-candidates.tsv',['source_package','source_version','detected_family','reason','required_by_source','field','relation'],sorted(set(map(tuple,candidates))))
 tsv(OUT/'unresolved.tsv',['from_source','from_version','field','relation','reason','candidate','candidate_version'],unr)
 tsv(OUT/'build-order.tsv',['order','source_package','packaging_version','candidate_family','decision'],[[str(i),p,selected[p][0],selected[p][1],selected[p][3]] for i,p in enumerate(order,1)]+[['UNRESOLVED',p,selected[p][0],selected[p][1],selected[p][3]] for p in cyc])
 with (OUT/'selected-source-records.txt').open('w',encoding='utf-8') as f:
  for p in sorted(records):
   f.write(f"### {p} {records[p].get('Version','-')}\n")
   for k in sorted(records[p]): f.write(f'{k}: {records[p][k]}\n')
   f.write('\n')
 counts=defaultdict(int)
 for v in selected.values(): counts[v[1]]+=1
 lines=[f'AURORA_KSQ_0_APT_SNAPSHOT={ss}',f"AURORA_KSQ_0_CLOSURE_STATUS={'COMPLETE' if not unr else 'INCOMPLETE'}",f'AURORA_KSQ_0_CLOSURE_SOURCES={len(selected)}',f'AURORA_KSQ_0_CLOSURE_UNRESOLVED={len(unr)}',f'AURORA_KSQ_0_CLOSURE_BUILD_ORDERED={len(order)}']
 lines += [f"AURORA_KSQ_0_CLOSURE_{k.upper().replace('-','_').replace('.','_')}={counts[k]}" for k in sorted(counts)]
 text='\n'.join(lines)+'\n'; (OUT/'closure-status.env').write_text(text); print(text,end='')
 return 0 if a.allow_unresolved or not unr else 2
if __name__=='__main__': raise SystemExit(main())
