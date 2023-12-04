from conclib.config import ConclibConfig
import subprocess
import threading
import sys
import time


class RedisDaemonThread(threading.Thread):
    def __init__(self, config: ConclibConfig):
        super().__init__(name=f"{self.__class__.__name__}", daemon=True)
        self.config = config
        self.redis_proc = None

    def run(self):
        redis_command = f"redis-server --port {self.config.redis_port}"
        self.redis_proc = subprocess.Popen(
            redis_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )

        # TODO: Add clean shutdown mechanism?
        for line in iter(self.redis_proc.stdout.readline, b""):
            sys.stdout.write(line.decode())

    def shutdown(self):
        self.redis_proc.terminate()


def start_redis(config: ConclibConfig) -> RedisDaemonThread:
    redis_thread = RedisDaemonThread(config=config)
    redis_thread.start()
    time.sleep(2)

    # TODO: Add blocking check until redis is ready
    return redis_thread
