#!/usr/bin/env python3

import json
import os
import subprocess
import sys

def check_volume_name():
    o = subprocess.check_output("docker volume ls", shell=True)
    lines = o.decode('utf-8').split('\n')
    for line in lines:
        if "mx_cache" in line:
            return line.split()[-1]
    return None

def get_volume_json(volume_name):
    o = subprocess.check_output(f"docker volume inspect {volume_name}", shell=True)
    return json.loads(o)

def main():
    volume_name = check_volume_name()
    print(f"Volume name: {volume_name}")
    volume_info = get_volume_json(volume_name)
    mount_point = volume_info[0]['Mountpoint']
    print(mount_point)
    os.system(f"sudo cp -r {mount_point}/* ./mx-cache")

if __name__ == '__main__':
    main()
