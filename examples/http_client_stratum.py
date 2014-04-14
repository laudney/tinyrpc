#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tinyrpc.protocols.stratum import StratumRPCProtocol
from tinyrpc.transports.http import HttpPostClientTransport
from tinyrpc import RPCClient

rpc_client = RPCClient(
    StratumRPCProtocol(),
    HttpPostClientTransport('http://127.0.0.1:5000/')
)

remote_server = rpc_client.get_proxy()

# call a method called 'reverse_string' with a single string argument
result = remote_server.reverse_string('Hello, World!')

print "Server answered:", result
