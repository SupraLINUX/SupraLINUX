"""Seal local review inputs and prove byte restoration without a remote service."""
import argparse,hashlib,json,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--scope',required=True);p.add_argument('--include',type=Path,action='append',required=True);a=p.parse_args()
root=Path.cwd().resolve();out=a.output.resolve();assert out.is_relative_to(root/'.artifacts') and not out.exists();out.mkdir(parents=True)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
files={}
for supplied in a.include:
 path=supplied.absolute();assert path.exists() and not path.is_symlink()
 for item in ([path] if path.is_file() else sorted(path.rglob('*'))):
  if not item.is_file() or item.is_symlink():continue
  name=str(item.relative_to(root)) if item.is_relative_to(root) else 'external/'+str(item).removeprefix('/')
  assert name not in files;files[name]=item
archive=out/'inputs.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
 for name,item in files.items():z.write(item,name)
restore=out/'empty-offline-restore';restore.mkdir()
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None;assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist());z.extractall(restore)
for name,item in files.items():assert sha(restore/name)==sha(item)
index={'schema':1,'state':'PASS','scope':a.scope,'archive_path':str(archive.relative_to(root)),'archive_sha256':sha(archive),'files':{name:{'sha256':sha(item),'size':item.stat().st_size} for name,item in files.items()},'empty_offline_byte_restore_verified':True,'requires_github_for_restore':False,'off_host_backup_verified':False,'candidate_execution':'NOT RUN','package_attempt_consumed':False}
(out/'index.json').write_text(json.dumps(index,indent=2)+'\n');print('Independent local review input byte retention and empty restore PASS',len(files))
