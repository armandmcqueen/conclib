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
    use_daemon_thread = True  # CHANGED

    def __init__(self, urn: Optional[str], *args, **kwargs):  # noqa
        self.actor_urn = urn if urn else uuid.uuid4().urn  # CHANGED
        self.actor_inbox = self._create_actor_inbox()
        self.actor_stopped = threading.Event()
        self._actor_ref = ActorRef(self)
