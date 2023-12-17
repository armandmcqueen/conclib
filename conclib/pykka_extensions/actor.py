import uuid
import threading
import pykka
from pykka import ActorRef
from typing import Optional


# Overwrite the logic we don't like in pykka.Actor.
# Changelog:
# - Changed the actor urn so that it can be passed in at creation time.
# - Changed to use a daemon thread.
class Actor(pykka.ThreadingActor):
    URN: str | None = None  # CHANGED
    use_daemon_thread = True  # CHANGED

    def __init__(self, urn: Optional[str] = None, *args, **kwargs):  # noqa  # CHANGED

        ### CHANGED ###
        final_urn = None
        if self.URN:
            final_urn = self.URN
        if urn:
            final_urn = urn
        if not final_urn:
            final_urn = str(uuid.uuid4().urn)
        ### END CHANGED ###

        self.actor_urn = final_urn   # CHANGED
        self.actor_inbox = self._create_actor_inbox()
        self.actor_stopped = threading.Event()
        self._actor_ref = ActorRef(self)
