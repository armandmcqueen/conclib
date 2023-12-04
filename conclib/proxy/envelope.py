from pydantic import BaseModel
import conclib
from typing import TypeVar, Type
import pykka

ActorMessageType = TypeVar("ActorMessageType", bound=conclib.ActorMessage)


class ResponseEnvelope(BaseModel):
    """Message sent from the actor system to outside. Will be serialized through redis"""

    message_id: str
    message_type: str
    contents: dict

    def extract(self, cls: Type[ActorMessageType]) -> ActorMessageType:
        """Convert the contents to a specific ActorMessage subclass"""
        actor_msg = cls(**self.contents)
        return actor_msg


class RequestEnvelope(BaseModel):
    """Message sent from outside into the actor system. Will be serialized through redis"""

    message_id: str
    message_type: str
    actor_urn: str
    contents: dict

    def matches(self, cls: Type[ActorMessageType]) -> bool:
        """
        Determine if the message type matches the given class. If so, return True
        """
        return self.message_type == cls.__name__

    def extract(self, cls: Type[ActorMessageType]) -> ActorMessageType:
        """Convert the contents to a specific ActorMessage subclass"""
        actor_msg = cls(**self.contents)
        return actor_msg

    def respond(self, msg: conclib.ActorMessage):
        """Send the response. Wrap in a ResponseEnvelope and send to the RespondingActor"""
        response_envelope = ResponseEnvelope(
            message_id=self.message_id,
            message_type=msg.__class__.__name__,
            contents=msg.model_dump(),
        )
        responding_actor_ref = pykka.ActorRegistry.get_by_urn(
            conclib.constants.RESPONDING_ACTOR
        )
        responding_actor_ref.tell(response_envelope)
