import time as root_time
import requests

default_login = {"username": "EPSONWEB", "password": "ADMIN"}

control_page = "/cgi-bin/webconf"

req_headers = {"Referer": "http://{ip}/cgi-bin/webconf"}

commands = {
    "power_on": {
        "type": "power",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "3B"], ["_", "$$time"]],
    },
    "power_off": {
        "type": "power",
        "mode": "get",
        "duplicate": True,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "3B"], ["_", "$$time"]],
    },
    # Cycle / toggle keys from the original Epson remote protocol
    "OTHER": {  # Computer (cycle between 1 and 2)
        "type": "source_cycle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "43"], ["_", "$$time"]],
    },
    "VIDEO": {  # HDMI1, HDMI2, S-Video, Video
        "type": "source_cycle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "46"], ["_", "$$time"]],
    },
    "USB": {  # USB display, USB
        "type": "source_cycle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "85"], ["_", "$$time"]],
    },
    "LAN": {
        "type": "source_cycle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "8A"], ["_", "$$time"]],
    },
    "BLANK": {
        "type": "toggle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "3E"], ["_", "$$time"]],
    },
    "FREEZE": {
        "type": "toggle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "47"], ["_", "$$time"]],
    },
    "A/V MUTE": {
        "type": "toggle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "3E"], ["_", "$$time"]],
    },
    "SEARCH": {
        "type": "toggle",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [["KEY", "67"], ["_", "$$time"]],
    },
}

# Mapping from human-readable source names (as returned by request_source)
# to the cycle command that should be used to reach them.
TARGET_TO_CYCLE_COMMAND = {
    # Video sources
    "HDMI1": "VIDEO",
    "HDMI 1": "VIDEO",
    "HDMI2": "VIDEO",
    "HDMI 2": "VIDEO",
    "S-Video": "VIDEO",
    "Video": "VIDEO",
    "VIDEO": "VIDEO",
    # Computer sources
    "Computer1": "OTHER",
    "Computer 1": "OTHER",
    "COMPUTER1": "OTHER",
    "Computer2": "OTHER",
    "Computer 2": "OTHER",
    "COMPUTER2": "OTHER",
    # USB sources
    "USB": "USB",
    "USB Display": "USB",
    # Network
    "LAN": "LAN",
}


def request_status(user, password, ip):
    p = "05"
    base_url = f"http://{user}:{password}@{ip}"
    payload = {"page": p}
    full_url = f"{base_url}/cgi-bin/webconf"
    try:
        response = requests.post(full_url, data=payload)
        return "The projector is currently on standby" not in response.text
    except requests.exceptions.RequestException as e:
        return False


def request_source(user, password, ip):
    p = "05"
    base_url = f"http://{user}:{password}@{ip}"
    payload = {"page": p}
    full_url = f"{base_url}/cgi-bin/webconf"
    try:
        response = requests.post(full_url, data=payload)
        if "The projector is currently on standby" in response.text:
            return None
        text = response.text
        idx = text.find("Source")
        return text[idx + 155 : idx + 166].strip(" ").split("<")[0]
    except requests.exceptions.RequestException as e:
        return None


def time():
    return str(round(root_time.time() * 1000))
