import conclib
from conclib.utils.redisd import redisclient
from conclib import ActorMessage
from conclib.config import ConclibConfig
from conclib.proxy.envelope import RequestEnvelope, ResponseEnvelope

from typing import TypeVar, Type

import time
import json

import uuid

ActorMessageType = TypeVar("ActorMessageType", bound=conclib.ActorMessage)


class ProxyClient:
    def __init__(self, config: ConclibConfig):
        self.config = config
        self.redis_client = redisclient.RedisClient(self.config)

    def ask_actor(
        self,
        actor_urn: str,
        contents: ActorMessage,
        response_type: Type[ActorMessageType],
    ) -> ActorMessageType:
        print("[ProxyClient] Entered ask_actor")
        message_id = f"{actor_urn}-{uuid.uuid4()}"
        message = RequestEnvelope(
            message_id=message_id,
            message_type=contents.__class__.__name__,
            actor_urn=actor_urn,
            contents=contents.model_dump(),
        )
        print("[ProxyClient] Publishing RequestEnvelope")
        self.redis_client.redis_client.publish(
            self.config.inbound_channel_name, message.model_dump_json()
        )
        print("[ProxyClient] Published RequestEnvelope")
        response_channel = self.config.outbound_channel_prefix + message_id
        self.redis_client.pubsub.subscribe(response_channel)
        print(f"[ProxyClient] Subscribed to {response_channel}")

        while True:
            got_message = False
            message = self.redis_client.pubsub.get_message()
            if message:
                # do something with the message

                if message["type"] == "message":
                    print(f"[ProxyClient] Received response message: {message}")
                    data_dict = json.loads(message["data"])
                    resp_envelope = ResponseEnvelope(**data_dict)
                    return resp_envelope.extract(response_type)

                else:
                    print(
                        f"[ProxyClient] Received non-actor message from redis: {message}"
                    )
                got_message = True

            if not got_message:
                time.sleep(0.001)  # be nice to the system :)
