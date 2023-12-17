import queue
import threading
import uuid

import time

from typing import Optional

import pykka

import conclib


# Class to run code every X seconds. This type of work doesn't fit well into the pykka actor model.
# This should generally be used to send a message to an actor every X second and have the logic
# exist inside that actor.
class Ticker(threading.Thread):
    def __init__(
            self,
            interval: float = 10,
            thread_name: str | None = None
    ) -> None:
        self.shutdown_queue = queue.Queue()
        self.interval = interval
        self.next_scheduled_time: Optional[int] = None
        thread_name = thread_name or f"{self.__class__.__name__}-{uuid.uuid4()}"
        super().__init__(name=thread_name)

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


class ChildTicker(Ticker):
    """
    A ticker that is created by a parent actor and sends a type of message to the parent actor.
    This is a utility class to be able to create a PeriodicActor which reduces boilerplate.
    """
    def __init__(
            self,
            interval: float,
            actor_ref: pykka.ActorRef,
            message_type: type[conclib.ActorMessage]
    ) -> None:
        self.actor_ref = actor_ref
        self.message_type = message_type
        # Generate a name based on the Actor class, the frequency, and the message type
        thread_name = f"{self.actor_ref.actor_class.__name__}-{interval}-{self.message_type.__name__}"
        super().__init__(interval=interval, thread_name=thread_name)

    def execute(self):
        self.actor_ref.tell(self.message_type())
