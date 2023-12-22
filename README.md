# Concurrency Lib

Template/library for building concurrent systems in Python that use a slightly extended pykka 
for the actor system.  Provides a way to communicate with the actor system from a 
different process via redis (e.g. from a web server that runs in multiple processes).

Extend pykka actors to have uniquely identifiable names (URNs) that can be used to 
send messages. Eventually add additional observability to the actor framework.


## Usage - proxy

In order to communicate with an Actor system from a different process (or machine), 
we use redis as a message bus and run a proxy that sits between redis and the actors. 
The proxy listens to redis for messages, forwards them to the correct Actor, and then 
forwards the response back to the correct location in redis.

Set up the proxy and redis infrastructure.

```python
import conclib
import pykka

# Create a config which specifies where redis is running 
# (and some other rarely used options)  
config = conclib.DefaultConfig()

# Optionally start redis in a background thread (can 
# configure to use existing redis instance instead)
redis_daemon = conclib.start_redis(config=config)

# Start the threads that:
# (1) polls redis for request messages and forwards them to actors
# (2) sends response messages back to redis
conclib.start_proxy(config=config)

# DO YOUR STUFF

# Clean up all the actors (including the proxy) when you are done 
pykka.ActorRegistry.stop_all()

# Shut down redis when you are done to prevent blocking the main process shutting down
redis_daemon.shutdown()

```

Define the request and response messages. Do this in a separate file that is shared
between the actor system and outside the system.
```python
import conclib

class ExampleRequestMessage(conclib.ActorMessage):
    pass

class ExampleResponseMessage(conclib.ActorMessage):
    pass
```

Send requests from outside the actor system. This will block until a response is received 
via redis. 

`ProxyClient` is probably a slightly misleading name since it only communicates with redis 
and `start_proxy` implies that redis is not part of the proxy.
```python
import conclib

config = conclib.DefaultConfig()
client = conclib.ProxyClient(config=config)
result = client.ask_actor("actor_urn", ExampleRequestMessage(), response_type=ExampleResponseMessage)
type(result) # ExampleResponseMessage
```

Handle requests inside the actor system (see ExampleActor below)


## Usage - modified pykka actors

```python
import conclib


class ExampleActor(conclib.Actor):
    URN = "example_actor"
    # URN is optional here, but recommended so that actor-to-actor 
    # communication can use the urn string instead of the actor ref.
    # If using the proxy, the URN is more-or-less required to be able
    # to address the inbound messages.
    
    def __init__(self):
        
        super().__init__()

    def on_receive(self, message):
        # Check if the message is a RequestEnvelope (i.e. a message that arrived from 
        # outside the actor system)
        if isinstance(message, conclib.RequestEnvelope):
            req_envelope = message
            # Check which type of message was received and extract it. We cannot do an 
            # isinstance() check due to how the RequestEnvelope is implemented.
            if req_envelope.matches(ExampleRequestMessage):
                actor_message = req_envelope.extract(ExampleRequestMessage)
                type(actor_message)  # ExampleRequestMessage
                
                # DO SOMETHING WITH THE MESSAGE
                
                # Send a response back to the sender
                req_envelope.respond(ExampleResponseMessage())
            else:
                raise conclib.errors.UnexpectedMessageError(message)
               

```

## Usage - Tickers

A `Ticker` is a thread that runs a function at a regular interval.  In `conclib`, it is 
designed to look similar to an `Actor`. The primary use case is to send a message to an 
`Actor` at a regular interval so that it can have scheduled behavior while still using 
the Actor paradigm (e.g. handling other tasks, clean shutdown, etc). 

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
        super().__init__()
    
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
            raise conclib.errors.UnexpectedMessageError(message)

```

## Usage - run API utility

Conclib includes a utility to run a web server in a background process, similar to redis.

```python
import conclib

# Optionally start the REST API in a background thread. This isn't required
# at all, but is offered as a conclib utility.
# This will launch the server and poll the healthcheck URL until it returns a 200
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

## Usage - PeriodicActor

A very common pattern right now is an actor that runs a function at a regular interval. This
adds a bunch of boilerplate to every actor that needs this behavior. `PeriodicActor` is a
convenience class that handles this boilerplate. It is an actor that has one or more child 
tickers. Each `Ticker` sends a specific `ActorMessage` to the `PeriodicActor` at a regular
interval. 

NOTE: If you override `on_stop`, `on_start` or `on_failure` in a `PeriodicActor`, you must
call `super()` (e.g. `super().on_stop()`) to make sure the tickers are started/stopped correctly.

```python
import conclib

class ExampleTickMessage(conclib.ActorMessage):
    pass


class ExamplePeriodicActor(conclib.PeriodicActor):
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
```
