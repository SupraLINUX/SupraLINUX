# SPDX-License-Identifier: CC0-1.0
from pathlib import Path
import json,os,resource,signal,subprocess,tempfile,sqlite3,sys

assert len(sys.argv)==3,'Provide client and artifact output directory'
client=Path(sys.argv[1]).resolve();folder=Path(sys.argv[2]);folder.mkdir(parents=True,exist_ok=True)
daemons=[p for p in subprocess.check_output(['dpkg','-L','kactivitymanagerd'],text=True).splitlines() if p.endswith('/libexec/kactivitymanagerd')];assert len(daemons)==1;daemon=daemons[0]
with tempfile.TemporaryDirectory(prefix='supralinux-kactivitymanagerd-') as temporary:
    home=Path(temporary)
    for name in ['runtime','config','data','cache','state','empty-config','empty-data']:
        (home/name).mkdir(mode=0o700)
    bus=home/'private-dbus.conf'
    bus.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(home/'runtime')+'</listen><policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
    env=os.environ.copy()
    for key in ['DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER']:
        env.pop(key,None)
    env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_CONFIG_DIRS=str(home/'empty-config'),XDG_DATA_HOME=str(home/'data'),XDG_DATA_DIRS='/usr/local/share:/usr/share',XDG_CACHE_HOME=str(home/'cache'),XDG_STATE_HOME=str(home/'state'),XDG_RUNTIME_DIR=str(home/'runtime'),QT_QPA_PLATFORM='offscreen',LC_ALL='C.UTF-8')
    code='''set -Eeuo pipefail
daemon_pid=''
stop_daemon() { if [[ -n "$daemon_pid" ]]; then kill "$daemon_pid" 2>/dev/null || true; wait "$daemon_pid" 2>/dev/null || true; daemon_pid=''; fi; }
trap stop_daemon EXIT
"$2" --offline
"$1" > "$HOME/first-daemon.log" 2>&1 & daemon_pid=$!
"$2"
stop_daemon
"$1" > "$HOME/second-daemon.log" 2>&1 & daemon_pid=$!
"$2" --verify-persistence
stop_daemon
'''
    def limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    process=subprocess.Popen(['dbus-run-session','--config-file='+str(bus),'--','bash','-c',code,'fixture',daemon,str(client)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True,preexec_fn=limits)
    try:output,_=process.communicate(timeout=65)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);output,_=process.communicate();raise RuntimeError(output)
    (folder/'ubuntu-local-output.txt').write_text(output)
    for name in ['first-daemon.log','second-daemon.log']:
        if (home/name).exists():(folder/name).write_bytes((home/name).read_bytes())
    print(output,flush=True)
    if process.returncode:
        for name in ['first-daemon.log','second-daemon.log']:
            if (home/name).exists():print((home/name).read_text(),flush=True)
    assert process.returncode==0,process.returncode
    database=home/'data/kactivitymanagerd/resources/database';assert database.is_file()
    with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert connection.execute('SELECT count(*) FROM ResourceLink WHERE initiatingAgent=?',('org.supralinux.private-test',)).fetchone()==(0,)
        schema=connection.execute("SELECT value FROM SchemaInfo WHERE key='version'").fetchone();assert schema==('2015.02.09',)
    (folder/'sqlite-result.json').write_text(json.dumps({'state':'PASS','scope':'actual private daemon SQLite integrity, schema and fixture-link cleanup','schema':schema[0]},indent=2)+'\n')
print('Owned private daemon and bus reaped; private configuration removed')
