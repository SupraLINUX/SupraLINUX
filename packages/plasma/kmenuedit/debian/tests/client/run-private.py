"""Exercise a public GUI on a private display/bus/profile and reap every owned group."""
import argparse, configparser, importlib.machinery, json, os, select, shutil, signal, subprocess, tempfile, time, traceback
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('kind',choices=['editor']);p.add_argument('output',type=Path);p.add_argument('--inspect-file-menu',action='store_true');p.add_argument('--public-client',type=Path,required=True);a=p.parse_args()
assert not a.inspect_file_menu or a.kind=='inspect'
out=a.output.resolve();assert not out.exists();out.mkdir(parents=True)
driver=importlib.machinery.SourceFileLoader('owned_input',str(root/'owned-x11-input.py')).load_module()
processes=[];handles=[];control=None;error=None;cleanup_errors=[]
class CompletedInspection(Exception):pass
def group_exists(pid):
    try: os.killpg(pid,0); return True
    except ProcessLookupError: return False
def start(argv,name,piped=False):
    stdout=subprocess.PIPE if piped else (out/(name+'-stdout')).open('w')
    stderr=(out/(name+'-stderr')).open('w');handles.append(stderr)
    if not piped:handles.append(stdout)
    proc=subprocess.Popen(argv,env=env,start_new_session=True,stdout=stdout,stderr=stderr,text=True)
    processes.append(proc);return proc
def line(proc):
    assert select.select([proc.stdout],[],[],10)[0], 'Owned service address timeout'
    value=proc.stdout.readline().strip();assert value;return value
def wait_assert(check,message,timeout=10):
    deadline=time.monotonic()+timeout
    while not check():
        assert app.poll() is None, 'Owned app exited early'
        assert time.monotonic()<deadline,message
        time.sleep(.05)
