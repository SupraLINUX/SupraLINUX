"""Bounded XTEST input exclusively on the explicitly owned private Xvfb display."""
import ctypes as C
import os, time

class Attributes(C.Structure):
    _fields_=[(k,C.c_int) for k in ['x','y','width','height','border_width','depth']]+[('visual',C.c_void_p),('root',C.c_ulong)]+[(k,C.c_int) for k in ['klass','bit_gravity','win_gravity','backing_store']]+[('backing_planes',C.c_ulong),('backing_pixel',C.c_ulong),('save_under',C.c_int),('colormap',C.c_ulong),('map_installed',C.c_int),('map_state',C.c_int)]+[(k,C.c_long) for k in ['all_event_masks','your_event_mask','do_not_propagate_mask']]+[('override_redirect',C.c_int),('screen',C.c_void_p)]
class ErrorEvent(C.Structure):
    _fields_=[('type',C.c_int),('display',C.c_void_p),('resourceid',C.c_ulong),('serial',C.c_ulong),('error_code',C.c_ubyte),('request_code',C.c_ubyte),('minor_code',C.c_ubyte)]

class OwnedInput:
    def __init__(self, pid):
        name=os.environ.get('DISPLAY','')
        assert name==os.environ.get('SUPRA_PRIVATE_XVFB_DISPLAY') and name.startswith(':') and name[1:].isdigit()
        self.pid=pid; self.x=C.CDLL('libX11.so.6'); self.t=C.CDLL('libXtst.so.6')
        self.x.XOpenDisplay.argtypes=[C.c_char_p]; self.x.XOpenDisplay.restype=C.c_void_p
        self.d=self.x.XOpenDisplay(name.encode()); assert self.d
        self.errors=[];self.stale_windows=0
        @C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
        def error_handler(display,event):
            details=C.cast(event,C.POINTER(ErrorEvent)).contents
            if details.error_code==3 and details.request_code in {3,15,20}:
                self.stale_windows+=1
            else:self.errors.append({'error_code':details.error_code,'request_code':details.request_code,'resourceid':details.resourceid})
            return 0
        self.error_handler=error_handler
        self.x.XSetErrorHandler.argtypes=[C.c_void_p];self.x.XSetErrorHandler.restype=C.c_void_p
        self.previous_handler=self.x.XSetErrorHandler(C.cast(error_handler,C.c_void_p))
        self.x.XDefaultRootWindow.argtypes=[C.c_void_p]; self.x.XDefaultRootWindow.restype=C.c_ulong
        self.x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        self.x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_void_p)]
        self.x.XFree.argtypes=[C.c_void_p]
        self.x.XInternAtom.argtypes=[C.c_void_p,C.c_char_p,C.c_int]; self.x.XInternAtom.restype=C.c_ulong
        self.x.XGetWindowProperty.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.c_void_p)]
        self.x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
        self.x.XGetInputFocus.argtypes=[C.c_void_p,C.POINTER(C.c_ulong),C.POINTER(C.c_int)]
        self.x.XGetWindowAttributes.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(Attributes)]
        self.x.XSync.argtypes=[C.c_void_p,C.c_int]
        self.x.XStringToKeysym.argtypes=[C.c_char_p]; self.x.XStringToKeysym.restype=C.c_ulong
        self.x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong]; self.x.XKeysymToKeycode.restype=C.c_ubyte
        self.x.XCloseDisplay.argtypes=[C.c_void_p]
        self.t.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
        self.pid_atom=self.x.XInternAtom(self.d,b'_NET_WM_PID',0)
        self.title_atom=self.x.XInternAtom(self.d,b'_NET_WM_NAME',0)
    def windows(self):
        root=self.x.XDefaultRootWindow(self.d); found=[]
        def scan(w,depth):
            actual=C.c_ulong(); parent=C.c_ulong(); children=C.POINTER(C.c_ulong)(); count=C.c_uint()
            if not self.x.XQueryTree(self.d,w,C.byref(actual),C.byref(parent),C.byref(children),C.byref(count)):return
            try:
                for child in list(children[:count.value]):
                    found.append(child)
                    if depth: scan(child,depth-1)
            finally:
                if children: self.x.XFree(children)
        scan(root,1); return found
    def title(self,w):
        typ=C.c_ulong();fmt=C.c_int();n=C.c_ulong();after=C.c_ulong();data=C.c_void_p()
        rc=self.x.XGetWindowProperty(self.d,w,self.title_atom,0,1024,0,0,C.byref(typ),C.byref(fmt),C.byref(n),C.byref(after),C.byref(data))
        try:
            if rc==0 and fmt.value==8 and n.value and data.value:
                return C.string_at(data,n.value).decode(errors='replace')
        finally:
            if data.value:self.x.XFree(data)
        p=C.c_void_p()
        if not self.x.XFetchName(self.d,w,C.byref(p)) or not p.value: return ''
        try: return C.string_at(p).decode(errors='replace')
        finally: self.x.XFree(p)
    def owner(self,w):
        typ=C.c_ulong(); fmt=C.c_int(); n=C.c_ulong(); after=C.c_ulong(); data=C.c_void_p()
        rc=self.x.XGetWindowProperty(self.d,w,self.pid_atom,0,1,0,0,C.byref(typ),C.byref(fmt),C.byref(n),C.byref(after),C.byref(data))
        try:
            return C.cast(data,C.POINTER(C.c_ulong))[0] if rc==0 and fmt.value==32 and n.value==1 and data.value else None
        finally:
            if data.value:self.x.XFree(data)
    def wait_window(self, text, timeout=10):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            for w in self.windows():
                if text in self.title(w) and self.owner(w)==self.pid and self.viewable(w):
                    self.sync();return w
            self.sync()
            time.sleep(.05)
        observed=[{'window':w,'title':self.title(w),'pid':self.owner(w),'viewable':bool(self.viewable(w))} for w in self.windows()]
        self.sync()
        raise AssertionError('Owned window readiness timeout: '+text+'; private display windows='+str(observed))
    def focus(self,w):
        assert self.owner(w)==self.pid and self.viewable(w)
        self.x.XSetInputFocus(self.d,w,2,0); self.sync()
    def wait_focus(self,w,timeout=10):
        assert self.owner(w)==self.pid
        deadline=time.monotonic()+timeout;stable=None
        while time.monotonic()<deadline:
            visible=[win for win in self.windows() if self.viewable(win)]
            self.sync()
            if visible==[w]:
                if stable is None:stable=time.monotonic()
                if time.monotonic()-stable>=.25:
                    self.focus(w);return
            else:stable=None
            time.sleep(.025)
        raise AssertionError('Other private mapped windows remain after modal operation: '+str([(win,self.title(win)) for win in visible]))
    def viewable(self,w):
        a=Attributes();return self.x.XGetWindowAttributes(self.d,w,C.byref(a)) and a.map_state==2
    def sync(self):
        self.x.XSync(self.d,0)
        assert not self.errors,'Owned Xlib protocol error; abort through normal cleanup: '+str(self.errors)
    def key(self, name, modifiers=()):
        def event(k,pressed):
            sym=self.x.XStringToKeysym(k.encode()); assert sym
            code=self.x.XKeysymToKeycode(self.d,sym); assert code
            assert self.t.XTestFakeKeyEvent(self.d,code,pressed,0)
        for k in modifiers:event(k,1)
        event(name,1); event(name,0)
        for k in reversed(modifiers):event(k,0)
        self.sync(); time.sleep(.03)
    def type_text(self,text):
        punctuation={'/':'slash','.':'period','-':'minus',' ':'space'}
        assert text.isascii() and all(c.islower() or c.isdigit() or c in punctuation for c in text)
        for c in text:self.key(punctuation.get(c,c))
    def close(self):
        if self.d:
            self.x.XCloseDisplay(self.d);self.d=None
            self.x.XSetErrorHandler(self.previous_handler)
