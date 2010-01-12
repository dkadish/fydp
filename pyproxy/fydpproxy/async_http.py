import asyncore
import asynchat
import copy
import collections
import logging
import socket
from httpmsg import HttpRequest, HttpResponse

# Constants and other useful bits of module-level data.
CLRF = "\r\n"
HTTP_SEP = CLRF * 2
_HEADERS = 'headers'
_CONTENT = 'content'
_CHUNKED_SIZE = 'chunked-size'
_CHUNKED_CONTENT = 'chunked-content'
_CHUNKED_TRAILER = 'chunked-trailer'

class Server(asyncore.dispatcher):
    def __init__(self, host, port, request_handler):
        asyncore.dispatcher.__init__(self)
        # Fun fact: this will allow us to pick-up a socket that is currently in
        # TIME_WAIT (i.e. a socket that is waiting to die)
        self.request_handler = request_handler
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.address = self.socket.getsockname()
        self.listen(1)

    # TODO: If something really exceptional happens, we should devise some sort
    # of exit strategy
    def handle_expt(self):
        pass

    def handle_connect(self):
        """
        Called when the active opener's socket actually makes a connection; at
        this point, I think the connection is being managed by our
        RequestHandler.
        """
        pass

    def handle_accept(self):
        """
        Caled when when a connection can be established with a new remote
        endpoint that has issued a connect() call for the local endpoint.

        NB: If I understand this correctly, an accept is the equivalent of a
        'pre-connect'; the remote endpoint hasn't actually connected yet.
        """
        # From the asyncore docs:
        #
        # Return value is a pair (conn, address) where conn is a new
        # socket object usable to send and receive data on the
        # connection, and address is the address bound to the socket
        # on the other end of the connection.
        sock, addr = self.accept()

        self.request_handler(sock = sock)

class Client(asynchat.async_chat):
    """
    A _very_ rudimentary HTTP client that is somewhat HTTP/1.1 compliant;
    support for some of the more esoteric portions of the HTTP/1.1 spec will be
    added on an 'as-needed' basis.  Will we need separate logic and/or code for
    providing HTTP/{0.9,1.0} clients. Do we need to worry about legacy clients?

    NB: Right now, this doesn't support connection pipelining. We NEED to
    support this.
    """

    def __init__(self, receiver = None):
        asynchat.async_chat.__init__(self)
        self.logger = logging.getLogger('HttpClient')

        self.set_terminator(HTTP_SEP)
        self.data = []
        self.chunk_buffer = None
        self.receiver = receiver
        self.should_close = False
        self.response_queue = collections.deque()

    def conn(self, host, port = 80):
        self.host = host
        self.port = port

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.logger.info("Connected to %s:%d" % (host, port))

    def make_request(self, command, resource, headers):
        #TODO: We can mangle the headers here if need be...
        h = copy.deepcopy(headers)
        del h['accept-encoding']
        req = HttpRequest(command, resource, 1, 1, h)
        self.logger.debug(repr(str(req) + HTTP_SEP))
        self.push(str(req) + HTTP_SEP)
        self.state = _HEADERS

    def handle_content(self, data):
        self.set_terminator(HTTP_SEP)
        self.state = _HEADERS
        self.response_queue.popleft()

    def handle_chunked_size(self, data):
        # Figure out the chunk size (byte size of the chunk is encoded as hex
        # for some weird reason. Thanks HTTP/1.1!)
        #
        # XXX We probably want to assert on this to make sure that we're
        # receiving everything the server promised.
        self.logger.debug("***" + repr(data))
        chunk_size = int(data.split(None, 1)[0], 16)
        if chunk_size > 0:
            self.chunk_size = chunk_size
            self.logger.debug("Chunk size: %d" % chunk_size)
            self.state = _CHUNKED_CONTENT
            self.set_terminator(chunk_size)
        else:
            self.logger.debug("End of chunked content encountered")
            self.chunk_size = None
            self.state = _CHUNKED_TRAILER
            self.set_terminator(HTTP_SEP)

            chunk_data = ''.join(self.chunk_buffer)
            r = self.response_queue.popleft()
            del r.msg['transfer-encoding']
            r.msg['content-length'] = str(len(chunk_data))
            self.receiver.push(str(r) + HTTP_SEP)
            self.receiver.push(chunk_data + HTTP_SEP)

    def handle_chunked_content(self, data):
        self.chunk_buffer.append(data)
        self.logger.debug(repr(''.join(self.chunk_buffer)))
        self.set_terminator(CLRF)
        self.state = _CHUNKED_SIZE

    # For now, let's throw away the trailer of a chunked response
    # Let's forward the complete, de-chunked response to the client.
    def handle_chunked_trailer(self, data):
        self.logger.debug(repr(''.join(self.chunk_buffer)))
        self.state = _HEADERS

    # XXX We definitely need to refactor this; we should be reassigning
    # found_terminator rather than resorting to if/elif hootenany.
    def found_terminator(self):
        self.logger.debug("Found terminator")
        data = ''.join(self.data)
        self.data = []

        if len(data) == 0:
            # empty string?
            return

        if self.state == _HEADERS:
            resp = HttpResponse.from_string(data)
            self.response_queue.append(resp)

            assert not (resp.length and resp.chunked)

            if resp.length:
                self.set_terminator(resp.length)
                self.state = _CONTENT
                self.receiver.push(str(resp) + HTTP_SEP)
            elif resp.chunked:
                self.chunk_buffer = []
                self.set_terminator(CLRF)
                self.state = _CHUNKED_SIZE

        elif self.state == _CONTENT:
            self.handle_content(data)

        elif self.state == _CHUNKED_SIZE:
            self.handle_chunked_size(data)

        elif self.state == _CHUNKED_CONTENT:
            self.handle_chunked_content(data)

        elif self.state == _CHUNKED_TRAILER:
            self.handle_chunked_trailer(data)

        # Next up, figure out when to close.

    def dechunk(self, response):
        # XXX We should de-chunkify requests so that we can store them as
        # continguous blobs in the cache
        pass

    def handle_connect(self):
        pass

    def handle_expt(self):
        self.close()

    def handle_close(self):
        self.logger.debug("Server '%s' closed connection" % self.host)
        #self.receiver.close()
        self.close()

    def collect_incoming_data(self, data):
        self.logger.debug("Data size: %d" % len(data))
        self.logger.debug('Incoming data: """%s"""' % repr(data))

        self.data.append(data)

        if self.state == _CONTENT and self.receiver:
            self.receiver.push(data)
