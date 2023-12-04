import pykka

import conclib
import time


class ExampleReqMessage(conclib.ActorMessage):
    pass


class ExampleRespMessage(conclib.ActorMessage):
    pass


class ExampleActor(conclib.Actor):
    URN = "example_actor"

    def __init__(self):
        # URN is optional here, but recommended so that actor-to-actor
        # communication can use the urn string instead of the actor ref.
        # If using the proxy, the URN is more-or-less required to be able
        # to address the inbound messages.
        super().__init__(urn=self.URN)

    def on_start(self) -> None:
        print("[ExampleActor] ExampleActor started")

    def on_receive(self, message):
        # Check if the message is a RequestEnvelope (i.e. a message that arrived from outside the actor system)
        print(f"[ExampleActor] Received message: {message}")
        if isinstance(message, conclib.RequestEnvelope):
            print("[ExampleActor] Received request envelope")
            req_envelope = message
            # Check which type of message was received and extract it
            if req_envelope.matches(ExampleReqMessage):
                actor_message = req_envelope.extract(ExampleReqMessage)  # noqa
                # Do something with the message
                print("[ExampleActor] Sending response ")
                req_envelope.respond(ExampleRespMessage())
            else:
                raise RuntimeError("Unknown message type")


def main():
    config = conclib.DefaultConfig()

    # Start the backend
    redis_daemon = conclib.start_redis(config=config)
    try:
        conclib.start_proxy(config=config)
        time.sleep(2)

        # Start the example actor
        ExampleActor.start()
        time.sleep(2)

        # Make a request to the actor system
        client = conclib.ProxyClient(config=config)
        print("[test] Sending request")
        result = client.ask_actor(
            "example_actor", ExampleReqMessage(), response_type=ExampleRespMessage
        )
        print("[test] Got response")
        print(f"[test] {type(result)}")  # ExampleRespMessage
        print(f"[test] {result}")

        pykka.ActorRegistry.stop_all()
    finally:
        redis_daemon.shutdown()


if __name__ == "__main__":
    main()
