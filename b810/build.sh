#!/usr/bin/env bash
# Rebuild the Drobo B810n / B810i test boot files from source.
# Tested on Ubuntu 24.04 (x86_64). Needs ~3 GB of disk and 10-20 minutes.
#
#   sudo apt install gcc-arm-linux-gnueabihf device-tree-compiler bc bison flex \
#                    libssl-dev cpio git make python3
#   ./build.sh
#
# Output in out/: kernel.bin, b810-safe.dtb, b810-probe.dtb (see RUNBOOK.md)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/work}"
OUT="$HERE/out"
CROSS=arm-linux-gnueabihf-
KVER=v6.12
BBVER=1_36_1
JOBS="$(nproc)"

mkdir -p "$WORK" "$OUT"

# 1. Mainline Linux v6.12 LTS: Armada XP needs no kernel patches.
[ -d "$WORK/linux" ] || git clone --depth 1 --branch "$KVER" https://github.com/gregkh/linux "$WORK/linux"

# 2. Static BusyBox (ARMv7 hard-float)
if [ ! -x "$WORK/bb/busybox" ]; then
  [ -d "$WORK/bb" ] || git clone --depth 1 --branch "$BBVER" https://github.com/mirror/busybox "$WORK/bb"
  make -C "$WORK/bb" ARCH=arm CROSS_COMPILE=$CROSS defconfig
  sed -i 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/; s/^CONFIG_TC=y/# CONFIG_TC is not set/' "$WORK/bb/.config"
  make -C "$WORK/bb" -j"$JOBS" ARCH=arm CROSS_COMPILE=$CROSS
fi

# 3. Discovery initramfs
R="$WORK/rootfs"
rm -rf "$R"
mkdir -p "$R"/{bin,sbin,etc,proc,sys,dev,tmp,root,mnt,usr/bin,usr/sbin,usr/share/udhcpc}
cp "$WORK/bb/busybox" "$R/bin/"
install -m 755 "$HERE/initramfs/init" "$R/init"
install -m 755 "$HERE/initramfs/udhcpc.script" "$R/usr/share/udhcpc/default.script"

# 4. Kernel (uncompressed Image, initramfs built in), out-of-tree build
K="$WORK/kbuild"
mkdir -p "$K"
cp "$HERE/kernel/b810.config" "$K/.config"
"$WORK/linux/scripts/config" --file "$K/.config" --set-str INITRAMFS_SOURCE "$R"
make -C "$WORK/linux" O="$K" ARCH=arm CROSS_COMPILE=$CROSS olddefconfig
make -C "$WORK/linux" O="$K" -j"$JOBS" ARCH=arm CROSS_COMPILE=$CROSS Image

# 5. Stub (Drobo 5N project's trampoline, unmodified)
${CROSS}gcc -march=armv7-a -marm -mfloat-abi=soft -c \
  -DCOPY -DIMG_LEN=0 -DDEST=0x01208000 -DDTB_ADDR=0x03f00000 \
  -o "$WORK/stub.o" "$HERE/stub/stub.S"
${CROSS}ld -Ttext=0 --build-id=none -o "$WORK/stub.elf" "$WORK/stub.o"
${CROSS}objcopy -O binary -j .text "$WORK/stub.elf" "$WORK/stub.bin"

# 6. Device trees
cat "$HERE/dts/drobo5n-base.dts" "$HERE/dts/b810-common.dtsi" > "$WORK/b810-safe.dts"
cat "$HERE/dts/drobo5n-base.dts" "$HERE/dts/b810-common.dtsi" "$HERE/dts/b810-probe-pcie.dtsi" > "$WORK/b810-probe.dts"
dtc -q -I dts -O dtb -o "$OUT/b810-safe.dtb" "$WORK/b810-safe.dts"
dtc -q -I dts -O dtb -o "$OUT/b810-probe.dtb" "$WORK/b810-probe.dts"

# 7. kernel.bin = stub + Image
python3 "$HERE/pack.py" "$WORK/stub.bin" "$K/arch/arm/boot/Image" "$OUT/kernel.bin"

ls -la "$OUT"
echo "Done. See RUNBOOK.md: DTB at 0x3f00000, kernel.bin at 0x8000000, go 0x8000000."
