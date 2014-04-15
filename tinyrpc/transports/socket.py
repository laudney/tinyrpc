import Queue
from . import ServerTransport


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
        self._queue_class = queue_class
        self.messages = queue_class()

    def receive_message(self):
        return self.messages.get()

    def send_reply(self, context, reply):
        if not isinstance(reply, basestring):
            raise TypeError('string expected')

        context.put(reply)

    def handle(self, sock, address):
        """StreamServer handler function.

        The transport will serve a request by reading the message and putting
        it into an internal buffer. It will then block until another
        concurrently running function sends a reply using
        :py:func:`~tinyrpc.transports.socket.StreamServerTransport.send_reply`.

        The reply will then be sent to the client being handled and handle will
        return.
        """
        msg = sock.makefile().read()
        # create new context
        context = self._queue_class()
        self.messages.put((context, msg))

        # ...and send the reply
        response = context.get()
        yield response
