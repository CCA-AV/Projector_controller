import time as root_time
import requests

default_login = {
    "username": "EPSONWEB",
    "password": "ADMIN"
}

control_page = "/cgi-bin/webconf"

req_headers = {
    "Referer": "http://{ip}/cgi-bin/webconf"
}

commands = {
    "power_on": {
        "type": "power",
        "mode": "get",
        "duplicate": False,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [
            ["KEY","3B"],
            ["_","$$time"]
        ]
    },
    "power_off": {
        "type": "power",
        "mode": "get",
        "duplicate": True,
        "path": "/cgi-bin/directsend?",
        "default_kvjoiner": "=",
        "default_kjoiner": "&",
        "params": [
            ["KEY","3B"],
            ["_","$$time"]
        ]
    },
}

OTHER: Computer (cycle between 1 and 2) : 43
Video (cycle between HDMI1, HDMI2, S-Video, Video) : 46
USB (cycle between USB display and USB): 85
LAN : 8A
Blank (cycle between off/on) : 3E
Freeze (cycle between off/on) : 47
Search : 67

def request_status(user,password,ip):
    p = '05' 
    base_url = f'http://{user}:{password}@{ip}'
    relative_path = '/cgi-bin/webconf'
    full_url = base_url + relative_path
    
    payload = {
        'page': p
    }
    try:
        response = requests.post(full_url, data=payload)
        if "The projector is currently on standby" in response.text:
            return False
        else:
            return True
    
    except requests.exceptions.RequestException as e:
        return False

def request_source(user,password,ip):
    p = '05' 
    base_url = f'http://{user}:{password}@{ip}'
    relative_path = '/cgi-bin/webconf'
    full_url = base_url + relative_path
    
    payload = {
        'page': p
    }
    try:
        response = requests.post(full_url, data=payload)
        if "The projector is currently on standby" in response.text:
            return None
        else:
            text = response.text
            idx = text.find("Source")
            source = text[idx+155:idx+165].strip(" ").split("<")[0]
            return source
    except requests.exceptions.RequestException as e:
        return None

def time():
    return str(round(root_time.time()*1000))
