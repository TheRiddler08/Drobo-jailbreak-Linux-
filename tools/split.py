import sys, struct, zlib, time, os
data = open(sys.argv[1], 'rb').read()
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
# container header
print("container header words:", [hex(x) for x in struct.unpack('>16I', data[:64])])
print("container ascii:", data[:0x22c].replace(b'\x00', b'.')[:200])
for off in (0x22c, 0x120022c):
    h = data[off:off+64]
    magic, hcrc, ts, size, load, ep, dcrc, os_, arch, typ, comp = struct.unpack('>7I4B', h[:32])
    name = h[32:].split(b'\0')[0].decode(errors='replace')
    print(f"\nuImage @0x{off:x}: name='{name}' size={size} load=0x{load:x} entry=0x{ep:x} "
          f"time={time.strftime('%Y-%m-%d', time.gmtime(ts))} os={os_} arch={arch} type={typ} comp={comp}")
    payload = data[off+64:off+64+size]
    print("  data crc ok:", zlib.crc32(payload) & 0xffffffff == dcrc)
    fn = os.path.join(out, f"img_{off:x}.bin")
    open(fn, 'wb').write(payload)
    if comp == 1 or payload[:2] == b'\x1f\x8b':
        try:
            d = zlib.decompress(payload, 47)
            open(fn + '.dec', 'wb').write(d)
            print("  decompressed:", len(d))
        except Exception as e:
            print("  gunzip failed:", e)
# gzip inside zImage
z = data.find(b'\x1f\x8b\x08', 0x290)
d = zlib.decompressobj(47)
k = d.decompress(data[z:z+0x1200000])
open(os.path.join(out, 'linux_Image'), 'wb').write(k)
print("\nlinux Image decompressed:", len(k))
print("trailing after second image:", len(data) - (0x120022c + 64 + struct.unpack('>I', data[0x120022c+12:0x120022c+16])[0]))
