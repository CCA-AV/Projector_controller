import time as root_time
import requests

default_login = {"username": "user", "password": "1978"}

control_page = "/html/remote.html"

req_headers = {}

commands = {
    "power_on": {
        "type": "power",
        "mode": "post",
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
        "mode": "post",
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
}


def request_status(user, password, ip):
    try:
        Power_Get = "p:" + str(0x02) + ",c:" + str(0x6000) + ",v:" + str(0)
        myUrl = f"http://{ip}/cgi-bin/webctrl.cgi.elf?" + "&" + Power_Get
        x = requests.post(myUrl)
        data = x.json()
        if data[0]["val"] == [1]:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


def request_source(user, password, ip):
    try:
        Input_Get = "p:" + str(0x02) + ",c:" + str(0x2000) + ",v:" + str(0)
        myUrl = f"http://{ip}/cgi-bin/webctrl.cgi.elf?" + "&" + Input_Get
        x = requests.post(myUrl)
        data = x.json()
        source = data[0]["val"][0]
        if source == 3:
            return "HDMI 1"
        elif source == 13:
            return "HDMI 2"
        elif source == 14:
            return "HDMI 3"
        elif source == 16:
            return "HDMI 4"
        elif source == 8:
            return "DVI-I"
        elif source == 9:
            return "DVI-D"
        elif source == 17:
            return "HDBaseT"
        elif source == 18:
            return "SDI"
        elif source == 19:
            return "DisplayPort"
        else:
            return False
    except Exception as e:
        print(e)
        return None


def time():
    return str(round(root_time.time() * 1000))
