import Queue
import gevent
from gevent import socket
from . import ServerTransport, ClientTransport


class StreamServerTransport(ServerTransport):
    """TCP socket transport.

    This transport has a few peculiarities: It must be run in a thread,
    greenlet or some other form of concurrent execution primitive.

    This is due to
    :py:func:`~tinyrpc.transports.socket.StreamServerTransport.handle` blocking
    while waiting for a call to
    :py:func:`~tinyrpc.transports.socket.StreamServerTransport.send_reply`.

    The parameter ``queue_class`` must be used to supply a proper queue class
    for the chosen concurrency mechanism (i.e. when using :py:mod:`gevent`,
    set it to :py:class:`gevent.queue.Queue`).

    :param queue_class: The Queue class to use.
    """

    def __init__(self, queue_class=Queue.Queue):
        self._config_buffer = 4096
        self._config_timeout = 5
        self._socket_error = False
        self._queue_class = queue_class
        self.messages = queue_class()

    def receive_message(self):
        return self.messages.get()

    def send_reply(self, context, reply):
        if not isinstance(reply, basestring):
            raise TypeError('string expected')

        context.put(reply)

    def _get_data(self, sock):
        """ Retrieves a data chunk from the socket. """
        sock_error = False
        try:
            data = sock.recv(self._config_buffer)
        except socket.timeout:
            data = None
        except socket.error:
            sock_error = True
            data = None

        return data, sock_error

    def handle(self, sock, address):
        """StreamServer handler function.

        The transport will serve a request by reading the message and putting
        it into an internal buffer. It will then block until another
        concurrently running function sends a reply using
        :py:func:`~tinyrpc.transports.socket.StreamServerTransport.send_reply`.

        The reply will then be sent to the client being handled and handle will
        return.
        """

        sock.settimeout(self._config_timeout)

        chunks = []
        while True:
            data, sock_error = self._get_data(sock)
            if not data:
                break
            chunks.append(data)
            if len(data) < self._config_buffer:
                break

        msg = ''.join(chunks)
        if sock_error:
            sock.close()
        else:
            # create new context
            context = self._queue_class()
            self.messages.put((context, msg))
            # ...and send the reply
            response = context.get()
            sock.send(response)


class StreamClientTransport(ClientTransport):
    """TCP socket based client transport.

    Requires :py:mod:`websocket-python`. Submits messages to a server using the body of
    an ``HTTP`` ``WebSocket`` message. Replies are taken from the response of the websocket.

    The connection is establish on the ``__init__`` because the protocol is connection oriented,
    you need to close the connection calling the close method.

    :param endpoint: The URL to connect the websocket.
    :param kwargs: Additional parameters for :py:func:`websocket.send`.
    """
    def __init__(self, endpoint, **kwargs):
        self._config_timeout = 5
        self._config_buffer = 4096
        self.endpoint = endpoint
        self.request_kwargs = kwargs
        self.sock = gevent.socket.create_connection(self.endpoint, **kwargs)
        self.sock.settimeout(self._config_timeout)

    def send_message(self, message, expect_reply=True):
        if not isinstance(message, basestring):
            raise TypeError('str expected')

        self.sock.send(message)
        if expect_reply:
            chunks = []
            while True:
                try:
                    data = self.sock.recv(self._config_buffer)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
                if len(data) < self._config_buffer:
                    break
            response = ''.join(chunks)
            return response

    def close(self):
        if self.sock is not None:
            self.sock.close()
