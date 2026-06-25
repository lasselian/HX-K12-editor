"""Cross-platform access to the HX-K12 vendor HID interface.

Two interchangeable backends, picked automatically:

* **hidraw** (Linux only, no dependencies) — writes ``/dev/hidrawN`` directly.
  This is what runs out of the box on Linux.
* **hidapi** (Windows / macOS / Linux) — uses the ``hid`` Python binding
  (``pip install hidapi``). Required on non-Linux platforms.

Both select the *vendor* interface, whose HID report descriptor uses the
vendor-defined usage page ``0xFF00``. See PROTOCOL.md.
"""

import glob
import os
import sys

from . import protocol


class DeviceNotFound(Exception):
    pass


class DeviceError(Exception):
    pass


# --------------------------------------------------------------------------
# hidraw backend (Linux, dependency-free)
# --------------------------------------------------------------------------
def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return b""


def _uevent(path):
    d = {}
    for line in _read(path).decode("utf-8", "replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    return d


def find_hidraw(vid=protocol.VID, pid=protocol.PID):
    """Return the /dev/hidrawN path for the vendor (0xFF00) interface."""
    matches = []
    for dev in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        name = os.path.basename(dev)
        ue = _uevent(os.path.join(dev, "device", "uevent"))
        hid_id = ue.get("HID_ID", "").upper()      # 0003:00001189:00008840
        if f"{vid:08X}" not in hid_id or f"{pid:08X}" not in hid_id:
            continue
        rd = _read(os.path.join(dev, "device", "report_descriptor"))
        matches.append((f"/dev/{name}", rd[:3] == b"\x06\x00\xff"))
    for path, is_vendor in matches:
        if is_vendor:
            return path
    if matches:
        return matches[0][0]
    raise DeviceNotFound(
        f"No hidraw node for {vid:04x}:{pid:04x}. Is the pad plugged in?"
    )


class HidrawBackend:
    name = "hidraw"

    def __init__(self, vid=protocol.VID, pid=protocol.PID):
        self.path = find_hidraw(vid, pid)
        self._fd = None

    def open(self):
        try:
            self._fd = os.open(self.path, os.O_RDWR)
        except PermissionError as e:
            raise PermissionError(
                f"No write access to {self.path}. Install the udev rule "
                f"(udev/99-hx-k12.rules) and replug the pad."
            ) from e

    def write(self, report: bytes):
        os.write(self._fd, report)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


# --------------------------------------------------------------------------
# hidapi backend (cross-platform)
# --------------------------------------------------------------------------
class HidapiBackend:
    name = "hidapi"

    def __init__(self, vid=protocol.VID, pid=protocol.PID):
        try:
            import hid
        except ImportError as e:
            raise DeviceError(
                "The 'hid' module is required on this platform. "
                "Install it with: pip install hidapi"
            ) from e
        self._hid = hid
        self.vid, self.pid = vid, pid
        self.path = self._find_path()
        self._dev = None

    def _find_path(self):
        infos = self._hid.enumerate(self.vid, self.pid)
        if not infos:
            raise DeviceNotFound(
                f"No HID device {self.vid:04x}:{self.pid:04x}. Is the pad plugged in?"
            )
        for info in infos:
            if info.get("usage_page") == 0xFF00:
                return info["path"]
        # fall back to the first interface if usage pages aren't reported
        return infos[0]["path"]

    def open(self):
        self._dev = self._hid.device()
        try:
            self._dev.open_path(self.path)
        except (OSError, IOError) as e:
            raise PermissionError(
                f"Could not open the device ({e}). On Linux install the udev "
                f"rule and replug; on macOS grant input-monitoring permission."
            ) from e

    def write(self, report: bytes):
        # hidapi takes the report-ID byte as the first byte of the buffer,
        # which is exactly how protocol.encode_report() already frames it.
        self._dev.write(report)

    def close(self):
        if self._dev is not None:
            self._dev.close()
            self._dev = None


def _pick_backend():
    """hidraw on Linux (no deps); hidapi elsewhere."""
    if sys.platform.startswith("linux") and glob.glob("/sys/class/hidraw/hidraw*"):
        return HidrawBackend
    return HidapiBackend


# --------------------------------------------------------------------------
# Public facade
# --------------------------------------------------------------------------
class Device:
    def __init__(self, backend=None, vid=protocol.VID, pid=protocol.PID):
        self._backend = (backend or _pick_backend())(vid, pid)

    @property
    def backend_name(self):
        return self._backend.name

    @property
    def path(self):
        return self._backend.path

    def __enter__(self):
        self._backend.open()
        return self

    def __exit__(self, *exc):
        self._backend.close()

    def write(self, report: bytes):
        self._backend.write(report)

    def program_key(self, cfg, commit=True):
        """Write a single KeyConfig and optionally commit to flash."""
        self.write(cfg.encode_report())
        if commit:
            self.write(protocol.flash_report())

    def flash_layout(self, configs, progress=None):
        """Write a whole layout, then a single flash-commit.

        Mirrors the OEM "Download": every key report is sent first, then one
        ``AA AA`` commit. Writing the full set (rather than one key) preserves
        the other keys. ``configs`` is an iterable of KeyConfig.
        ``progress`` (optional) is called as ``progress(done, total)``.
        """
        configs = list(configs)
        total = len(configs)
        for i, cfg in enumerate(configs, 1):
            self.write(cfg.encode_report())
            if progress:
                progress(i, total)
        self.write(protocol.flash_report())


def available():
    """Return (ok, message) describing whether the device can be reached."""
    try:
        dev = Device()
        return True, f"{dev.path} via {dev.backend_name}"
    except (DeviceNotFound, DeviceError) as e:
        return False, str(e)
