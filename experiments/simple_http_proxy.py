#buuts
import asynchat
import asyncore
import logging
import socket
import signal
import time
import urlparse
from zhttp import message
from zhttp.client import SimpleHttpClient

SHUTDOWN_PERFORMED = 0
HTTP_NEWLINE = "\r\n"
PROXY_PORT = 8088
LOGGING_LEVEL = logging.INFO

class SimpleHttpProxy(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        # Fun fact: this will allow us to pick-up a socket that is currently in
        # TIME_WAIT (i.e. a socket that is waiting to die)
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
        this point, I thinkthe connection is being managed by our
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
        sock, addr = self.accept()
        # From the asyncore docs:
        #
        # Return value is a pair (conn, address) where conn is a new socket object
        # usable to send and receive data on the connection, and address is the address
        # bound to the socket on the other end of the connection.
        SimpleHttpProxyRequestHandler(sock = sock)

class SimpleHttpProxyRequestHandler(asynchat.async_chat):
    """From the BaseHTTPServer docs:

    ---

    HTTP (HyperText Transfer Protocol) is an extensible protocol on
    top of a reliable stream transport (e.g. TCP/IP).  The protocol
    recognizes three parts to a request:

    1. One line identifying the request type and path
    2. An optional set of RFC-822-style headers
    3. An optional data part

    The headers and data are separated by a blank line.

    The first line of the request has the form

    <command> <path> <version>

    where <command> is a (case-sensitive) keyword such as GET or POST,
    <path> is a string containing path information for the request,
    and <version> should be the string "HTTP/1.0" or "HTTP/1.1".
    <path> is encoded using the URL encoding scheme (using %xx to signify
    the ASCII character with hex code xx).

    The specification specifies that lines are separated by CRLF but
    for compatibility with the widest range of clients recommends
    servers also handle LF.  Similarly, whitespace in the request line
    is treated sensibly (allowing multiple spaces between components
    and allowing trailing whitespace).

    Similarly, for output, lines ought to be separated by CRLF pairs
    but most clients grok LF characters just fine.

    If the first line of the request has the form

    <command> <path>

    (i.e. <version> is left out) then this is assumed to be an HTTP
    0.9 request; this form has no optional headers and data part and
    the reply consists of just the data.

    The reply form of the HTTP 1.x protocol again has three parts:

    1. One line giving the response code
    2. An optional set of RFC-822-style headers
    3. The data

    Again, the headers and data are separated by a blank line.

    ---

    The response code line has the form

    <version> <responsecode> <responsestring>

    where <version> is the protocol version ("HTTP/1.0" or "HTTP/1.1"),
    <responsecode> is a 3-digit response code indicating success or
    failure of the request, and <responsestring> is an optional
    human-readable string explaining what the response code means.

    The following request details are parsed and stored in a HttpRequest object:

    - command, path and version;

    - headers (as an instance of email.Message) containing the header information;

    IT IS IMPORTANT TO ADHERE TO THE PROTOCOL FOR RETURNING DATA TO THE CLIENT!

    The first thing to be written must be the response line.  Then
    follow 0 or more header lines, then a blank line, and then the
    actual data (if any).  The meaning of the header lines depends on
    the command executed by the server; in most cases, when data is
    returned, there should be at least one header line of the form

    Content-type: <type>/<subtype>

    where <type> and <subtype> should be registered MIME types,
    e.g. "text/html" or "text/plain".
    """
    def __init__(self, sock):
        self.logger = logging.getLogger('LoggingHttpHandler%s' % str(sock.getsockname()))
        self.buff = []
        asynchat.async_chat.__init__(self, sock)

        # HTTP headers end with a blank line
        self.set_terminator(HTTP_NEWLINE * 2)
        self.http_clients = {}
        self.http_client = None

        #XXX Awful debug hackery
        self.old_push = self.push
        def foo(data):
            self.logger.debug("*** %s" % repr(data))
            self.old_push(data)
        self.push = foo

    def collect_incoming_data(self, data):
        """
        Collect all incoming data into a buffer; it's unlikely that client
        requests will ever be big enough to warrant buffering, but this is
        generally good practice for network-y type operations.
        """
        self.buff.append(data)

    def found_terminator(self):
        """
        Called upon receiving a double '\r\n'; in the case of a GET, this means
        that we've received a full request (i.e. a path and any appropriate
        headers)
        """
        raw_request = ''.join(self.buff)
        self.buff = []

        request = message.HttpRequest.from_string(raw_request)
        self.logger.debug("Headers: %s" % repr(request.headers))
        self.logger.debug("Command: %s Resource: %s" % (request.command, ''.join(request.uri)))

        # If we receive anything other than a GET: All. Bets. Are. Off.
        #
        # Let's step around this unfortunate state of affairs by killing the
        # connection if we can. [MZ]
        if not request.command == 'GET':
            self.logger.warn("Received an unsupported HTTP command: '%s'; attempting to close channel" % request.command)
            self.push("HTTP/1.1 500 Internal Server Error" + HTTP_NEWLINE *2 )
            self.close()
            return

        http_client = SimpleHttpClient(self)
        http_client.conn(request.uri.hostname)

        #TODO: This is a good spot to modify any headers that will be sent to an
        # external host. [MZ]
        http_client.make_request(request.command, request.uri.path, request.headers)

    def handle_connect(self):
        """
        Called when an honest-to-goodness connection is made with a remote
        endpoint.
        """
        self.logger.debug("Connection with remote endpoint opened.")

    def handle_close(self):
        """
        Called when a connection with the server is closed by the other end; I'm
        assuming this happens when the browser has received everything it needs
        from the proxy, but I'm not totally sure.

        Aside: I'm pretty puzzled by Firefox's behaviour WRT making seemingly
        persistent connections to the proxy. Who exactly is responsible for
        closing the connection between the proxy and the browser. What's the
        exit strategy (for connections) here? [MZ]
        """
        self.logger.info('Remote connection closed')
        self.close()

def handle_signal (*ignore):
    shutdown()

def shutdown():
    global SHUTDOWN_PERFORMED

    if not SHUTDOWN_PERFORMED:
        l.warn('Passing out...')
        l.debug("Socket map: %s" % repr(asyncore.socket_map))
        l.info("Closing %d socket(s)" % len(asyncore.socket_map))
        asyncore.close_all()
        l.debug("Socket map: %s" % repr(asyncore.socket_map))
        l.warn('Gone')

if __name__ == '__main__':
    signal.signal (signal.SIGTERM, handle_signal)
    signal.signal (signal.SIGINT, handle_signal)
    signal.signal (signal.SIGHUP, handle_signal)

    logging.basicConfig(level=LOGGING_LEVEL, format='[%(levelname)s] %(asctime)s - %(name)s :: %(message)s',)
    l = logging.getLogger('main')
    address = ('localhost', PROXY_PORT)
    server = SimpleHttpProxy(address[0], address[1])
    l.info("Created HTTP proxy server on %s:%d" % server.address)

    asyncore.loop(use_poll = True)

