# Concurrency Lib

Template for building concurrent systems in Python that use a slightly extended pykka 
for the actor system.  Provide a way to communicate with the actor system from a 
different process by using redis (e.g. from a web server that runs in multiple processes).

Extend pykka actors to have uniquely identifiable names (URNs) that can be used to 
send messages. Eventually add additional observability to the actor framework.


## Usage - proxy

Set up the proxy and redis infrastructure.

```python
import conclib

# Create a config which specifies where redis is running (and some other rarely used 
# options)  
config = conclib.DefaultConfig()

# Optionally start redis in a background thread (can 
# configure to use existing redis instance instead)
redis_daemon = conclib.start_redis(config=config)

# Start the threads that:
# (1) polls redis for request messages and forwards them to actors
# (2) sends response messages back to redis
conclib.start_proxy(config=config)

# DO STUFF

# Shut down redis when you are done to prevent blocking the main process shutting down
redis_daemon.shutdown()

```

Define the request and response messages. Do this in a separate file that is shared
between the actor system and outside the system.
```python
import conclib

class ExampleReqMessage(conclib.ActorMessage):
    pass

class ExampleRespMessage(conclib.ActorMessage):
    pass
```

Send requests from outside the actor system
```python
import conclib

config = conclib.DefaultConfig()
client = conclib.ProxyClient(config=config)
result = client.ask_actor("actor_urn", ExampleReqMessage(), response_type=ExampleRespMessage)
type(result) # ExampleRespMessage
```

Handle requests inside the actor system (see ExampleActor below)


## Usage - modified pykka actors

```python
import conclib


class ExampleActor(conclib.Actor):
    URN = "example_actor"
    def __init__(self):
        # URN is optional here, but recommended so that actor-to-actor 
        # communication can use the urn string instead of the actor ref.
        # If using the proxy, the URN is more-or-less required to be able
        # to address the inbound messages.
        super().__init__(urn=self.URN)

    def on_receive(self, message):
        # Check if the message is a RequestEnvelope (i.e. a message that arrived from outside the actor system)
        if isinstance(message, conclib.RequestEnvelope):
            req_envelope = message
            # Check which type of message was received and extract it
            if req_envelope.matches(ExampleReqMessage):
                actor_message = req_envelope.extract(ExampleReqMessage)
                type(actor_message)  # ExampleReqMessage
                # Do something with the message
                req_envelope.respond(ExampleRespMessage())
            else:
                raise RuntimeError("Unknown message type")
               

```

## Usage - Tickers

A `Ticker` is a thread that runs a function at a regular interval.  In `conclib`, it is 
designed to look similar to an `Actor`.

Note: Currently you need to explicitly shut down the `Ticker` in both `Actor.on_stop` and 
`Actor.on_failure` to make sure `pykka.ActorRegistry.stop_all()` always cleans up all threads. 
I might write a `conclib.ActorRegistry` wrapper around `pykka.ActorRegistry` to make this 
automatic, if it is painful.

```python
import conclib
import pykka
import datetime

class PrintTimeMessage(conclib.ActorMessage):
    pass


class PrintTimeTicker(conclib.Ticker):
    """ Tell the PrintTimeActor to print the current time every 1.5 seconds """
    INTERVAL = 1.5

    def __init__(self, print_time_actor_urn):
        # Save a pointer to the actor so we can send it messages. An ActorRef would 
        # work equally well here, I just prefer to reference by URN.
        self.print_time_actor_urn = print_time_actor_urn
        # Note that tickers do not have a URN because they are not addressable
        super().__init__(interval=self.INTERVAL)

    def execute(self):
        pykka.ActorRegistry.get_by_urn(self.print_time_actor_urn).tell(
            PrintTimeMessage()
        )

class PrintTimeActor(conclib.Actor):
    URN = "print_time_actor"

    def __init__(self):
        self.ticker = PrintTimeTicker(self.URN)
        super().__init__(urn=self.URN)
    
    def on_start(self):
        # Start the ticker when the actor starts and not in __init__. This 
        # prevents actor reference errors.  
        self.ticker.start()
    
    def on_stop(self):
        # Shut down the ticker when the actor stops
        self.ticker.stop()
    
    def on_failure(self, *args, **kwargs):
        # Shut down the ticker when the actor fails
        self.ticker.stop()
    
    def on_receive(self, message):
        if isinstance(message, PrintTimeMessage):
            print(datetime.datetime.utcnow().isoformat())
        else:
            raise RuntimeError("Unknown message type")

```

## Usage - run API utility

Conclib includes a utility to run a web server in a background process, similar to redis.

```python
import conclib

# Optionally start the REST API in a background thread. This isn't required
# at all, but is offered as a conclib utility.
# This launch the server and poll the healthcheck URL until it returns a 200
# or the timeout is reached.
rest_daemon = conclib.start_api(
    fast_api_command="uvicorn conclib.utils.apid.example_api:app  --port 8000",
    healthcheck_url="http://localhost:8000/healthz",
    startup_healthcheck_timeout=10,
)

# DO STUFF

# Shut down the REST API when you are done to prevent blocking the main process shutting down
rest_daemon.shutdown()
```