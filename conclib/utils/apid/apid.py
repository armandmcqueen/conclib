import threading
import time
import subprocess
import sys
import requests


class RestApiDaemonImplementationError(Exception):
    """
    Error raised when the implementing code is incorrect.

    Usually when trying to manipulate the subprocess before it has been created
    """
    pass


class RestApiDidntStartError(Exception):
    pass


class RestApiDaemonThread(threading.Thread):
    daemon = True

    def __init__(self, fast_api_command: str):
        super().__init__(name=f"{self.__class__.__name__}")
        self.fast_api_command = fast_api_command
        self._run_started = False
        self.fast_api_parent_proc = None

    def run(self):
        self._run_started = True
        self.fast_api_parent_proc = subprocess.Popen(
            self.fast_api_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
        )

        for line in iter(self.fast_api_parent_proc.stdout.readline, b""):
            sys.stdout.write(line.decode())

    def shutdown(self):
        if not self._run_started:
            raise RestApiDaemonImplementationError("Trying to shutdown before starting")
        self.fast_api_parent_proc.terminate()

    def wait_for_healthy(
            self,
            healthcheck_url: str,
            startup_healthcheck_timeout: int,
            startup_healthcheck_poll_interval: float = 0.5,
    ):
        """Query the healthcheck endpoint until either it returns a 200 or we timeout."""
        if not self._run_started:
            raise RestApiDaemonImplementationError(
                "Trying to wait for healthy before starting"
            )

        while self.fast_api_parent_proc is None:
            # Wait for the subprocess to be created by the thread
            time.sleep(0.005)

        start_time = time.time()
        max_time = start_time + startup_healthcheck_timeout
        while time.time() < max_time:
            try:
                response = requests.get(healthcheck_url, timeout=0.5)
                if response.status_code == 200:
                    print("✅  REST API is healthy")
                    return
            except requests.exceptions.ConnectionError:
                print(f"⏳  ConnectionError when trying to connect to {healthcheck_url}")
                pass
            except requests.exceptions.ReadTimeout:
                print(f"⌛️ ReadTimeout when trying to connect to {healthcheck_url}")
                pass
            time.sleep(startup_healthcheck_poll_interval)
        raise RestApiDidntStartError(
            f"FastAPI didn't start within {startup_healthcheck_timeout} seconds"
        )


def start_api(
        fast_api_command: str,
        healthcheck_url: str,
        startup_healthcheck_timeout: int,
        startup_healthcheck_poll_interval: float = 0.5
):
    api_thread = RestApiDaemonThread(fast_api_command)
    api_thread.start()
    api_thread.wait_for_healthy(
        healthcheck_url,
        startup_healthcheck_timeout,
        startup_healthcheck_poll_interval
    )
    return api_thread