with tempfile.TemporaryDirectory(prefix='supra-menu-owned-') as temporary:
    state=Path(temporary);env=os.environ.copy()
    for key in ['DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER','DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','DBUS_STARTER_ADDRESS','DBUS_STARTER_BUS_TYPE','LD_PRELOAD','LD_LIBRARY_PATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML_IMPORT_PATH','QML2_IMPORT_PATH','XDG_CURRENT_DESKTOP','KDE_FULL_SESSION','XAUTHORITY','XDG_MENU_PREFIX']:
        env.pop(key,None)
    for key,directory in [('HOME','home'),('XDG_RUNTIME_DIR','runtime'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_CONFIG_DIRS','base-config'),('XDG_DATA_DIRS','base-data')]:
        path=state/directory;path.mkdir(mode=0o700);env[key]=str(path)
    env.update(QT_QPA_PLATFORM='xcb',QT_STYLE_OVERRIDE='Fusion',XDG_SESSION_TYPE='x11',DBUS_SYSTEM_BUS_ADDRESS=f'unix:path={state}/no-system-bus',LC_ALL='C.UTF-8',LANGUAGE='en_US')
    try:
        xvfb=start(['Xvfb','-displayfd','1','-nolisten','tcp','-noreset','-screen','0','1024x768x24'],'xvfb',True)
        number=line(xvfb);assert number.isdigit();env['DISPLAY']=':'+number;env['SUPRA_PRIVATE_XVFB_DISPLAY']=env['DISPLAY']
        # An explicit config with no service directories prevents host activation.
        config=state/'bus.conf';config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(state)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
        bus=start(['dbus-daemon','--nofork','--print-address=1','--config-file='+str(config)],'bus',True)
        address=line(bus);assert address.startswith('unix:');env['DBUS_SESSION_BUS_ADDRESS']=address
        # Input guard sees the exact display that this wrapper started.
        os.environ['DISPLAY']=env['DISPLAY'];os.environ['SUPRA_PRIVATE_XVFB_DISPLAY']=env['DISPLAY']
        if a.kind in {'mechanism','shortcuts','stale','negative-focus'}:
            app=start([str(root/('input-shortcut-mechanism' if a.kind=='shortcuts' else 'input-mechanism'))],'client')
            control=driver.OwnedInput(app.pid);w=control.wait_window('Supra owned input');control.focus(w)
            if a.kind=='stale':
                assert control.owner(0xdeadbeef) is None and not control.viewable(0xdeadbeef)
                control.sync();assert control.stale_windows>=2
            if a.kind=='negative-focus':
                control.x.XSetInputFocus(control.d,0xdeadbeef,2,0);control.sync()
            if a.kind=='shortcuts':
                control.key('m',('Control_L',));control.key('n',('Control_L','Shift_L'))
            control.type_text('supraownedentry');control.key('Return');assert app.wait(timeout=10)==0
            observed=json.loads((out/'client-stdout').read_text());assert observed['state']=='PASS'
        else:
            apps=state/'base-data/applications';apps.mkdir()
            writable_apps=state/'data/applications';writable_apps.mkdir()
            original=apps/'org.supralinux.MenuFixture.desktop'
            original.write_text('[Desktop Entry]\nType=Application\nName=Owned Original\nExec=/bin/false\nIcon=application-x-executable\nCategories=Utility;\n')
            original_bytes=original.read_bytes()
            menus=state/'base-config/menus';menus.mkdir()
            base_menu=menus/'applications.menu'
            base_menu.write_text('<?xml version="1.0"?><!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN" "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd"><Menu><Name>Applications</Name><AppDir>'+str(apps)+'</AppDir><AppDir>'+str(writable_apps)+'</AppDir><DirectoryDir>'+str(state/'data/desktop-directories')+'</DirectoryDir><MergeFile>'+str(state/'config/menus/applications-kmenuedit.menu')+'</MergeFile><Include><All/></Include></Menu>')
            (state/'config/kmenueditrc').write_text('[General]\nShowMenuBar=true\n')
            app=start(['/usr/bin/kmenuedit','org.supralinux.MenuFixture.desktop'],'editor')
            control=driver.OwnedInput(app.pid);w=control.wait_window('KDE Menu Editor');control.focus(w)
            if a.kind=='inspect':
                if a.inspect_file_menu:control.key('f',('Alt_L',))
                time.sleep(.2)
                pixels=start([str(a.public_client.resolve()),'screenshot',str(out/'private-editor.png')],'pixels');assert pixels.wait(timeout=10)==0
                selected=start([str(a.public_client.resolve()),'select','org.supralinux.MenuFixture.desktop'],'selection');assert selected.wait(timeout=10)==0
                observed={'state':'PASS','scope':'private original GUI inspection and typed public selection only','creation_save':'NOT-RUN'}
                (out/'result.json').write_text(json.dumps(observed,indent=2)+'\n')
                # Exit the diagnostic through ordinary cleanup.
                raise CompletedInspection()
            # Existing entry name uses the public, source-declared QLabel mnemonic.
            control.key('n',('Alt_L',));control.key('a',('Control_L',));control.type_text('supraownedrenamed');control.key('s',('Control_L',))
            override=state/'data/applications/org.supralinux.MenuFixture.desktop'
            def renamed():
                if not override.exists():return False
                parser=configparser.ConfigParser(interpolation=None);parser.read(override)
                return parser['Desktop Entry'].get('Name')=='supraownedrenamed' and parser['Desktop Entry'].get('Exec')=='/bin/false'
            wait_assert(renamed,'Actual entry rename/save did not reach private desktop override')
            assert original.read_bytes()==original_bytes
            control.wait_focus(w)
            control.key('n',('Control_L','Shift_L'));dialog=control.wait_window('New Submenu');control.focus(dialog);control.type_text('supraownedfolder');control.key('Return')
            time.sleep(.1);control.focus(w);control.key('s',('Control_L',))
            saved_menu=state/'config/menus/applications-kmenuedit.menu'
            wait_assert(lambda:saved_menu.exists() and 'supraownedfolder' in saved_menu.read_text(),'Actual submenu/save did not reach private menu')
            directories=list((state/'data/desktop-directories').glob('*.directory'))
            assert any('Name=supraownedfolder' in f.read_text() for f in directories)
            control.wait_focus(w)
            control.key('n',('Control_L',));dialog=control.wait_window('New Item');control.focus(dialog);control.type_text('supraownedentry');control.key('Return')
            control.wait_focus(w);control.key('p',('Alt_L',));control.key('a',('Control_L',));control.type_text('/bin/false');control.key('s',('Control_L',))
            def new_entry():
                for f in writable_apps.glob('*.desktop'):
                    entry=configparser.ConfigParser(interpolation=None);entry.read(f)
                    fields=entry['Desktop Entry']
                    if fields.get('Name')=='supraownedentry' and fields.get('Type')=='Application' and fields.get('Exec')=='/bin/false':return f
                return None
            wait_assert(new_entry,'Actual new entry/save did not preserve typed Name/Type/Exec')
            assert 'supraownedentry' in saved_menu.read_text()
            assert original.read_bytes()==original_bytes
            control.wait_focus(w)
            generated=new_entry();assert generated
            selected=start([str(a.public_client.resolve()),'select',generated.name],'created-selection');assert selected.wait(timeout=10)==0
            pixels=start([str(a.public_client.resolve()),'screenshot',str(out/'private-editor.png')],'pixels');assert pixels.wait(timeout=10)==0
            control.key('q',('Control_L',));assert app.wait(timeout=10)==0
            app=start(['/usr/bin/kmenuedit',generated.name],'reopened-editor')
            control.close();control=driver.OwnedInput(app.pid);w=control.wait_window('KDE Menu Editor');control.focus(w)
            selected=start([str(a.public_client.resolve()),'select',generated.name],'reopened-selection');assert selected.wait(timeout=10)==0
            control.key('n',('Alt_L',));control.key('a',('Control_L',));control.type_text('supraownedreopened');control.key('s',('Control_L',))
            def reopened():
                entry=configparser.ConfigParser(interpolation=None);entry.read(generated)
                return entry['Desktop Entry'].get('Name')=='supraownedreopened' and entry['Desktop Entry'].get('Exec')=='/bin/false'
            wait_assert(reopened,'Saved menu/entry did not reopen for actual second edit');control.wait_focus(w)
            for directory in ['data/applications','data/desktop-directories','config/menus']:
                source=state/directory
                if source.exists():shutil.copytree(source,out/'payload'/directory)
            observed={'state':'PASS','scope':'original installed editor actual private rename/submenu/new-entry/Exec/save/reopen, typed public selection and software pixels','seed_unchanged':True,'generated_entry':generated.name,'show_menu_bar':True,'application_launch':'NOT-RUN','global_shortcuts':'NOT-RUN'}
        (out/'result.json').write_text(json.dumps(observed,indent=2)+'\n')
    except CompletedInspection:
        pass
    except BaseException as caught:
        error=caught;(out/'result.json').write_text(json.dumps({'state':'FAIL','scope':a.kind,'error':str(caught),'traceback':traceback.format_exc()},indent=2)+'\n')
    finally:
        if control:control.close()
        for proc in reversed(processes):
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            if proc.poll() is None:
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
            deadline=time.monotonic()+3
            while group_exists(proc.pid) and time.monotonic()<deadline:time.sleep(.05)
            if group_exists(proc.pid):
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                deadline=time.monotonic()+3
                while group_exists(proc.pid) and time.monotonic()<deadline:time.sleep(.05)
                if group_exists(proc.pid):cleanup_errors.append('Owned group remains: '+str(proc.pid))
            if proc.stdout and hasattr(proc.stdout,'close'):proc.stdout.close()
        for handle in handles:handle.close()
cleanup={'state':'PASS' if not cleanup_errors and not state.exists() else 'FAIL','owned_process_groups_absent':not cleanup_errors,'private_runtime_absent':not state.exists(),'errors':cleanup_errors}
(out/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
assert cleanup['state']=='PASS',cleanup
if error:raise error
print('Actual '+a.kind+' PASS; all owned groups and runtime removed')
