# SPDX-FileCopyrightText: 2026 SupraLINUX contributors
# SPDX-License-Identifier: CC0-1.0
import json,os,resource,signal,shutil,subprocess,sys,tempfile,time
from pathlib import Path
root=Path(__file__).resolve().parent
client=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with tempfile.TemporaryDirectory(prefix='supralinux-private-video-') as temp:
 env=os.environ.copy()
 for key in ['DBUS_SESSION_BUS_ADDRESS','DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER','PIPEWIRE_RUNTIME_DIR','PIPEWIRE_CONFIG_DIR','PIPEWIRE_CONFIG_PREFIX','PIPEWIRE_CONFIG_NAME','PIPEWIRE_DEBUG','QT_PLUGIN_PATH','QML_IMPORT_PATH','QML2_IMPORT_PATH','LD_LIBRARY_PATH']:
  env.pop(key,None)
 for key in ['HOME','XDG_RUNTIME_DIR','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME']:
  path=Path(temp)/key;path.mkdir(mode=0o700);env[key]=str(path)
 env.update(PIPEWIRE_REMOTE='supralinux-private-video',PIPEWIRE_CONFIG_DIR=str(root),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',LIBGL_ALWAYS_SOFTWARE='1',KPIPEWIRE_FORCE_ENCODER='libvpx',DBUS_SESSION_BUS_ADDRESS='unix:path='+str(Path(temp)/'unused-dbus'),DBUS_SYSTEM_BUS_ADDRESS='unix:path='+str(Path(temp)/'unused-system-dbus'))
 with (output/'pipewire.log').open('w') as log,(output/'producer.log').open('w') as producer_log:
  producer=None
  service=subprocess.Popen(['pipewire','-c',str(root/'private-pipewire.conf')],env=env,stdout=log,stderr=log,start_new_session=True)
  try:
   deadline=time.monotonic()+10
   while time.monotonic()<deadline and service.poll() is None:
    if (Path(env['XDG_RUNTIME_DIR'])/'supralinux-private-video').exists():break
    time.sleep(0.05)
   assert service.poll() is None,'Private PipeWire service stopped early'
   producer=subprocess.Popen([str(Path(sys.argv[3]).resolve())],env=env,stdout=producer_log,stderr=producer_log,start_new_session=True)
   deadline=time.monotonic()+8
   while True:
    assert producer.poll() is None,'Private video producer stopped early'
    dump=subprocess.run(['pw-dump','-r','supralinux-private-video'],env=env,text=True,capture_output=True,timeout=5);dump.check_returncode()
    if any(o.get('type')=='PipeWire:Interface:Node' for o in json.loads(dump.stdout)):break
    assert time.monotonic()<deadline,'Private source node registration timed out'
    time.sleep(0.05)
   (output/'registry.json').write_text(dump.stdout)
   nodes=[obj for obj in json.loads(dump.stdout) if obj.get('type')=='PipeWire:Interface:Node']
   assert len(nodes)==1 and nodes[0]['info']['props']['node.name']=='supralinux-private-source','Unexpected device in private registry'
   video=Path(temp)/'actual-recording.webm'
   with (output/'client-stdout.txt').open('w') as stdout,(output/'client-stderr.txt').open('w') as stderr:
    process=subprocess.Popen([str(client),str(nodes[0]['id']),str(video)],env=env,text=True,stdout=stdout,stderr=stderr,start_new_session=True)
    linked=set();deadline=time.monotonic()+40
    try:
     while process.poll() is None and time.monotonic()<deadline:
      registry=subprocess.run(['pw-dump','-r','supralinux-private-video'],env=env,text=True,capture_output=True,timeout=5);registry.check_returncode()
      objects=json.loads(registry.stdout)
      ports=[o for o in objects if o.get('type')=='PipeWire:Interface:Port']
      outputs=[o for o in ports if o['info']['props'].get('port.direction')=='out' and int(o['info']['props']['node.id'])==nodes[0]['id']]
      inputs=[o for o in ports if o['info']['props'].get('port.direction')=='in']
      assert len(outputs)==1
      for target in inputs:
       pair=(outputs[0]['id'],target['id'])
       serials=(outputs[0]['info']['props']['object.serial'],target['info']['props']['object.serial'])
       if serials not in linked:
        link=subprocess.run(['pw-link','-r','supralinux-private-video',str(pair[0]),str(pair[1])],env=env,text=True,capture_output=True,timeout=5)
        (output/('link-'+str(pair[1])+'.log')).write_text(link.stdout+link.stderr)
        (output/'link-registry.json').write_text(registry.stdout)
        link.check_returncode();linked.add(serials)
      time.sleep(0.1)
     assert process.poll()==0,'Private consumer failed or exceeded timeout'
    finally:
     if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
     process.wait()
   print((output/'client-stdout.txt').read_text(),(output/'client-stderr.txt').read_text())
   probe=subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(video)],env=env,text=True,capture_output=True,timeout=10);probe.check_returncode()
   (output/'decoded-recording.json').write_text(probe.stdout)
   streams=json.loads(probe.stdout)['streams'];assert len(streams)==1
   assert streams[0]['codec_type']=='video' and streams[0]['codec_name']=='vp8' and streams[0]['width']==160 and streams[0]['height']==120 and int(streams[0]['nb_read_frames'])>=10,'Recording decode incomplete'
   subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],env=env,check=True,timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   shutil.copyfile(video,output/'actual-recording.webm')
   print('Isolated actual PipeWire source, SDK consumer, VP8 recording and complete FFmpeg decode: PASS')
  finally:
   if producer is not None:
    if producer.poll() is None:os.killpg(producer.pid,signal.SIGTERM)
    try:producer.wait(timeout=3)
    except subprocess.TimeoutExpired:os.killpg(producer.pid,signal.SIGKILL);producer.wait()
   if service.poll() is None:os.killpg(service.pid,signal.SIGTERM)
   try:service.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(service.pid,signal.SIGKILL);service.wait()
