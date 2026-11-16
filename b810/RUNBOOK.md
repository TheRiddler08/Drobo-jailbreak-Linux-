# Drobo B810n / B810i runbook

Both units use a Marvell Armada XP MV78460 (4 cores, ARMv7) with 2 GB of
RAM, and are very likely the same board. This kit boots mainline Linux 6.12
from RAM using the Drobo 5N project's U-Boot `go` stub, with a discovery
system that maps the hardware.

**Nothing here writes to flash, disks, GPIOs or I²C chips.** Unplug the
power for 10 seconds and the unit is back on stock firmware.

## Ground rules
- No drives with data you need. Start with **no drives**, then one blank one.
- In U-Boot, never run `saveenv`, `flinfo` (it crashes this U-Boot on the
  5N), `erase`, or `bootm` with a Linux kernel.
- Serial adapter jumper on **3.3V**. GND, TX and RX only, never VCC.
- Keep sessions to under an hour with the case open. On the 5N the power
  controller slows the fan down when nothing manages it, and our test
  system doesn't manage it yet. The report prints temperatures; stop if
  anything goes past 70 °C.

## Session 1: look, don't touch (B810n first)

1. **Open it up.** Unplug, remove all drives, open the case. Photograph the
   whole motherboard and the drive backplane (both sides if you can).
2. **Find the consoles.** There are two serial ports, both 115200 8N1. A
   B810i owner found one showing Marvell U-Boot then VxWorks, and the other
   showing Linux booting to a root shell. **We need the U-Boot one** (the
   chip's UART0): the stub and our kernel only print there. On the 5N that
   port is four bare holes with no header fitted (you solder three wires),
   and the factory header is the Linux one. Photograph both before
   touching anything, and confirm GND with a multimeter (continuity to
   chassis) before connecting.
3. **Wire and log.** Adapter GND to GND, TX to board RX, RX to board TX.
   115200 8N1, no flow control. Turn on logging to a file.
4. **Capture a full stock boot from each header.** We especially want the
   U-Boot lines that start with `PEX` (they say how the PCIe lanes are set
   up) and the whole Linux log.
5. **Catch U-Boot.** On the 5N the boot delay is 0, so there is no
   countdown: unplug, start tapping the space bar, plug in, and keep
   tapping until `Marvell>>` appears. Then type slowly, one command at a
   time. This U-Boot drops characters when they arrive too fast. Run:
   ```
   version
   bdinfo
   printenv
   help
   ```
6. **On the Linux header** (if it reaches a shell), run and save:
   ```
   cat /proc/cpuinfo; cat /proc/cmdline; cat /proc/mtd
   ls /sys/bus/i2c/devices/; lspci 2>/dev/null; dmesg
   ```
7. Send me everything. That decides which device tree we use in session 2.

## Session 2: boot mainline Linux from RAM

Files (in `prebuilt/`):
- `kernel.bin`: stub + Linux 6.12 + discovery system. Load at `0x8000000`.
- `b810-safe.dtb`: only the two PCIe ports the 5N uses. Try this first.
- `b810-probe.dtb`: all ten PCIe ports. Only if session 1's `PEX` lines
  say it's safe.

1. Run a TFTP server on your PC with those files (Tftpd64 on Windows,
   `dnsmasq`/`tftpd-hpa` on Linux/Mac). Give the PC `192.168.1.10`.
2. Cable a Drobo Ethernet port straight to the PC.
3. Catch U-Boot and run:
   ```
   setenv ipaddr 192.168.1.50
   setenv serverip 192.168.1.10
   setenv netmask 255.255.255.0
   tftpboot 3f00000 b810-safe.dtb
   tftpboot 8000000 kernel.bin
   usb stop
   go 8000000
   ```
   These settings live in RAM only. `usb stop` matters: on the 5N, without
   it the USB controller keeps writing into memory under Linux. The two
   addresses must stay exactly as shown.

### What success looks like
1. `#STUB alive ...`, `#STUB caches off, jumping`, CPU reset and copy lines
2. `Booting Linux on physical CPU 0x0` and kernel messages
3. A report: board model, 4 CPU cores, ~2 GB RAM, PCIe devices (Marvell is
   `1b4b`), SATA links, network ports, every I²C bus with the chips on it,
   temperatures and GPIO lines
4. A `#` prompt. `dhcp` starts networking and telnet; `pca BUS ADDR` reads
   an I²C expander without changing it.

Drive-bay disks probably won't show up yet: on the 5N, bays stay unpowered until
Linux switches them on through an I²C expander. Send me the report and I'll
work out the B810's bay-power map before we switch anything on.

### If it fails
- **No `#STUB alive`:** the load address or file is wrong. Send the log.
- **Stops after `jumping` or the copy:** send the log. That's the area the
  5N project spent the most time on, and their stub prints exactly where it
  stopped.
- **Kernel panic:** the system waits so you can read it (`panic=0`). Send it.

## Planned
- Map bay power, bay LEDs, fan and power button (like the 5N's `drobo-bays`,
  `drobo-fand`, `drobo-powerbtn`)
- Back up the internal USB stick (it holds the stock firmware; a B810i
  owner found `vxworks` and `lximage` on it) and the SPI flash, from the
  running Linux, before anything is changed
- Persistent Debian 13 install with mdadm, Samba/NFS, and an iSCSI target
  (LIO) on the B810i
- Set U-Boot to boot Linux on its own (`amp_enable no`, see the 5N README)

## Credits
The stub (`stub/stub.S`, unmodified) and the base device tree
(`dts/drobo5n-base.dts`) come from
[georgestephanis/drobo-5n](https://github.com/georgestephanis/drobo-5n)
(GPL-2.0), as does the memory layout (Image copied to 0x1208000, DTB at
0x3f00000, kernel.bin at 0x8000000).
