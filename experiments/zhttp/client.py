import asynchat
import copy
import logging
import socket
import message

HTTP_NEWLINE = "\r\n"

class SimpleHttpClient(asynchat.async_chat):
    """
    A _very_ rudimentary HTTP client that is somewhat HTTP/1.1 compliant;
    support for some of the more esoteric portions of the HTTP/1.1 spec will be
    added on an 'as-needed' basis.  Will we need separate logic and/or code for
    providing HTTP/{0.9,1.0} clients. Do we need to worry about legacy clients?
    """

    def __init__(self, receiver = None):
        asynchat.async_chat.__init__(self)
        self.logger = logging.getLogger('SimpleHttpClient')

        # We're going to mangle these headers to remove the proxy-specific
        # fields from them.
        self.set_terminator(HTTP_NEWLINE * 2)
        self.data = []
        self.receiver = receiver
        self.should_close = False

    def conn(self, host, port = 80):
        self.host = host
        self.port = port

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.logger.info("Connected to %s:%d" % (host, port))

    def make_request(self, command, resource, headers):
        req = []
        self.headers = copy.deepcopy(headers)
        req.append("%s %s HTTP/1.1" % (command, resource))
        for k, v in self.headers.items():
            req.append("%s: %s" % (k, v))
        req.append('')
        http_request = HTTP_NEWLINE.join(req)
        self.state = 'headers'

        print repr(http_request)
        self.push(http_request + HTTP_NEWLINE)

    def found_terminator(self):
        self.logger.warn("Found terminator")
        data = self.data[:]
        self.data = []

        if self.receiver:
            self.receiver.push(data)

        if self.state == 'headers':
            resp = message.HttpResponse.from_string(''.join(data))
            print resp
            self.state = 'content'
        elif self.state == 'content':
            self.logger.warn("Closing connection")
            self.close()

#    def read(self, amt=None):
#        if self.fp is None:
#            return ''
#
#        if self.chunked:
#            return self._read_chunked(amt)
#
#        if amt is None:
#            # unbounded read
#            if self.length is None:
#                s = self.fp.read()
#            else:
#                s = self._safe_read(self.length)
#                self.length = 0
#            self.close()        # we read everything
#            return s
#
#        if self.length is not None:
#            if amt > self.length:
#                # clip the read to the "end of response"
#                amt = self.length
#
#        # we do not use _safe_read() here because this may be a .will_close
#        # connection, and the user is reading more bytes than will be provided
#        # (for example, reading in 1k chunks)
#        s = self.fp.read(amt)
#        if self.length is not None:
#            self.length -= len(s)
#            if not self.length:
#                self.close()
#        return s
#
#    def _read_chunked(self, amt):
#        assert self.chunked != _UNKNOWN
#        chunk_left = self.chunk_left
#        value = ''
#
#        # XXX This accumulates chunks by repeated string concatenation,
#        # which is not efficient as the number or size of chunks gets big.
#        while True:
#            if chunk_left is None:
#                line = self.fp.readline()
#                i = line.find(';')
#                if i >= 0:
#                    line = line[:i] # strip chunk-extensions
#                try:
#                    chunk_left = int(line, 16)
#                except ValueError:
#                    # close the connection as protocol synchronisation is
#                    # probably lost
#                    self.close()
#                    raise IncompleteRead(value)
#                if chunk_left == 0:
#                    break
#            if amt is None:
#                value += self._safe_read(chunk_left)
#            elif amt < chunk_left:
#                value += self._safe_read(amt)
#                self.chunk_left = chunk_left - amt
#                return value
#            elif amt == chunk_left:
#                value += self._safe_read(amt)
#                self._safe_read(2)  # toss the CRLF at the end of the chunk
#                self.chunk_left = None
#                return value
#            else:
#                value += self._safe_read(chunk_left)
#                amt -= chunk_left
#
#            # we read the whole chunk, get another
#            self._safe_read(2)      # toss the CRLF at the end of the chunk
#            chunk_left = None
#
#        # read and discard trailer up to the CRLF terminator
#        ### note: we shouldn't have any trailers!
#        while True:
#            line = self.fp.readline()
#            if not line:
#                # a vanishingly small number of sites EOF without
#                # sending the trailer
#                break
#            if line == '\r\n':
#                break
#
#        # we read everything; close the "file"
#        self.close()
#
#        return value
#
#    def _safe_read(self, amt):
#        """Read the number of bytes requested, compensating for partial reads.
#
#        Normally, we have a blocking socket, but a read() can be interrupted
#        by a signal (resulting in a partial read).
#
#        Note that we cannot distinguish between EOF and an interrupt when zero
#        bytes have been read. IncompleteRead() will be raised in this
#        situation.
#
#        This function should be used when <amt> bytes "should" be present for
#        reading. If the bytes are truly not available (due to EOF), then the
#        IncompleteRead exception can be used to detect the problem.
#        """
#        s = []
#        while amt > 0:
#            chunk = self.fp.read(min(amt, MAXAMOUNT))
#            if not chunk:
#                raise IncompleteRead(''.join(s), amt)
#            s.append(chunk)
#            amt -= len(chunk)
#        return ''.join(s)
#
#    def getheader(self, name, default=None):
#        if self.msg is None:
#            raise ResponseNotReady()
#        return self.msg.getheader(name, default)
#
#    def getheaders(self):
#        """Return list of (header, value) tuples."""
#        if self.msg is None:
#            raise ResponseNotReady()
#        return self.msg.items()

    def handle_connect(self):
        pass

    def handle_expt(self):
        self.close()

    def handle_close(self):
        self.logger.info("Server '%s' closed connection" % self.host)
        self.receiver.close()
        self.close()

    def collect_incoming_data(self, data):
        self.data.append(data)

