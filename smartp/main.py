from pprint import pformat
import json
import subprocess

def _is_smart_capable(name):
    path = f"/dev/{name}"
    check_cmd = f"smartctl --json -i {path}".split()
    enable_cmd = f"smartctl -s on {path}".split()
    data = json.loads(
        subprocess.run(check_cmd, capture_output=True, text=True).stdout)
    support = data.get("smart_support")
    if not support or not support.get("available"):
        return False
    if not support.get("enabled"):
        print(f"Enabling SMART on {path}")
        subprocess.run(enable_cmd)
    return True

def run_tests(smart_disks):
    print(f"Running SMART test on: {smart_disks}")
    pass

def main():
    lsblk_cmd = "lsblk -J -d -l -o NAME,SIZE,LABEL,MODEL,SERIAL".split()
    out = subprocess.run(lsblk_cmd, capture_output=True, text=True)
    disks = json.loads(out.stdout)["blockdevices"]
    smart_disks = []
    for d in disks:
        print(f"Checking SMART capability on:\n{pformat(d)}")
        name = d["name"]
        if _is_smart_capable(name):
            print(f"{name} is SMART capable")
            smart_disks.append(name)
        else:
            print(f"{name} is not SMART capable")
    if smart_disks:
        run_tests(smart_disks)
    else:
        print("No SMART capable disks found")
        exit(0)


