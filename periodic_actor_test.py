import conclib


class AccumulateMessage(conclib.ActorMessage):
    pass


class CheckMessage(conclib.ActorMessage):
    pass


class AccumulatorActor(conclib.PeriodicActor):
    URN = "accumulator"
    TICKS = {
        AccumulateMessage: 0.2,
        CheckMessage: 1.02,
    }

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.is_first_check = True
        self.is_first_accumulate = True

    def on_receive(self, message: conclib.ActorMessage) -> None:
        if isinstance(message, AccumulateMessage):
            # Ignore the first check message because it will fire immediately on start
            # and the order is undefined.
            if self.is_first_accumulate:
                self.is_first_accumulate = False
                return

            print("Accumulating")
            self.counter += 1

        elif isinstance(message, CheckMessage):
            # Ignore the first check message because it will fire immediately on start
            # and the order is undefined.
            if self.is_first_check:
                self.is_first_check = False
                return

            print("Checking")
            if self.counter != 5:
                print("Check failed")
                raise RuntimeError("Counter should be 6")
            self.counter = 0
            print("Check passed")
        else:
            raise conclib.errors.UnexpectedMessageError(message)


if __name__ == '__main__':
    import time
    import pykka
    try:
        AccumulatorActor.start()
        time.sleep(5)
    finally:
        pykka.ActorRegistry.stop_all()
