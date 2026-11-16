# Drobo Jailbreak: Linux on Drobo business units

Goal: run a modern Linux as the **only** OS on Drobo's 8-bay business
units, with Linux driving every bay directly. BeyondRAID is replaced with
standard `mdadm` RAID, plus Samba, NFS or a Linux iSCSI target.

Drobo went out of business in 2023, so these units get no more updates.
This project gives them an open, maintainable software stack.

> **Status: untested on hardware.** The boot files are built and ready, but
> nothing has run on a real unit yet. Every runbook step boots from RAM and
> never writes to flash.

## Devices

| Model | Chip | Folder | Status | Priority |
|---|---|---|---|---|
| **B810n** (NAS) | Armada XP MV78460, 4× ARMv7, 2 GB | [`b810/`](b810/) | Kit ready, awaiting serial session | **1st** |
| **B810i** (iSCSI) | Same chip, likely the same board | [`b810/`](b810/) | Kit ready | 2nd |
| B800i / DroboElite | MV78200, 2× ARMv5 | [`b800i/`](b800i/) | Kit ready, on hold | Later |

The B810s go first: their chip has solid mainline Linux support (no kernel
patches needed), and the
[Drobo 5N Debian project](https://github.com/georgestephanis/drobo-5n)
already runs standalone Debian 13 on the same chip family. We reuse its
U-Boot stub and base device tree.

## How it works
Stock firmware splits the chip: VxWorks runs the disks and BeyondRAID,
Linux runs the network side, and they talk through shared memory. This
project stops at U-Boot before VxWorks starts, loads our own kernel into
RAM, and starts it with `go` through a small stub. (Drobo's Marvell AMP
U-Boot can't start modern kernels with `bootm`.) Linux then owns the whole
chip, including the drive controllers.

## Repo layout
| Path | What |
|---|---|
| `b810/RUNBOOK.md` | Bench steps for the B810n/B810i |
| `b810/prebuilt/` | `probe.bin`, `kernel.bin`, `b810-safe.dtb`, `b810-probe.dtb`, checksums |
| `b810/uboot/` | U-Boot command files for each step, typed by `tools/drobo-console.py` |
| `b810/dts/`, `b810/stub/`, `b810/kernel/`, `b810/initramfs/` | Sources: device trees, 5N stub, kernel config, discovery system |
| `b810/build.sh` | Rebuilds the B810 files from source |
| `b800i/` | The same set for the B800i (kernel patch with a board file) |
| `docs/b800i-firmware-analysis.md` | What's inside the stock B800i firmware |
| `docs/hardware-notes.md` | What is known vs guessed about each unit, with sources |
| `tools/drobo-console.py` | Serial helper: catches U-Boot, types commands safely, logs everything |
| `tools/tftpd.py` | Small read-only TFTP server (from the 5N project) |
| `tools/scan.py`, `tools/split.py` | Unpack and analyze stock `.tdf` firmware |
| `logs/` | Console captures from real units |

## Quick start (B810n)
With the serial adapter wired to the U-Boot console (see the runbook):
```
pip install pyserial
python3 tools/drobo-console.py PORT run b810/uboot/session1.txt --catch   # start, then plug the Drobo in
```
That records U-Boot's version and settings and changes nothing. The
[B810 runbook](b810/RUNBOOK.md) continues from there: a probe that returns
to U-Boot, then a RAM boot of Linux.

## Building
```
# B810 (ARMv7)
sudo apt install gcc-arm-linux-gnueabihf device-tree-compiler bc bison flex libssl-dev cpio git make python3
b810/build.sh

# B800i (ARMv5)
sudo apt install gcc-arm-linux-gnueabi bc bison flex libssl-dev cpio git make
b800i/build.sh
```

## Roadmap
- [x] Analyze stock B800i firmware
- [x] B800i kernel + board file, RAM-only system
- [x] B810 kernel, device trees, 5N stub, discovery system
- [x] Serial helper, TFTP server, probe stub, checksums
- [ ] B810n session 1: serial logs, U-Boot environment, board photos
- [ ] B810n session 2: RAM boot, map PCIe, I²C, GPIOs
- [ ] Bay power, LEDs, fan, power button
- [ ] Flash backup from Linux
- [ ] Persistent Debian 13, mdadm, Samba/NFS; LIO iSCSI target on the B810i
- [ ] Return to the B800i

## Safety
Use drives with no data you need. Don't `saveenv`, `flinfo` or erase flash
in U-Boot until the flash is backed up. Serial adapter at **3.3V**; never
connect its VCC pin.

## Credits
- [georgestephanis/drobo-5n](https://github.com/georgestephanis/drobo-5n) (GPL-2.0): the `go` stub, base device tree and boot layout used for the B810
- [droboports](https://github.com/droboports/droboports.github.io) wiki: DroboFS hardware and console notes
- [dhomas1/DroboApps](https://github.com/dhomas1/DroboApps): firmware archive

GPL-2.0, like Linux (see `LICENSE`).
