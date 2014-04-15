#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import gevent.queue
from gevent.server import StreamServer
from tinyrpc.protocols.stratum import StratumRPCProtocol
from tinyrpc.transports.socket import StreamServerTransport
from tinyrpc.server.gevent import RPCServerGreenlets
from tinyrpc.dispatch import RPCDispatcher

dispatcher = RPCDispatcher()
transport = StreamServerTransport(queue_class=gevent.queue.Queue)

# start wsgi server as a background-greenlet
stream_server = StreamServer(('127.0.0.1', 5000), transport.handle)
gevent.spawn(stream_server.serve_forever)

rpc_server = RPCServerGreenlets(
    transport,
    StratumRPCProtocol(),
    dispatcher
)

@dispatcher.public
def reverse_string(s):
    return s[::-1]

# in the main greenlet, run our rpc_server
rpc_server.serve_forever()
