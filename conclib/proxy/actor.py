# The actor side of the system. Polling thread and responding actor, plus
# start_proxy utility to start them in one line
from types import TracebackType

import conclib

from conclib.config import ConclibConfig
from conclib.utils.redisd.redisclient import RedisClient
from conclib.proxy.envelope import RequestEnvelope, ResponseEnvelope

from typing import Optional

import threading
import json
import pykka
import time


class RedisPollingThread(threading.Thread):
    def __init__(self, config: ConclibConfig):
        super().__init__(name=f"{self.__class__.__name__}")
        self.shutdown_event = threading.Event()
        self.config = config
        self.redis_client = None
        self.redis_p = None

    def shutdown(self):
        self.shutdown_event.set()

    def run(self):
        self.redis_client = RedisClient(config=self.config)
        self.redis_client.pubsub.subscribe(self.config.inbound_channel_name)
        print(f"[RedisPollingThread] Subscribed to {self.config.inbound_channel_name}")
        while True:
            if self.shutdown_event.is_set():
                print("[RedisPollingThread] Shutting down")
                return

            got_message = False
            message = self.redis_client.pubsub.get_message()
            if message:
                got_message = True
                if message["type"] == "message":
                    print(f"[RedisPollingThread] Received message: {message}")
                    data_dict = json.loads(message["data"])
                    req_envelope = RequestEnvelope(**data_dict)
                    actor_urn = req_envelope.actor_urn

                    # This is a tell because the response is routed to the RespondingActor
                    # instead of being handled by this thread (to avoid blocking)
                    actor_ref = pykka.ActorRegistry.get_by_urn(actor_urn)
                    actor_ref.tell(req_envelope)

                else:
                    # These are system messages we don't need to handle
                    pass

            if not got_message:
                time.sleep(0.001)  # be nice to the system :)


class RespondingActor(conclib.Actor):
    def __init__(self, config: ConclibConfig):
        self.config = config
        self.redis_client: Optional[RedisClient] = None
        self.redis_polling_thread = RedisPollingThread(config)

        super().__init__(urn=conclib.constants.RESPONDING_ACTOR)

    def on_start(self):
        self.redis_client = RedisClient(self.config)
        self.redis_polling_thread.start()

    def on_stop(self) -> None:
        self.redis_polling_thread.shutdown()
        self.redis_polling_thread.join()

    def on_failure(
        self,
        exception_type: Optional[type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.redis_polling_thread.shutdown()
        self.redis_polling_thread.join()

    def on_receive(self, message):
        print("[RespondingActor] on_receive reached")
        if not isinstance(message, ResponseEnvelope):
            raise RuntimeError(
                "RespondingActor received message that is not a ResponseEnvelope. This is an implementation bug"
            )
        response_channel = self.config.outbound_channel_prefix + message.message_id
        print(f"[RespondingActor] Publishing ResponseEnvelope to {response_channel}")
        self.redis_client.redis_client.publish(
            channel=response_channel, message=message.model_dump_json()
        )


def start_proxy(config: ConclibConfig):
    RespondingActor.start(config)
