import sys, struct, re
data = open(sys.argv[1], 'rb').read()
print("size", len(data))
print("header hex:", data[:64].hex())
sigs = {
    b'\x27\x05\x19\x56': 'uImage',
    b'\x1f\x8b\x08': 'gzip',
    b'\x7fELF': 'ELF',
    b'hsqs': 'squashfs-le',
    b'sqsh': 'squashfs-be',
    b'\x45\x3d\xcd\x28': 'cramfs',
    b'\x85\x19\x03\x20': 'jffs2-node-le',
    b'\x19\x85\x20\x03': 'jffs2-node-be',
    b'\x18\x28\x6f\x01': 'zImage-magic',
    b'070701': 'cpio-newc',
    b'BZh91AY': 'bzip2',
    b'\xfd7zXZ': 'xz',
    b'\x5d\x00\x00\x80': 'lzma?',
}
hits = []
for s, n in sigs.items():
    for m in re.finditer(re.escape(s), data):
        hits.append((m.start(), n))
hits.sort()
from collections import Counter
c = Counter(n for _, n in hits)
print(c)
last = {}
for off, n in hits:
    if n.startswith('jffs2'):
        continue
    if n == 'lzma?' and c[n] > 30:
        continue
    print(f"0x{off:08x} {n}")
j = [o for o, n in hits if n.startswith('jffs2')]
if j:
    print(f"jffs2 nodes: first 0x{j[0]:x} last 0x{j[-1]:x} count {len(j)}")
