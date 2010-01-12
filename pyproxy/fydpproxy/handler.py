import asyncore
import asynchat

class ProxyHttpRequestHandler(asynchat.async_chat):
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
        self.logger = logging.getLogger(
            'LoggingHttpHandler%s' % str(sock.getsockname()))

        self.buff = []
        asynchat.async_chat.__init__(self, sock)
        self.logger.info("created new HTTP handler")

        # HTTP headers end with a blank line
        self.set_terminator(HTTP_NEWLINE * 2)
        self.http_clients = {}

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
        headers = copy.deepcopy(request.msg)
        if 'proxy-connection' in headers:
            del headers['proxy-connection']
            del headers['keep-alive']

        self.logger.debug("Headers: %s" % repr(headers))
        self.logger.debug("Command: %s Resource: %s"
                          % (request.command, ''.join(request.uri)))

        # If we receive anything other than a GET: All. Bets. Are. Off.
        #
        # Let's step around this unfortunate state of affairs by killing the
        # connection if we can. [MZ]
        if not request.command == 'GET':
            self.logger.warn("Received an unsupported HTTP command: '%s'; attempting to close channel" % request.command)
            self.push("HTTP/1.1 500 Internal Server Error" + HTTP_NEWLINE *2 )
            self.close()
            return

        http_client = None
        self.logger.info(request.uri.hostname)
        if not request.uri.hostname in self.http_clients:
            http_client = SimpleHttpClient(self)
            http_client.conn(request.uri.hostname)
            self.http_clients[request.uri.hostname] = http_client
        else:
            http_client = self.http_clients[request.uri.hostname]

        #XXX Mother of god, we need to figure out when the connection has been closed.

        #TODO: This is a good spot to modify any headers that will be sent to an
        # external host. [MZ]
        http_client.make_request(request.command, request.uri.path, headers)

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
        self.logger.debug('Remote connection closed')
        self.close()

