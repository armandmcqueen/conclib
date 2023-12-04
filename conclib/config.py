from dataclasses import dataclass


@dataclass
class ConclibConfig:
    redis_port: int
    redis_host: str
    inbound_channel_name: str
    outbound_channel_prefix: str


class DefaultConfig(ConclibConfig):
    def __init__(self):
        super().__init__(
            redis_port=6379,
            redis_host="localhost",
            inbound_channel_name="out2actor",
            outbound_channel_prefix="actor2out/",
        )
