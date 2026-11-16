# Hardware notes: what is known, and how we know it

Nothing in this project has run on a real B810 or B800i yet. This page
separates facts from guesses so the bench sessions can confirm or correct
each one. Update the "Confirmed" column as logs come in.

## B810n / B810i

| Item | Current belief | Source | Confirmed on our unit |
|---|---|---|---|
| CPU | Marvell Armada XP MV78460, 4× ARMv7 | B810n review; B810i U-Boot banner "DB-78460-BP" in an EEVblog repair thread | no |
| RAM | 2 GB | B810n review | no |
| B810n and B810i share a board | Likely | Same CPU and U-Boot board name | no |
| U-Boot | Marvell 2009.08 AMP build; starts VxWorks, then Linux | 5N project; EEVblog thread | no |
| Boot delay | 0 (no countdown) | 5N project | no |
| U-Boot console | UART0, 115200 8N1; on the 5N it is unpopulated holes (J2) | 5N project | no |
| Linux console | UART1 on a factory header (J3 on the 5N) | 5N project; stock `mv_rsrc=uart1` | no |
| Register window | `0xd0000000` | 5N project | no (the probe stub prints it) |
| Stock firmware storage | Internal USB stick with `vxworks`, `lximage` | EEVblog thread (`fatls usb 0:1`) | no |
| `bootm` with modern Linux | Fails; `go` + stub works | 5N project | no |
| Writes below 16 MB hang during boot | True on the 5N; we copy the kernel to 0x1208000 | 5N project | no |
| SATA controllers | Unknown for 8 bays. The 5N has two 88SE9122 on PCIe ports 8 and 9 | 5N project | no |
| Bay power / LEDs | Unknown. The 5N uses PCA9555 expanders at I²C 0x20 and 0x23 | 5N project | no |
| Fan / power controller | Unknown. The 5N talks to it on UART2 at 38400 baud | 5N project | no |
| Ethernet | Unknown port mapping. B810n has 2 ports; B810i has more | Product specs | no |

## B800i / DroboElite

| Item | Current belief | Source | Confirmed on our unit |
|---|---|---|---|
| CPU | Marvell MV78200, 2 independent ARMv5 cores | Firmware image name "TD78200-A0"; DroboFS wiki | no |
| Core split | VxWorks runs disks + BeyondRAID, Linux 2.6.22 runs networking | Firmware analysis in this repo | from firmware only |
| Consoles | Two 3.3 V serial ports, 115200 baud (J4 VxWorks, J5 Linux on the DroboFS) | DroboFS wiki | no |
| SATA controller | Marvell 88SX7042 on PCIe | DroboFS wiki | no |
| RAM | Unknown; the stub assumes 256 MB | Guess | no |
| Register window | `0xf1000000` or `0xd0000000` | Guess; two stub builds cover both | no |
| Machine ID | 9001 is our own made-up number; the stub passes it itself | This repo | n/a |

## Sources
- Drobo 5N Debian project: https://github.com/georgestephanis/drobo-5n
- DroboFS hardware wiki: https://github.com/droboports/droboports.github.io/wiki/DroboFS-hardware
- EEVblog B810i repair thread: https://www.eevblog.com/forum/repair/drobo-b810i-nas-half-bricked-after-failed-firmware-update/5/?wap2=
- B810n review (CPU, RAM): https://www.itpro.com/nas/29191/drobo-b810n-review
- Firmware analysis: [b800i-firmware-analysis.md](b800i-firmware-analysis.md)
