# Drobo B800i: first serial session runbook

Kernel: Linux 6.12 (LTS) with a new B800i board file, built-in sata_mv
(88SX7042 bays), mv643xx_eth (both ports), MD RAID, ext4/btrfs, and a
BusyBox system that runs entirely from RAM.

**Nothing in this runbook writes to flash.** If anything goes wrong, unplug
the power for 10 seconds and the unit boots stock firmware again.

## Ground rules
- Only use drives with no data you care about. For the first boot, use
  one blank spare drive, or no drives at all.
- Do **not** run `saveenv`, `flinfo`, any `erase` or any `cp.b` to flash
  in U-Boot. (`flinfo` crashed the Drobo 5N's U-Boot.)
- Adapter jumper on **3.3V**. Connect GND, TX and RX only, never VCC.

## Session 1: look, don't touch

1. **Open the case.** Unplug the power, remove the drives, open the shell,
   and photograph the whole motherboard (send me the photos).
2. **Find the consoles.** Look for two 4-pin headers near a board edge. On
   the DroboFS they're side by side with the pinout `Vcc | Rx | Tx | Gnd`.
   Confirm ground with a multimeter (continuity to the chassis) before
   connecting anything.
3. **Wire up.** Adapter GND to board GND, adapter TX to board RX, adapter RX
   to board TX. Terminal settings: 115200 baud, 8N1, no flow control
   (PuTTY, Tera Term or `screen /dev/ttyUSB0 115200`). Turn on logging to
   a file.
4. **Capture a stock boot.** Power on and save everything from both headers
   (move the adapter between them across two boots if you only have one).
5. **Interrupt U-Boot.** Power-cycle and press a key during the U-Boot
   countdown on the header that prints `Marvell>>` or similar. Then run:
   ```
   version
   bdinfo
   printenv
   help
   md.l 0xf1020080 1
   md.l 0xd0020080 1
   ```
   The last two tell us where the chip's registers live. One may hang; if
   so, power-cycle and skip it. Then power off.
6. **Send me** the logs and photos. Stop here for session 1.

## Session 2: boot our Linux from RAM (after I review session 1)

Pick the file based on step 5:
- Register base reads back as `f10000xx` → `b800i-linux-f1.bin`
- Register base reads back as `d00000xx` → `b800i-linux-d0.bin`

Loading over the network (fast):
1. Run a TFTP server on your PC (Tftpd64 on Windows, `dnsmasq` or
   `tftpd-hpa` on Linux/Mac) serving the .bin file.
2. Cable a Drobo Ethernet port straight to the PC. Give the PC a static IP
   of `192.168.1.10`.
3. Interrupt U-Boot **before** it starts VxWorks, then run:
   ```
   setenv ipaddr 192.168.1.50
   setenv serverip 192.168.1.10
   tftpboot 0x2000000 b800i-linux-f1.bin
   dcache off
   icache off
   go 0x2000000
   ```
   (If `dcache`/`icache` say "unknown command", skip them.)

Loading over serial (slow, about 11 minutes, if U-Boot has no network):
```
loady 0x2000000
```
Then send the file with YMODEM from your terminal and run `go 0x2000000`.

### What success looks like
1. `B800i stub OK, starting Linux...`
2. `Uncompressing Linux... done, booting the kernel.` then kernel messages
3. A banner listing the CPU, memory, PCI devices (we hope to see
   `11ab:7042`, the drive controller), any disks found, and the network ports
4. A `#` shell prompt. Type `dhcp` to get an address and start telnet.

### If it fails
- **Nothing after "stub OK":** probably the register-base or console
  setting. Try the other .bin, then send me the log.
- **Kernel panic or hang:** send me the full log. That's normal for a first
  bring-up, and the log tells us what to fix.
- **Boots but no disks:** send the output of `dmesg | grep -i -E "pci|ata"`.

## Later sessions (planned)
- Back up the whole flash from the running Linux over the network. This is
  safer than doing it in U-Boot.
- Find the GPIOs for bay power, LEDs, fan and power button.
- Install a persistent system (Debian armel on a USB stick or a drive),
  `mdadm` RAID across the bays, and Samba/NFS or a Linux iSCSI target.

## Files
- `prebuilt/b800i-linux-f1.bin`, `prebuilt/b800i-linux-d0.bin`: stub + kernel, load at 0x2000000
- `stub/stub.S`: the launcher. It turns caches/MMU off, writes ATAGs
  (256 MB RAM, machine 9001) and jumps to the kernel.
- `kernel/linux-b800i.patch`, `kernel/b800i.config`: kernel changes and config
- `initramfs/init`: the RAM system's start-up script
