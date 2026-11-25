"""Strict P6 capture parsing, fixture verification, and PNG export."""
import re
import struct
import zlib

def parse_ppm(data):
    header = re.match(rb"P6\s+(\d+)\s+(\d+)\s+255\r?\n", data)
    if not header:
        raise ValueError("Unsupported PPM header")
    width, height = map(int, header.groups())
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError("Invalid dimensions")
    pixels = data[header.end():]
    if len(pixels) != width * height * 3:
        raise ValueError("Unexpected PPM payload length")
    return width, height, pixels

def check_fixture(width, height, pixels):
    def color(x, y):
        i = (y * width + x) * 3
        return list(pixels[i:i+3])
    top = color(width//2, height//4)
    bottom = color(width//2, height*3//4)
    if not (top[2] > top[0] + 60 and top[2] > top[1] + 60
            and bottom[0] > bottom[1] + 60 and bottom[0] > bottom[2] + 60):
        raise ValueError(f"Expected blue/red fixture; sampled {top}, {bottom}")
    return {"top_rgb": top, "bottom_rgb": bottom}

def png_bytes(width, height, pixels):
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))
    raw = b"".join(b"\0" + pixels[y*width*3:(y+1)*width*3] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
