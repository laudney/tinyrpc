#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG)

from tinyrpc.protocols.stratum import StratumRPCProtocol
from tinyrpc.transports.tcp import StreamClientTransport
from tinyrpc import RPCClient


rpc_client = RPCClient(
    StratumRPCProtocol(),
    StreamClientTransport(('127.0.0.1', 5000))
)

remote_server = rpc_client.get_proxy()

# call a method called 'reverse_string' with a single string argument
result = remote_server.reverse_string('Hello, World!')
print "Server answered:", result

result = remote_server.reverse_string('Goodbye, World!')
print "Server answered:", result
