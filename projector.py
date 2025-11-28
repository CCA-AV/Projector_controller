import time
import math
import requests
import json
import importlib

class Projector:
    def __init__(self, ip, projector_type):
        self.ip = ip
        self.projector_type = projector_type
        self.projector_lib = importlib.import_module(f"projectors.{projector_type}")

    def generate_command(self, command):
        command = self.projector_lib.commands[command]
        user = self.projector_lib.default_login['username']
        password = self.projector_lib.default_login['password']
        url = f"http://{user}:{password}@{self.ip}{command['path']}"
        for param in command["params"]:
            key = param[0]
            value = param[1]
            if value == "$$time":
                value = self.projector_lib.time()
            url += key + command["default_kvjoiner"] + value + command["default_kjoiner"]
        url = url.strip(command["default_kjoiner"])
        return url, command["mode"], command["duplicate"]

    def on(self):
        url, mode, duplicate = self.generate_command("power_on")

        if mode == "get":
            caller = requests.get
        else:
            caller = requests.post
            
        caller(url, headers= self.projector_lib.req_headers)
        if duplicate:
            time.sleep(.5)
            url, _, _ = self.generate_command("power_on")
            caller(url, headers= self.projector_lib.req_headers)

    def off(self):
        url, mode, duplicate = self.generate_command("power_off")

        if mode == "get":
            caller = requests.get
        else:
            caller = requests.post
            
        x = caller(url, headers= self.projector_lib.req_headers)
        if duplicate:
            time.sleep(.5)
            url, _, _ = self.generate_command("power_off")
            caller(url, headers= self.projector_lib.req_headers)

    def status(self):
        ip = self.ip
        user = self.projector_lib.default_login['username']
        password = self.projector_lib.default_login['password']
        return self.projector_lib.request_status(user,password,ip)

    def source(self):
        ip = self.ip
        user = self.projector_lib.default_login['username']
        password = self.projector_lib.default_login['password']
        return self.projector_lib.request_source(user,password,ip)

proj = Projector("192.168.0.28", "christie")

print(proj.source())
"""with open("data.json","w") as f:
    json.dump(headers, f)
    """
def determine(ip):
    try:
        x = requests.get(f"http://{ip}/html/remote.html", timeout = .5)
        if x.status_code in (401, 200):
            return "Cristie"
        elif x.status_code == 404:
            x = requests.get(f"http://{ip}/cgi-bin/webconf", headers = headers, timeout = .5)
            if x.status_code in (401, 200):
                return "Epson"
        return None
    except Exception as e:
        return None
    
def discover():
    for i in range(0,255):
        ip = f"192.168.0.{i}"
        projector = determine(ip)
        if projector:
            print(ip, projector)
