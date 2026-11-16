#!/usr/bin/env python3
"""split.py FIRMWARE.tdf OUTDIR : pull the U-Boot images out of a Drobo .tdf.

Finds every U-Boot legacy image (magic 0x27051956) whose header checksum is
valid, wherever it sits in the file, checks its data checksum, and writes:

  img_<offset>.bin        the image payload
  img_<offset>.bin.dec    the same, gunzipped, if it is gzip
  img_<offset>.kernel     the decompressed kernel, if the payload is an ARM
                          zImage with a gzip stream inside

Developed against B800i/DroboElite firmware 2.0.6.
"""
import os
import re
import struct
import sys
import time
import zlib

MAGIC = b"\x27\x05\x19\x56"


def uimages(data):
    for m in re.finditer(re.escape(MAGIC), data):
        off = m.start()
        hdr = data[off:off + 64]
        if len(hdr) < 64:
            continue
        hcrc = struct.unpack(">I", hdr[4:8])[0]
        if zlib.crc32(hdr[:4] + b"\0\0\0\0" + hdr[8:]) & 0xFFFFFFFF == hcrc:
            yield off, hdr


def gunzip(blob):
    return zlib.decompressobj(47).decompress(blob)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = open(sys.argv[1], "rb").read()
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)

    found = list(uimages(data))
    if not found:
        sys.exit("no U-Boot images with a valid header checksum found")
    first = found[0][0]
    print("container header: %d bytes, text: %r" % (
        first, b" ".join(re.findall(rb"[ -~]{4,}", data[:first]))[:120]))

    end = 0
    for off, hdr in found:
        _, _, ts, size, load, entry, dcrc, os_, arch, typ, comp = struct.unpack(">7I4B", hdr[:32])
        name = hdr[32:].split(b"\0")[0].decode(errors="replace")
        payload = data[off + 64:off + 64 + size]
        end = max(end, off + 64 + size)
        print("\nuImage @0x%x: name=%r size=%d load=0x%x entry=0x%x built=%s os=%d arch=%d type=%d comp=%d" % (
            off, name, size, load, entry, time.strftime("%Y-%m-%d", time.gmtime(ts)), os_, arch, typ, comp))
        print("  data checksum ok:", zlib.crc32(payload) & 0xFFFFFFFF == dcrc)
        fn = os.path.join(out, "img_%x.bin" % off)
        open(fn, "wb").write(payload)
        if payload[:2] == b"\x1f\x8b":
            try:
                dec = gunzip(payload)
                open(fn + ".dec", "wb").write(dec)
                print("  gunzipped: %d bytes" % len(dec))
            except zlib.error as e:
                print("  gunzip failed:", e)
        elif payload[0x24:0x28] == b"\x18\x28\x6f\x01":  # ARM zImage magic
            for m in re.finditer(rb"\x1f\x8b\x08", payload):
                try:
                    dec = gunzip(payload[m.start():])
                except zlib.error:
                    continue
                if len(dec) > 1 << 20:
                    kn = os.path.join(out, "img_%x.kernel" % off)
                    open(kn, "wb").write(dec)
                    ver = re.search(rb"Linux version [ -~]+", dec)
                    print("  zImage -> kernel: %d bytes; %s" % (
                        len(dec), ver.group(0).decode()[:80] if ver else "no version string"))
                    break
    print("\nbytes after the last image:", len(data) - end)


if __name__ == "__main__":
    main()
