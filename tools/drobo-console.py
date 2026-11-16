#!/usr/bin/env python3
"""drobo-console.py: drive a Drobo's U-Boot serial console safely.

  pip install pyserial

  drobo-console.py PORT log                 Just record the console to a file.
  drobo-console.py PORT catch               Tap space until the U-Boot prompt.
  drobo-console.py PORT run FILE [--catch]  Type the commands in FILE.

PORT is e.g. COM5, /dev/ttyUSB0 or /dev/cu.usbserial-XXXX. Everything seen
on the console is appended to --log (default: drobo-console.log).

Why a tool: Drobo's U-Boot has no boot countdown (bootdelay is 0) and drops
characters that arrive too fast. So this tool
  * taps space every 100 ms until the prompt appears: start it, THEN plug in;
  * types one character at a time and checks the echo of the whole line
    before pressing Enter; a garbled line is cancelled (Ctrl-C) and retyped,
    so a half-typed command is never run;
  * waits for the prompt before sending the next line;
  * refuses commands that write flash or U-Boot's environment, or that are
    known to hang this U-Boot, unless you pass --allow CMD for each one.

In a command FILE, blank lines and lines starting with # are skipped. After
a `go` line the tool stops typing and records the console until Ctrl-C.
"""
import argparse
import re
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial is missing: pip install pyserial")

# First word(s) of commands that change flash/env or are known to hang.
BLOCKED = [
    "saveenv", "resetenv", "flinfo", "erase", "protect", "bootm", "bubt",
    "cp", "mw", "nand", "sf", "run", "source", "usb write", "ide write",
    "mmc write",
]


def blocked(line, allow):
    words = line.split()
    if not words:
        return None
    first = words[0].split(".")[0]          # cp.b -> cp
    two = " ".join([first] + words[1:2])
    for b in BLOCKED:
        if (first == b or two == b) and b not in allow:
            return b
    return None


class Console:
    def __init__(self, port, baud, logpath, prompt, char_delay):
        self.ser = serial.Serial(port, baud, timeout=0.05)
        self.log = open(logpath, "ab")
        self.prompt = re.compile(prompt.encode())
        self.char_delay = char_delay
        self.buf = b""

    def pump(self):
        """Read whatever arrived; log it and show it."""
        data = self.ser.read(4096)
        if data:
            self.log.write(data)
            self.log.flush()
            sys.stdout.write(data.decode("latin-1"))
            sys.stdout.flush()
            self.buf = (self.buf + data)[-65536:]
        return data

    def at_prompt(self):
        return bool(self.prompt.search(self.buf[-200:]))

    def wait_prompt(self, timeout):
        end = time.time() + timeout
        while time.time() < end:
            self.pump()
            if self.at_prompt():
                # make sure output has really stopped
                time.sleep(0.2)
                if not self.pump() and self.at_prompt():
                    return True
        return False

    def catch(self, timeout):
        print("Tapping space. Plug the Drobo in now (Ctrl-C to give up).",
              file=sys.stderr)
        end = time.time() + timeout
        while time.time() < end:
            self.ser.write(b" ")
            time.sleep(0.1)
            self.pump()
            if self.at_prompt():
                # clear the spaces we typed: Ctrl-C gives a fresh prompt
                self.ser.write(b"\x03")
                self.buf = b""
                return self.wait_prompt(5)
        return False

    def type_line(self, line, tries=3):
        """Type `line`, confirm its echo, then press Enter. False if it
        could not be typed cleanly; in that case nothing was run."""
        for _ in range(tries):
            self.buf = b""
            for ch in line.encode():
                self.ser.write(bytes([ch]))
                time.sleep(self.char_delay)
                self.pump()
            end = time.time() + 1.0
            while time.time() < end and line.encode() not in self.buf:
                self.pump()
            if self.buf.strip() == line.encode().strip():
                self.buf = b""
                self.ser.write(b"\r")
                return True
            print("\n[echo mismatch: cancelling and retyping]", file=sys.stderr)
            self.ser.write(b"\x03")
            self.buf = b""
            if not self.wait_prompt(5):
                return False
        return False

    def record(self):
        print("\n[recording; Ctrl-C to stop]", file=sys.stderr)
        try:
            while True:
                self.pump()
        except KeyboardInterrupt:
            print("\n[stopped]", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port")
    ap.add_argument("action", choices=["log", "catch", "run"])
    ap.add_argument("file", nargs="?", help="command file for `run`")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--log", default="drobo-console.log")
    ap.add_argument("--prompt", default=r"(Marvell|U-Boot)>> ?$",
                    help="regex for the U-Boot prompt")
    ap.add_argument("--catch", action="store_true",
                    help="with `run`: catch U-Boot first")
    ap.add_argument("--catch-timeout", type=float, default=180)
    ap.add_argument("--cmd-timeout", type=float, default=120,
                    help="seconds to wait for the prompt after each command")
    ap.add_argument("--char-delay", type=float, default=0.02)
    ap.add_argument("--allow", action="append", default=[], metavar="CMD",
                    help="permit one normally refused command, e.g. --allow saveenv")
    a = ap.parse_args()

    lines = []
    if a.action == "run":
        if not a.file:
            ap.error("run needs a command FILE")
        for raw in open(a.file):
            line = raw.strip()
            if line and not line.startswith("#"):
                lines.append(line)
        # Check the whole file before typing anything.
        for line in lines:
            b = blocked(line, a.allow)
            if b:
                sys.exit("Refusing %r: `%s` can change flash/environment or hang "
                         "this U-Boot. Pass --allow '%s' if you are sure." % (line, b, b))

    con = Console(a.port, a.baud, a.log, a.prompt, a.char_delay)
    con.log.write(("\n=== %s %s ===\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                          a.action)).encode())
    if a.action == "log":
        con.record()
        return

    if a.action == "catch" or a.catch:
        if not con.catch(a.catch_timeout):
            sys.exit("\nNo U-Boot prompt seen. Check wiring (TX/RX swapped? "
                     "ground?) and that this is the U-Boot console.")
        print("\n[at the U-Boot prompt]", file=sys.stderr)
    if a.action == "catch":
        return

    # run
    if not a.catch:
        con.ser.write(b"\r")
        if not con.wait_prompt(5):
            sys.exit("Not at a U-Boot prompt. Use --catch, or run `catch` first.")
    for line in lines:
        if not con.type_line(line):
            sys.exit("\nCould not type %r cleanly; stopped. Nothing further was sent." % line)
        if line.split()[0] == "go":
            con.record()
            return
        if not con.wait_prompt(a.cmd_timeout):
            sys.exit("\nNo prompt after %r; stopped." % line)
    print("\n[all commands done; log in %s]" % a.log, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except serial.SerialException as e:
        sys.exit("\nSerial port problem (adapter unplugged, or port open in "
                 "another program?): %s" % e)
    except KeyboardInterrupt:
        sys.exit("\n[interrupted]")
