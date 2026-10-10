from pathlib import Path
import os,resource,select,signal,subprocess,tempfile,json

src=Path(__file__).resolve().parent
plugin='/usr/lib/x86_64-linux-gnu/qt6/plugins/plasma/kcms/systemsettings_qwidgets/kcm_kgamma.so'
observations=[]
server=subprocess.Popen(['Xvfb','-displayfd','1','-nolisten','tcp','-noreset','-screen','0','1024x768x24'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
try:
    assert select.select([server.stdout],[],[],10)[0],'Private Xvfb did not become ready'
    display=server.stdout.readline().strip();assert display.isdigit(),display
    for case in ['functional','unsupported']:
        with tempfile.TemporaryDirectory(prefix='supra-kgamma-'+case+'-') as directory:
            home=Path(directory);runtime=home/'runtime';runtime.mkdir(mode=0o700)
            bus_config=home/'private-dbus.conf'
            bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
            env=os.environ.copy()
            for key in ['DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','WAYLAND_DISPLAY']:env.pop(key,None)
            env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_CONFIG_DIRS=str(home/'empty-config'),XDG_DATA_HOME=str(home/'data'),XDG_CACHE_HOME=str(home/'cache'),XDG_RUNTIME_DIR=str(runtime),DISPLAY=':'+display,QT_QPA_PLATFORM='xcb',LC_ALL='C.UTF-8',LANGUAGE='C',LD_PRELOAD=str(src/'gamma-shim.so'))
            if case=='unsupported':env['SUPRA_GAMMA_UNSUPPORTED']='1'
            else:env.pop('SUPRA_GAMMA_UNSUPPORTED',None)
            def private_limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            proc=subprocess.Popen(['dbus-run-session','--config-file='+str(bus_config),'--',str(src/'ubuntu-kgamma-client'),plugin],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True,preexec_fn=private_limits)
            try:output,_=proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);output,_=proc.communicate();raise RuntimeError(output)
            (src/('ubuntu-local-'+case+'-output.txt')).write_text(output)
            print(case,output,flush=True)
            observations.append({'case':case,'wrapper_exit_code':proc.returncode,'log':'ubuntu-local-'+case+'-output.txt'})
            if case=='functional':assert proc.returncode==0,proc.returncode
            else:assert proc.returncode in [-11,139],proc.returncode
finally:
    server.terminate()
    try:server.communicate(timeout=5)
    except subprocess.TimeoutExpired:server.kill();server.communicate()
(src/'observations.json').write_text(json.dumps({'kind':'local-ubuntu-module-diagnosis','authoritative':False,'package_attempt_consumed':False,'package_quality_certification':False,'candidate_execution_started':False,'observations':observations,'private_xvfb_reaped':server.poll() is not None},indent=2)+'\n')
print('Private Xvfb and D-Bus sessions finished; no display process retained')
