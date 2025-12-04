"""
In‑process test projector that behaves like the Christie HTTP API,
but without performing any real HTTP or network I/O.

The rest of the application can treat this exactly like a normal
projector module (it exposes `commands`, `request_status`,
`request_source`, etc.), but all state is simulated in memory.
"""

import time as root_time
from typing import Dict
import random

# Kept only so the rest of the app can construct URLs; they are never used
# for real HTTP traffic when this module is active.
default_login = {"username": "user", "password": "1978"}

# Dummy control page – not actually served; useful if you ever want to
# point a local HTTP simulator at it.
control_page = "/html/remote.html"

# No special headers required for the simulated projector
req_headers: Dict[str, str] = {}

# ---------------------------------------------------------------------------
# Command definitions (mirrors christie.py so the UI looks the same)
# ---------------------------------------------------------------------------

commands = {
    "power_on": {
        "type": "power",
        "mode": "internal",  # special mode, handled without HTTP
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x001D)],
        ],
    },
    "power_off": {
        "type": "power",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x001E)],
        ],
    },
    "HDBASET": {
        "type": "source",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x001F)],
        ],
    },
    "HDMI1": {
        "type": "source",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x0012)],
        ],
    },
    "HDMI2": {
        "type": "source",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x000F)],
        ],
    },
    "COMPUTER1": {
        "type": "source",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x0010)],
        ],
    },
    "FREEZE": {
        "type": "feature",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x00B4)],
        ],
    },
    "MUTE": {
        "type": "feature",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x0052)],
        ],
    },
    "BLANK": {
        "type": "feature",
        "mode": "internal",
        "duplicate": False,
        "path": "/cgi-bin/webctrl.cgi.elf?&",
        "default_kvjoiner": ":",
        "default_kjoiner": ",",
        "params": [
            ["p", str(0x01)],
            ["c", str(0x1213)],
            ["v", str(2)],
            ["v", str(0x0041)],
        ],
    },
}


# ---------------------------------------------------------------------------
# Internal simulated state
# ---------------------------------------------------------------------------

_POWER_ON: bool = bool(random.randint(0, 1))
_CURRENT_SOURCE: str = "HDMI 1"
_FEATURES: Dict[str, bool] = {
    "FREEZE": False,
    "MUTE": False,
    "BLANK": False,
}


def _set_source_from_command(command_name: str) -> None:
    global _CURRENT_SOURCE
    global _POWER_ON
    if not _POWER_ON:
        raise Exception("Projector is not powered on")
    if command_name == "HDMI1":
        _CURRENT_SOURCE = "HDMI 1"
    elif command_name == "HDMI2":
        _CURRENT_SOURCE = "HDMI 2"
    elif command_name == "HDBASET":
        _CURRENT_SOURCE = "HDBaseT"
    elif command_name == "COMPUTER1":
        _CURRENT_SOURCE = "Computer 1"


def handle_command(command_name: str, projector_instance) -> None:
    """
    Entry point used by `Projector._execute_command` for this module.

    It mutates in‑memory state instead of performing any HTTP requests.
    """
    global _POWER_ON, _FEATURES

    root_time.sleep(1)
    if command_name == "power_on":
        _POWER_ON = True
        # Keep whatever source was last chosen
    elif command_name == "power_off":
        _POWER_ON = False
    elif command_name in ("HDMI1", "HDMI2", "HDBASET", "COMPUTER1"):
        _set_source_from_command(command_name)
    elif command_name in _FEATURES:
        # Simple toggle behaviour for features
        _FEATURES[command_name] = not _FEATURES[command_name]


def request_status(user, password, ip):
    """
    Mirror the Christie semantics: True when powered on, False otherwise.
    """
    print(password, user, ip)
    return _POWER_ON


def request_source(user, password, ip):
    """
    Return the current source in the same format as Christie.request_source.
    """
    if not _POWER_ON:
        return None
    return _CURRENT_SOURCE


def time():
    return str(round(root_time.time() * 1000))
