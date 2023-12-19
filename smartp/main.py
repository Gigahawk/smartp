import time
import concurrent.futures
import argparse
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

def _get_poll_time(path, test_type):
    check_cmd = f"smartctl --json -c {path}".split()
    if test_type == "long":
        test_type == "extended"
    data = json.loads(
        subprocess.run(check_cmd, capture_output=True, text=True).stdout)
    time = data["ata_smart_data"]["self_test"]["polling_minutes"][test_type]
    return time


def run_test(name, test_type):
    path = f"/dev/{name}"
    reset_cmd = f"smartctl -X {path}".split()
    run_cmd = f"smartctl -t {test_type} {path}".split()
    check_cmd = f"smartctl --json -c {path}".split()
    poll_time = _get_poll_time(path, test_type)
    max_time = poll_time*3
    subprocess.run(reset_cmd)
    print(
        f"{name}: starting {test_type} on {name}, "
        f"will take about {poll_time} min")
    start_time = time.time()
    subprocess.run(run_cmd)
    while time.time() - start_time < max_time*60:
        time.sleep(1)
        data = json.loads(
            subprocess.run(check_cmd, capture_output=True, text=True).stdout)
        passed = data["ata_smart_data"]["self_test"]["status"].get("passed")
        if passed is not None:
            print(f"{name}: {test_type} test complete, result: {passed}")
            return passed
    print(f"{name}: test did not finish after {max_time} minutes")
    return False

def run_tests(smart_disks, test_type, threads):
    print(f"Running {test_type} SMART test on: {smart_disks}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        future_to_name = {
            ex.submit(run_test, name, test_type):name for name in smart_disks
        }
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            result = future.result()
            print(f"{name}: {result}")

def parse_args():
    parser = argparse.ArgumentParser(
        prog="smartp",
        description=(
            "Run a smart test on all SMART capable drives attached to "
            "the system"
        )
    )
    parser.add_argument(
        "-t", "--test",
        choices=["short", "long", "conveyance"],
        default="short",
        help="Type of test to run",
        )
    parser.add_argument(
        "--threads",
        help="Number of tests to run simultaneously",
        default=20,
        type=int
    )
    return parser.parse_args()

def main():
    args = parse_args()
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
        run_tests(smart_disks, args.test, args.threads)
    else:
        print("No SMART capable disks found")
        exit(0)


