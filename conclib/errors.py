from typing import Any

class ConclibBaseException(Exception):
    pass


class UnexpectedMessageError(ConclibBaseException):
    """ When an actor receives a message it doesn't know how to handle """

    def __init__(self, message: Any):
        # TODO: We know exactly where this should be called (Actor.on_receive). Do some callstack magic
        #       to get the actor name? Potentially brittle?
        self.message_type = message.__class__.__name__

    def __str__(self):
        return f"Received unexpected message type: {self.message_type}"
