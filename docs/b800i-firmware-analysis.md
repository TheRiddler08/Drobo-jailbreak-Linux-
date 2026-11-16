# Stock firmware analysis: B800i / DroboElite 2.0.6

Source: `Drobo-B800i-Elite-firmware-2.0.6.zip` from the community archive at
[dhomas1/DroboApps](https://github.com/dhomas1/DroboApps) (the firmware itself
is not redistributed here). Reproduce with the scripts in `tools/` (run from the repo root):

```
unzip Drobo-B800i-Elite-firmware-2.0.6.zip      # -> .tdz
unzip Drobo-B800i-Elite-firmware-2.0.6.tdz      # -> release.Drobo_elite1.tdf
python3 tools/scan.py  release.Drobo_elite1.tdf
python3 tools/split.py release.Drobo_elite1.tdf out/
```

## Container (`.tdf`)
- 0x22c-byte header, magic `TDIH`, target name `Voltron`, string
  "Data Robotics Firmware". Not encrypted.
- Two U-Boot legacy images follow, both with valid CRCs:

| Offset | Name | Load/entry | OS | Size |
|---|---|---|---|---|
| 0x22c | `Linux-2.6.22.18` | 0x8008000 | Linux, uncompressed zImage | 2.8 MB |
| 0x120022c | `TD78200-A0:VOLTRON release bin g` | 0x10000 | VxWorks, gzip | 3.5 MB → 8.3 MB |

Both were built on 2015-09-10/11.

## Linux side
- `Linux version 2.6.22.18 (root@jwinfield01) (gcc 4.2.0 prerelease)`.
- Default built-in command line mounts root over NFS
  (`root=/dev/nfs ... mem=32M`), a leftover developer setting. The real root
  filesystem is **not** in the update file; it lives in the unit's flash.
- Contains USB host, usb-storage, SCSI and networking code.

## VxWorks side (board TD78200-A0, i.e. Marvell MV78200)
- Owns the disks: Marvell's SATA HAL (`mvSataInitAdapter`, EDMA queueing,
  staggered spin-up, NCQ/FBS) and BeyondRAID (zones, scrubbing, compaction,
  disk packs).
- Also carries an iSCSI target library (`iscsiSCSILib.c`) and the user's
  iSCSI IP/MTU settings.
- Talks to Linux through named shared-memory partitions (VxWorks and Linux
  "dynamic shared memory", queue pools, SGL descriptor pool, HLBAT cache,
  ZMDT buffers) plus doorbell interrupts.

## What it means for the port
The disk controller is a standard Marvell part (88SX7042 on PCIe, per
community DroboFS teardowns) with a mainline Linux driver (`sata_mv`). If
VxWorks never starts, Linux can own the controller directly. We lose
BeyondRAID (replace with `mdadm`) and gain a modern kernel.
