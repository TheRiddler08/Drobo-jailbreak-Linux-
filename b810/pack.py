#!/usr/bin/env python3
"""pack.py STUB_BIN IMAGE OUT : build the B810 kernel.bin for a U-Boot `go` boot.

kernel.bin = stub.bin with the Image length written after its "DRBOLEN0"
marker, followed by the uncompressed Image (which already contains the
initramfs). Load it at 0x8000000, load the DTB at 0x3f00000, then
`go 0x8000000`. The stub copies the Image to 0x1208000 and starts it with
r2 = 0x3f00000. (Same layout as the Drobo 5N project's make-boot-files.py.)
"""
import struct, sys

if len(sys.argv) != 4:
    sys.exit(__doc__)
stub = bytearray(open(sys.argv[1], "rb").read())
image = open(sys.argv[2], "rb").read()
m = stub.find(b"DRBOLEN0")
if m < 0:
    sys.exit("stub has no DRBOLEN0 marker")
if len(stub) % 256:
    sys.exit("stub size is not a multiple of 256; payload would be misaligned")
# Image is copied to 0x1208000 and must end below the DTB at 0x3f00000.
if 0x1208000 + len(image) >= 0x3f00000:
    sys.exit("Image too big: it would overwrite the DTB")
# kernel.bin itself sits at 0x8000000; keep it clear of anything above.
stub[m + 8:m + 12] = struct.pack("<I", len(image))
open(sys.argv[3], "wb").write(bytes(stub) + image)
print("%s: %d bytes (stub %d + Image %d)" % (sys.argv[3], len(stub) + len(image), len(stub), len(image)))
