# Session logs

Console captures from real units go here, so every finding can be traced
back to what the hardware printed.

Naming: `<unit>-<what>.log`, for example `b810n-stock-uart0.log`,
`b810n-uboot.log`, `b810n-probe.log`, `b810n-ramboot.log`.
`tools/drobo-console.py --log logs/NAME.log` appends with a timestamp.

Before committing a log, look through it for things you may not want
public: MAC addresses (`ethaddr`), serial numbers, share names, and any
network settings from the stock firmware.

After each session, update the "Confirmed" column in
[../docs/hardware-notes.md](../docs/hardware-notes.md) and the roadmap in
the main README.
