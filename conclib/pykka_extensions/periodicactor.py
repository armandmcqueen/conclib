import conclib
from conclib.pykka_extensions.ticker import ChildTicker
from types import TracebackType
from typing import Optional

TickFrequency = float
ActorMessageType = type[conclib.ActorMessage]


class PeriodicActor(conclib.Actor):
    """
    Actor with one or more Tickers built-in.

    IMPORTANT: If you override on_start, on_stop, or on_failure, you must class
    super() on them so that startup and cleanup happen.
    """
    TICKS: dict[ActorMessageType, TickFrequency] = {}

    def __init__(self):
        super().__init__()
        self.tickers: list[ChildTicker] = []
        for message_type, interval in self.TICKS.items():
            new_ticker = ChildTicker(
                interval=interval,
                actor_ref=self.actor_ref,
                message_type=message_type
            )
            self.tickers.append(new_ticker)

    def start_tickers(self):
        for ticker in self.tickers:
            ticker.start()

    def stop_tickers(self):
        for ticker in self.tickers:
            ticker.stop()

    def on_start(self) -> None:
        """ If this is overridden, super().on_start() must be called. """
        self.start_tickers()

    def on_stop(self) -> None:
        """ If this is overridden, super().on_stop() must be called. """
        self.stop_tickers()

    def on_failure(
        self,
        exception_type: Optional[type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """ If this is overridden, super().on_failure() must be called. """
        self.stop_tickers()


class ExampleTickMessage(conclib.ActorMessage):
    pass


class ExamplePeriodicActor(PeriodicActor):
    URN = "example_periodic_actor"
    # This is the type of message, and how often to send it
    TICKS = {
        ExampleTickMessage: 0.5,
    }

    def on_receive(self, message: conclib.ActorMessage) -> None:
        if isinstance(message, ExampleTickMessage):
            print("Tick")
        else:
            raise conclib.errors.UnexpectedMessageError(message)


if __name__ == '__main__':
    import time
    import pykka

    ExamplePeriodicActor.start()
    try:
        time.sleep(5)
    finally:
        pykka.ActorRegistry.stop_all()