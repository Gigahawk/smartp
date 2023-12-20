import time
import logging
from pySMART import Device

class SmartTestTimeout(Exception):
    pass

class SmartTestInvalidStartTime(Exception):
    pass


class SmartTester:
    def __init__(self, device: Device, test_type: str, debug: bool=False):
        self.device = device
        self.test_type = test_type
        self.poll_time_min = device.test_polling_time.get(test_type, 100)
        self.wait_time_sec = self.poll_time_min*3*60
        self.start_time = None
        self.logger = logging.getLogger(f"SmartTester-{device.name}")
        # Needed otherwise debug logs get printed twice?
        self.logger.propagate = False
        ch = logging.StreamHandler()
        if debug:
            self.logger.setLevel(logging.DEBUG)
            ch.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
            ch.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        self.logger.handlers = [ch]
        self.logger.debug("Initialized")

    @property
    def time_in_test(self):
        try:
            return time.time() - self.start_time
        except TypeError as err:
            self.logger.error(f"Invalid start time {self.start_time}")
            raise SmartTestInvalidStartTime from err

    def _progress_handler(self, progress: float):
        self.logger.debug(f"Progress: {progress}")
        if self.time_in_test > self.wait_time_sec:
            self.logger.error(f"Test has exceeded {self.wait_time_sec}s")
            self.device.abort_selftest()
            raise SmartTestTimeout

    def run_test(self):
        self.logger.info(
            f"Starting {self.test_type} test, "
            f"waiting up to {self.wait_time_sec}s for test to finish")
        self.device.abort_selftest()
        self.start_time = time.time()
        # Using run_selftest and polling manually with get_selftest_result
        # doesn't seem to work properly, have to use the built in blocking
        # test
        try:
            retcode, result = self.device.run_selftest_and_wait(
                self.test_type, polling=1, progress_handler=self._progress_handler)
            self.logger.info(
                f"Test finished in {self.time_in_test:.2f}s "
                f"with return code {retcode}")
            self.logger.info(result)
            return result
        except SmartTestTimeout:
            return f"Test did not finish within {self.wait_time_sec}s"