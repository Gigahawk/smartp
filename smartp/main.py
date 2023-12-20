import logging
import concurrent.futures
import argparse

from pySMART import DeviceList, Device
from .smarttester import SmartTester

logger = logging.getLogger("smartp")

def init_logging(debug: bool):
    ch = logging.StreamHandler()
    if debug:
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.handlers = [ch]
    logger.debug("Initialized")

def run_test(device: Device, test_type: str, debug: bool):
    tester = SmartTester(device, test_type, debug=debug)
    return tester.run_test()

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
    parser.add_argument(
        "--debug",
        help="Enable debug loggin",
        action="store_true"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    init_logging(args.debug)
    devices = DeviceList()
    if devices.devices:
        logger.info(f"Running {args.test} SMART test on: {[d.name for d in devices]}")
        failed_devices = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as ex:
            future_to_device = {
                ex.submit(run_test, d, args.test, args.debug):d for d in devices
            }
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                result = future.result()
                logger.info(f"{device.name}: {result.status}")
                if result.status != "Completed without error":
                    failed_devices += 1
                    logger.error(
                        "Found non-passed status for:\n"
                        f"- device: {device}\n"
                        f"- result: {result}")
        exit(failed_devices)
    else:
        logger.error("No SMART capable disks found")
        exit(0)


