"""Original disposable BIOS guest for QMP framebuffer verification."""
READY = b"SUPRA_READY"
def boot_disk():
    # Set VGA mode 13h (320x200), fill top blue and bottom red.
    code = bytearray.fromhex(
        "b8 13 00 cd 10 b8 00 a0 8e c0 31 ff fc "
        "b9 00 7d b0 01 f3 aa b9 00 7d b0 04 f3 aa ba e9 00"
    )
    # QEMU debug console marker is emitted only after the fixture is drawn.
    for byte in READY:
        code.extend((0xb0, byte, 0xee))
    code.extend(bytes.fromhex("fa f4 eb fd"))
    return (bytes(code).ljust(510, b"\0") + b"\x55\xaa").ljust(1474560, b"\0")
