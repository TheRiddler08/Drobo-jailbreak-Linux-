# Drobo Jailbreak: Linux on the Drobo B800i

Goal: run a modern Linux as the **only** OS on a Drobo B800i (and probably the
DroboElite, which shares its firmware), with Linux driving all 8 bays
directly. BeyondRAID gets replaced with standard `mdadm` RAID, plus Samba, NFS
or a Linux iSCSI target.

Drobo went out of business in 2023, so these units get no more updates. This
project gives them an open, maintainable software stack.

> **Status: untested on hardware.** The kernel builds and the images are
> ready, but nothing has been booted on a real B800i yet. Follow
> [RUNBOOK.md](RUNBOOK.md); every step there runs from RAM and never writes
> to flash.

## How it works
The B800i is built around a Marvell MV78200 with two independent ARMv5
cores. Stock firmware runs VxWorks on one core (disks + BeyondRAID) and
Linux 2.6.22 on the other (networking), and the two talk through shared
memory. See [docs/firmware-analysis.md](docs/firmware-analysis.md).

This project:
1. Stops at U-Boot before VxWorks starts.
2. Loads a small launcher stub (`stub/stub.S`) plus a Linux 6.12 LTS kernel
   into RAM and starts it with `go`. (Drobo's Marvell AMP U-Boot can't start
   modern kernels with `bootm`; the
   [Drobo 5N Debian project](https://github.com/georgestephanis/drobo-5n)
   found the same thing.)
3. Linux brings up both PCIe links, finds the 88SX7042 SATA controller with
   `sata_mv`, and runs a BusyBox system that reports what hardware it found.

## Repo layout
| Path | What |
|---|---|
| `RUNBOOK.md` | Step-by-step bench procedure for the serial console |
| `kernel/linux-b800i.patch` | Patch against Linux v6.12: B800i board file, Kconfig, machine type 9001 |
| `kernel/b800i.config` | Full kernel config |
| `stub/stub.S` | Launcher: optional register remap, caches/MMU off, ATAGs, jump to zImage |
| `initramfs/` | Start-up script for the RAM-only system |
| `prebuilt/` | Ready-to-load images (`-f1` / `-d0`, see the runbook for which) |
| `tools/` | Scripts that unpack and analyze the stock `.tdf` firmware |
| `build.sh` | Rebuilds everything from source |

## Building
```
sudo apt install gcc-arm-linux-gnueabi bc bison flex libssl-dev cpio git make
./build.sh
```

## Roadmap
- [x] Unpack and analyze the stock firmware
- [x] Linux 6.12 board support, kernel and RAM-only system
- [ ] Session 1: serial console, U-Boot environment, board photos
- [ ] Session 2: RAM-boot, confirm drives and Ethernet
- [ ] Back up the flash from the running Linux
- [ ] Map GPIOs: bay power, LEDs, fan, power button
- [ ] Persistent install (Debian armel), mdadm, Samba/NFS/iSCSI

## Safety
Use drives with no data you need. Don't `saveenv` or erase flash in U-Boot
until the flash has been backed up. Serial adapter at **3.3V**; never connect
its VCC pin.

## Credits
- [droboports](https://github.com/droboports/droboports.github.io) wiki: DroboFS hardware and console notes
- [georgestephanis/drobo-5n](https://github.com/georgestephanis/drobo-5n): the `go`-stub approach on Drobo U-Boot
- [dhomas1/DroboApps](https://github.com/dhomas1/DroboApps): firmware archive

Kernel code is GPL-2.0, like Linux (see `LICENSE`).
