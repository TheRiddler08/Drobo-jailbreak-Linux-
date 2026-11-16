# Drobo B810n / B810i runbook

Both units use a Marvell Armada XP MV78460 (4 cores, ARMv7) with 2 GB of
RAM, and are very likely the same board. This kit boots mainline Linux 6.12
from RAM using the Drobo 5N project's U-Boot `go` stub, with a discovery
system that maps the hardware.

**Nothing here writes to flash, disks, GPIOs or I²C chips.** Unplug the
power for 10 seconds and the unit is back on stock firmware.

Status: untested on a real B810. What is known and what is a guess is
listed in [../docs/hardware-notes.md](../docs/hardware-notes.md).

All commands below are run from the top folder of this repo.

## What you need
- A 3.3 V USB-to-serial adapter. Jumper on **3.3V**; connect GND, TX and RX
  only, never VCC.
- Possibly a soldering iron (see step 2 of session 1).
- A computer with Python 3 and `pip install pyserial`.
- An Ethernet cable from the Drobo straight to that computer (session 2).
- A multimeter helps for finding ground.

## Ground rules
- No drives with data you need. Start with **no drives**, then one blank one.
- In U-Boot, never run `saveenv`, `flinfo` (it crashes this U-Boot on the
  5N), `erase`, or `bootm` with a Linux kernel. `tools/drobo-console.py`
  refuses these for you.
- Keep open-case sessions under an hour. On the 5N the power controller
  slows the fan when nothing manages it, and this test system doesn't
  manage it yet. The report prints temperatures; stop above 70 °C.
- Save every log into [`../logs/`](../logs/), and read
  [`../logs/README.md`](../logs/README.md) before committing one.

## Session 1: look, don't touch (B810n first)

1. **Open it up.** Unplug, remove all drives, open the case. Photograph the
   whole motherboard and the drive backplane, both sides if you can.
2. **Find the consoles.** There are two serial ports, both 115200 8N1. A
   B810i owner found one showing Marvell U-Boot then VxWorks, and the other
   showing Linux booting to a root shell. **We need the U-Boot one** (the
   chip's UART0): the stub and our kernel only print there. On the 5N that
   port is four bare holes with no header fitted (you solder three wires),
   and the factory header is the Linux one. Confirm GND with a multimeter
   (continuity to chassis) before connecting.
3. **Wire it.** Adapter GND to GND, adapter TX to board RX, adapter RX to
   board TX. If the console prints but ignores typing, suspect the ground
   wire first.
4. **Record a full stock boot from each port:**
   ```
   python3 tools/drobo-console.py PORT log --log logs/b810n-stock-uart0.log
   ```
   (`PORT` is `COM5`, `/dev/ttyUSB0`, `/dev/cu.usbserial-…`.) Plug in, wait
   for the boot to finish, press Ctrl-C. Repeat on the other port with a
   different log name. The U-Boot lines starting with `PEX` matter most:
   they show how the PCIe lanes are set up.
5. **Catch U-Boot and read its settings.** There is no countdown (the boot
   delay is 0 on the 5N), so the tool taps space for you. Unplug the Drobo,
   start this, then plug in:
   ```
   python3 tools/drobo-console.py PORT run b810/uboot/session1.txt --catch --log logs/b810n-uboot.log
   ```
   It runs `version`, `bdinfo`, `printenv` and `help`, typing slowly and
   checking each line's echo, because this U-Boot drops fast characters.
6. **On the Linux port**, if it reaches a shell, run and save:
   ```
   cat /proc/cpuinfo; cat /proc/cmdline; cat /proc/mtd
   ls /sys/bus/i2c/devices/; lspci 2>/dev/null; dmesg
   ```
7. Send the logs and photos. They decide which device tree session 2 uses.

## Session 2: boot mainline Linux from RAM

Files in `b810/prebuilt/` (check them with `sha256sum -c SHA256SUMS` there):

| File | What | Load address |
|---|---|---|
| `probe.bin` | Prints one line of CPU state and returns to U-Boot | `8000000` |
| `kernel.bin` | Stub + Linux 6.12 + discovery system | `8000000` |
| `b810-safe.dtb` | Device tree with only the 5N's two PCIe ports. Use first. | `3f00000` |
| `b810-probe.dtb` | All ten PCIe ports. Only if session 1's `PEX` lines say it's safe. | `3f00000` |

1. Give your computer the address `192.168.1.10` on the port cabled to the
   Drobo, and start the TFTP server (it only serves that folder, read-only):
   ```
   python3 tools/tftpd.py --root b810/prebuilt
   ```
   Port 69 may need `sudo` on Linux. Allow it through the firewall.
2. **Probe first.** Unplug the Drobo, start this, plug in:
   ```
   python3 tools/drobo-console.py PORT run b810/uboot/probe.txt --catch --log logs/b810n-probe.log
   ```
   Success is one `#STUB alive r0=… sctlr=… intregwin=…` line and then the
   `Marvell>>` prompt again. That proves the load path, the console and the
   register address without changing anything. Press Ctrl-C. If there's no
   `#STUB alive` line, stop and send the log.
3. **Boot Linux.** Power-cycle the same way and run:
   ```
   python3 tools/drobo-console.py PORT run b810/uboot/ramboot.txt --catch --log logs/b810n-ramboot.log
   ```
   The file sets the addresses, loads the DTB and kernel, runs `usb stop`
   (on the 5N, without it the USB controller keeps writing into memory
   under Linux) and `go 8000000`. The tool then keeps recording. To type at
   the Linux prompt, press Ctrl-C and open the port in a normal terminal
   (PuTTY, `screen PORT 115200`).

### What success looks like
1. `#STUB alive ...`, `#STUB caches off, jumping`, CPU reset and copy lines
2. `Booting Linux on physical CPU 0x0` and kernel messages
3. A report: board model, 4 CPU cores, about 2 GB of RAM, PCIe devices
   (Marvell is `1b4b`), SATA links, network ports, every I²C bus with the
   chips on it, temperatures and GPIO lines
4. A `#` prompt. `dhcp` starts networking and telnet; `pca BUS ADDR` reads
   an I²C expander without changing it; `cat /tmp/report.txt` shows the
   report again.

Drive-bay disks probably won't show up yet: on the 5N, bays stay unpowered
until Linux switches them on through an I²C expander. Send the report and
the B810's bay-power map gets worked out before anything is switched on.
A small disk listed "via usb" is the internal stick holding the stock
firmware. Never write to it.

### If it fails
| What you see | Likely cause | Do |
|---|---|---|
| Tool says "No U-Boot prompt seen" | Wrong port (the Linux one), TX/RX swapped, bad ground | Recheck wiring; try the other port |
| `tftpboot` prints `T T T` and times out | Firewall, wrong PC address, or cable in a port U-Boot doesn't use | Try the other Ethernet port; check the TFTP server prints a request |
| No `#STUB alive` after `go` | File didn't load, or registers aren't at `0xd0000000` | Send the log |
| Stops after `jumping` or during the copy | The area the 5N project spent most time on | Send the log; the stub prints where it stopped |
| Kernel panic | First bring-up on a new board | The system waits (`panic=0`); send the log |

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
(GPL-2.0), as do the memory layout (Image copied to 0x1208000, DTB at
0x3f00000, kernel.bin at 0x8000000) and `tools/tftpd.py`.
