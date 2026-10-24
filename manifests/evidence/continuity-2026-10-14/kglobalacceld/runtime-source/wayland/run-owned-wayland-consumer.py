#!/usr/bin/env python3
"""Run a reviewed virtual compositor and consumer in an owned guest fixture."""
import argparse
import json
import os
import select
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--config',type=Path,required=True)
p.add_argument('--phase',required=True)
p.add_argument('--compositor',type=Path,required=True)
p.add_argument('--consumer',type=Path)
p.add_argument('--consumer-probe',action='store_true')
p.add_argument('--consumer-desktop-file',type=Path)
p.add_argument('--service-cache-builder',type=Path)
p.add_argument('--dbus-daemon',type=Path,required=True)
p.add_argument('--gdbus',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a = p.parse_args()
root = Path(__file__).resolve().parent
for path in [a.config,a.compositor,a.dbus_daemon,a.gdbus,
             *[x for x in (a.consumer,a.consumer_desktop_file,a.service_cache_builder) if x]]:
    assert path.is_file() and path.resolve().is_relative_to(root)
assert sorted(p.name for p in Path('/sys/class/net').iterdir()) == ['lo']
assert subprocess.check_output(['systemd-detect-virt'],text=True).strip()=='kvm'
a.output.mkdir(parents=True,exist_ok=False)
config = json.loads(a.config.read_text())['phases'][a.phase]
result = {'state':'FAIL','scope':'Owned virtual KWin diagnostic in zero-NIC KVM only',
          'canonical_effect':'none','package_attempt_consumed':False}
processes=[]
def stop_signal(signum,frame):
    raise RuntimeError('Owned virtual compositor interrupted: '+str(signum))
signal.signal(signal.SIGTERM,stop_signal)
signal.signal(signal.SIGINT,stop_signal)
def start(command,**options):
    process=subprocess.Popen(command,env=environment,start_new_session=True,**options)
    processes.append(process)
    return process
with tempfile.TemporaryDirectory(prefix='supra-wayland-private-') as temporary:
    state=Path(temporary)
    environment=os.environ.copy()
    for key in ['DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER','DBUS_SESSION_BUS_ADDRESS',
                'DBUS_SYSTEM_BUS_ADDRESS','DBUS_STARTER_ADDRESS','DBUS_STARTER_BUS_TYPE',
                'LD_PRELOAD','LD_LIBRARY_PATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
                'QML_IMPORT_PATH','QML2_IMPORT_PATH','KWIN_WAYLAND_NO_PERMISSION_CHECKS']:
        environment.pop(key,None)
    for key,directory in [('HOME','home'),('XDG_RUNTIME_DIR','runtime'),('XDG_CONFIG_HOME','config'),
                          ('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_CONFIG_DIRS','empty-config')]:
        path=state/directory;path.mkdir(mode=0o700);environment[key]=str(path)
    for key,values in config.items():
        assert key in {'LD_LIBRARY_PATH','QT_PLUGIN_PATH','LIBGL_DRIVERS_PATH',
                       '__EGL_VENDOR_LIBRARY_FILENAMES','QML_IMPORT_PATH','QML2_IMPORT_PATH',
                       'XDG_DATA_DIRS','XKB_CONFIG_ROOT'}
        for value in values:
            assert Path(value).resolve().is_relative_to(root) and Path(value).exists(),(key,value)
        environment[key]=':'.join(values)
    environment.update(LD_BIND_NOW='1',LD_DEBUG='libs',LIBGL_ALWAYS_SOFTWARE='1',
                       KWIN_COMPOSE='Q',QT_QUICK_BACKEND='software',QT_QPA_PLATFORM='offscreen',
                       QT_LOGGING_RULES='kwin_core.debug=true;KWIN_UTILS.debug=true',
                       XDG_SESSION_TYPE='wayland',DBUS_SYSTEM_BUS_ADDRESS=f'unix:path={state}/no-system-bus',LC_ALL='C.UTF-8')
    assert 'KWIN_WAYLAND_NO_PERMISSION_CHECKS' not in environment
    result['kwin_permission_override_absent']=True
    bus_config=state/'bus.conf'
    bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(state)
        +'</listen><auth>EXTERNAL</auth><policy context="default">'
        +'<allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/>'
        +'</policy></busconfig>')
    with (a.output/'bus-stderr.log').open('w') as berr, \
         (a.output/'compositor-stdout.log').open('w') as kout,(a.output/'compositor-stderr.log').open('w') as kerr, \
         (a.output/'consumer-stdout.log').open('w') as cout,(a.output/'consumer-stderr.log').open('w') as cerr:
        try:
            bus=start([str(a.dbus_daemon),'--nofork','--print-address=1','--config-file='+str(bus_config)],
                      stdout=subprocess.PIPE,stderr=berr,text=True)
            assert select.select([bus.stdout],[],[],10)[0], 'Private bus address deadline'
            address=bus.stdout.readline().strip();assert address.startswith('unix:')
            environment['DBUS_SESSION_BUS_ADDRESS']=address
            if a.consumer_desktop_file:
                assert a.consumer and a.service_cache_builder
                desktop=a.consumer_desktop_file.read_text()
                assert 'Exec='+str(a.consumer.resolve())+'\n' in desktop
                assert 'X-KDE-Wayland-Interfaces=org_kde_kwin_fake_input\n' in desktop
                applications=state/'data/applications';applications.mkdir()
                target=applications/a.consumer_desktop_file.name
                shutil.copyfile(a.consumer_desktop_file,target)
                with (a.output/'service-cache-stdout.log').open('w') as sout, (a.output/'service-cache-stderr.log').open('w') as serr:
                    cache=subprocess.run([str(a.service_cache_builder),'--noincremental'],env=environment,
                                         stdout=sout,stderr=serr,timeout=20)
                assert cache.returncode==0,'Owned desktop service cache construction failed'
                result['owned_exact_consumer_permission_declared']=True
            socket='supra-owned-virtual-wayland'
            compositor=start([str(a.compositor),'--virtual','--socket',socket,'--no-lockscreen',
                              '--width','1024','--height','768'],stdout=kout,stderr=kerr)
            deadline=time.monotonic()+30
            while True:
                assert compositor.poll() is None,'Original virtual KWin exited before readiness'
                ping=subprocess.run([str(a.gdbus),'call','--session','--dest','org.kde.KWin',
                    '--object-path','/KWin','--method','org.freedesktop.DBus.Peer.Ping'],
                    env=environment,capture_output=True,timeout=2)
                (a.output/'last-readiness.log').write_bytes(ping.stdout+ping.stderr)
                if ping.returncode==0 and (state/'runtime'/socket).exists():
                    break
                assert time.monotonic()<deadline,'Original virtual KWin readiness deadline'
                time.sleep(0.1)
            result['virtual_compositor_bus_socket_ready']='PASS'
            if a.consumer:
                environment.update(QT_QPA_PLATFORM='wayland',WAYLAND_DISPLAY=socket,SUPRA_PRIVATE_WAYLAND_SOCKET=socket)
                consumer=start([str(a.consumer),*(['--probe'] if a.consumer_probe else [])],stdout=cout,stderr=cerr)
                code=consumer.wait(timeout=45);result['consumer_exit_code']=code
                assert code==0,'Owned Wayland consumer assertions failed'
            else:
                result['consumer_execution']='NOT RUN; small compositor mechanism certification'
            assert compositor.poll() is None,'Virtual compositor died during consumer'
            result['state']='PASS'
        except Exception as error:
            result['error']=str(error)
        finally:
            signal.signal(signal.SIGTERM,signal.SIG_IGN)
            for process in reversed(processes):
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                if process.stdout:process.stdout.close()
            result['owned_processes_reaped']=all(p.poll() is not None for p in processes)
result['owned_temporary_directory_removed']=not state.exists()
(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['state']=='PASS' and result['owned_processes_reaped'] and result['owned_temporary_directory_removed'] else 1)
