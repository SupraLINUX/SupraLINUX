"""Minimal synchronous QMP client for a private disposable VM socket."""
import json
import socket

class Qmp:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(15)
        self.stream = None
        try:
            self.sock.connect(str(path))
            self.stream = self.sock.makefile("rwb")
            self.greeting = self.read()
            self.call("qmp_capabilities")
        except Exception:
            self.close()
            raise

    def read(self):
        line = self.stream.readline()
        if not line:
            raise RuntimeError("QMP disconnected")
        return json.loads(line)

    def call(self, command, arguments=None):
        request = {"execute": command}
        if arguments is not None:
            request["arguments"] = arguments
        self.stream.write((json.dumps(request) + "\n").encode())
        self.stream.flush()
        while True:
            response = self.read()
            if "error" in response:
                raise RuntimeError(str(response["error"]))
            if "return" in response:
                return response["return"]

    def close(self):
        if self.stream is not None:
            self.stream.close()
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
