import queue
import threading
import uuid

import time

from typing import Optional


# Class to run code every X seconds. This type of work doesn't fit well into the pykka actor model.
# This should generally be used to send a message to an actor every X second and have the logic
# exist inside that actor.
class Ticker(threading.Thread):
    def __init__(self, interval=10) -> None:
        self.shutdown_queue = queue.Queue()
        self.interval: int = interval
        self.next_scheduled_time: Optional[int] = None
        super().__init__(name=f"{self.__class__.__name__}-{uuid.uuid4()}")

    def stop(self):
        self.shutdown_queue.put(None)

    # This should be overwritten by subclass
    def execute(self):
        print(time.time())

    def run(self):
        self.next_scheduled_time = time.time()
        while True:
            try:
                wait_time = max(0.0, self.next_scheduled_time - time.time())

                # Block for wait_time unless we receive a shutdown message. If we don't get a
                # shutdown message, EXCEPT clause gets executed
                _ = self.shutdown_queue.get(block=True, timeout=wait_time)

                return

            except queue.Empty:
                self.next_scheduled_time = time.time() + self.interval
                self.execute()
