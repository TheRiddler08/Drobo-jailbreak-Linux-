#!/usr/bin/env bash
# Rebuild the Drobo B800i kernel images from source.
# Tested on Ubuntu 24.04 (x86_64). Needs about 2 GB of disk and ~10 minutes.
#
#   sudo apt install gcc-arm-linux-gnueabi bc bison flex libssl-dev cpio git make
#   ./build.sh
#
# Output: out/b800i-linux-f1.bin and out/b800i-linux-d0.bin (see RUNBOOK.md)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/work}"
OUT="$HERE/out"
CROSS=arm-linux-gnueabi-
KVER=v6.12
BBVER=1_36_1
JOBS="$(nproc)"

mkdir -p "$WORK" "$OUT"

# 1. Linux v6.12 LTS + B800i patch
if [ ! -d "$WORK/linux" ]; then
  git clone --depth 1 --branch "$KVER" https://github.com/gregkh/linux "$WORK/linux"
  git -C "$WORK/linux" apply "$HERE/kernel/linux-b800i.patch"
fi

# 2. Static BusyBox for the RAM-only system
if [ ! -x "$WORK/busybox/busybox" ]; then
  [ -d "$WORK/busybox" ] || git clone --depth 1 --branch "$BBVER" https://github.com/mirror/busybox "$WORK/busybox"
  make -C "$WORK/busybox" ARCH=arm CROSS_COMPILE=$CROSS defconfig
  sed -i 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/; s/^CONFIG_TC=y/# CONFIG_TC is not set/' "$WORK/busybox/.config"
  make -C "$WORK/busybox" -j"$JOBS" ARCH=arm CROSS_COMPILE=$CROSS
fi

# 3. Initramfs tree
R="$WORK/rootfs"
rm -rf "$R"
mkdir -p "$R"/{bin,sbin,etc,proc,sys,dev,tmp,root,mnt,usr/bin,usr/sbin,usr/share/udhcpc}
cp "$WORK/busybox/busybox" "$R/bin/"
install -m 755 "$HERE/initramfs/init" "$R/init"
install -m 755 "$HERE/initramfs/udhcpc.script" "$R/usr/share/udhcpc/default.script"

# 4. Kernel
cp "$HERE/kernel/b800i.config" "$WORK/linux/.config"
"$WORK/linux/scripts/config" --file "$WORK/linux/.config" --set-str INITRAMFS_SOURCE "$R"
make -C "$WORK/linux" ARCH=arm CROSS_COMPILE=$CROSS olddefconfig
make -C "$WORK/linux" -j"$JOBS" ARCH=arm CROSS_COMPILE=$CROSS zImage

# 5. Launcher stubs (f1: registers already at 0xf1000000; d0: move them there)
for v in f1 d0; do
  extra=""
  [ "$v" = d0 ] && extra="-DREMAP_FROM=0xd0020000"
  ${CROSS}gcc -march=armv5te -marm -nostdlib -Wl,--build-id=none -Ttext=0 $extra \
    -o "$WORK/stub-$v.elf" "$HERE/stub/stub.S"
  ${CROSS}objcopy -O binary -j .text "$WORK/stub-$v.elf" "$WORK/stub-$v.bin"
  # The kernel must start exactly at the stub's `payload` label.
  want=$((0x$(${CROSS}nm "$WORK/stub-$v.elf" | awk '/ payload$/{print $1}')))
  [ "$(stat -c %s "$WORK/stub-$v.bin")" = "$want" ] || { echo "stub size != payload offset"; exit 1; }
  cat "$WORK/stub-$v.bin" "$WORK/linux/arch/arm/boot/zImage" > "$OUT/b800i-linux-$v.bin"
done

ls -la "$OUT"
echo "Done. Load at 0x2000000 and run 'go 0x2000000' (see RUNBOOK.md)."
