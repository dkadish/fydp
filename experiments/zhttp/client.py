import asynchat
import copy
import logging
import socket
import message
import collections

HTTP_NEWLINE = "\r\n"
HTTP_SEP = HTTP_NEWLINE * 2
_HEADERS = 'headers'
_CONTENT = 'content'
_CHUNKED_SIZE = 'chunked-size'
_CHUNKED_CONTENT = 'chunked-content'
_CHUNKED_TRAILER = 'chunked-trailer'

class SimpleHttpClient(asynchat.async_chat):
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
        self.logger = logging.getLogger('SimpleHttpClient')

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
        req = message.HttpRequest(command, resource, 1, 1, h)
        self.push(str(req) + HTTP_SEP)
        self.state = _HEADERS

    def handle_content(self, data):
        self.set_terminator(HTTP_SEP)
        self.state = _HEADERS
        #self.should_close = True

    def handle_chunked_size(self, data):
        # Figure out the chunk size (byte size of the chunk is encoded as hex
        # for some weird reason. Thanks HTTP/1.1!)
        #
        # XXX We probably want to assert on this to make sure that we're
        # receiving everything the server promised.
        chunk_size = int(data.split(None, 1)[0], 16)
        if chunk_size > 0:
            self.chunk_size = chunk_size
            self.logger.debug("Chunk size: %d" % chunk_size)
            self.state = _CHUNKED_CONTENT
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
        self.state = _CHUNKED_SIZE

    # For now, let's throw away the trailer of a chunked response
    # Let's forward the complete, de-chunked response to the client.
    def handle_chunked_trailer(self, data):
        self.logger.debug(repr(''.join(chunk_buffer)))

    # XXX We definitely need to refactor this; we should be reassigning
    # found_terminator rather than resorting to if/elif hootenany.
    def found_terminator(self):
        self.logger.debug("Found terminator")
        data = ''.join(self.data)
        self.data = []

        if self.state == _HEADERS:
            resp = message.HttpResponse.from_string(data)
            self.response_queue.append(resp)

            assert not (resp.length and resp.chunked)

            if resp.length:
                self.set_terminator(int(resp.msg['content-length']))
                self.state = _CONTENT
                self.receiver.push(str(resp) + HTTP_SEP)
            elif resp.chunked:
                self.chunk_buffer = []
                self.set_terminator(HTTP_NEWLINE)
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
        self.logger.info("Server '%s' closed connection" % self.host)
        #self.receiver.close()
        self.close()

    def collect_incoming_data(self, data):
        self.logger.debug("Data size: %d" % len(data))
        self.logger.debug('Incoming data: """%s"""' % repr(data))

        self.data.append(data)

        if self.state == _CONTENT and self.receiver:
            self.receiver.push(data)

