from pprint import pformat
import urlparse
import email.message
import httpconst

HTTP_PORT = 80
HTTPS_PORT = 443

# States
_UNKNOWN = 'UNKNOWN'
_IDLE = 'Idle'
_REQ_STARTED = 'Request-started'
_REQ_SENT = 'Request-sent'

class HttpHeaders(object):

    def __init__(self):
        self.dict = {}
        self.unixfrom = ''
        self.headers = []
        self.status = ''

    @classmethod
    def from_string(klass, header_str):
        k = klass()
        k.readheaders(header_str)
        return k

    def addheader(self, key, value):
        """
        Add header for field key handling repeats.
        """
        prev = self.dict.get(key)
        if prev is None:
            self.dict[key] = value
        else:
            combined = ", ".join((prev, value))
            self.dict[key] = combined

    def addcontinue(self, key, more):
        """
        Add more field data from a continuation line.
        """
        prev = self.dict[key]
        self.dict[key] = prev + "\n " + more

    def readheaders(self, header_str):
        """
        Read header lines.

        Read header lines up to the entirely blank line that terminates them.
        The (normally blank) line that ends the headers is skipped, but not
        included in the returned list.

        If multiple header fields with the same name occur, they are combined
        according to the rules in RFC 2616 sec 4.2: Appending each subsequent
        field-value to the first, each separated by a comma. The order in which
        header fields with the same field-name are received is significant to
        the interpretation of the combined field value.
        """

        hlist = []
        headerseen = ""
        firstline = 1
        startofline = unread = tell = None

        for line in header_str.split('\n'):
            if headerseen and line[0] in ' \t':
                # It's a continuation line.
                hlist.append(line)
                self.addcontinue(headerseen, line.strip())
                continue

            headerseen = self.isheader(line)

            if headerseen:
                # It's a legal header line, save it.
                hlist.append(line)
                self.addheader(headerseen, line[len(headerseen)+1:].strip())
                continue
            else:
                # All bets are off, we never should have reached here; blow up.
                # For now, let's fail silently
                pass

    def isheader(self, line):
        """
        Determine whether a given line is a legal header.

        This method should return the header name, suitably canonicalized.
        You may override this method in order to use Message parsing on tagged
        data in RFC 2822-like formats with special header formats.
        """
        i = line.find(':')
        if i > 0:
            return line[:i].lower()
        return None

    def getheader(self, name, default=None):
        """Get the header value for a name.

        This is the normal interface: it returns a stripped version of the
        header value for a given header name, or None if it doesn't exist.
        This uses the dictionary version which finds the *last* such header.
        """
        return self.dict.get(name.lower(), default)
    get = getheader

    # Access as a dictionary (only finds *last* header of each type):
    def __len__(self):
        """Get the number of headers in a message."""
        return len(self.dict)

    def __getitem__(self, name):
        """Get a specific header, as from a dictionary."""
        return self.dict[name.lower()]

    def __setitem__(self, name, value):
        """Set the value of a header."""
        del self[name]
        self.dict[name.lower()] = value
        text = name + ": " + value
        for line in text.split("\n"):
            self.headers.append(line + "\n")

    def __delitem__(self, name):
        """Delete all occurrences of a specific header, if it is present."""
        name = name.lower()
        if not name in self.dict:
            return
        del self.dict[name]
        name = name + ':'
        n = len(name)
        lst = []
        hit = 0
        for i in range(len(self.headers)):
            line = self.headers[i]
            if line[:n].lower() == name:
                hit = 1
            elif not line[:1].isspace():
                hit = 0
            if hit:
                lst.append(i)
        for i in reversed(lst):
            del self.headers[i]

    def setdefault(self, name, default=""):
        lowername = name.lower()
        if lowername in self.dict:
            return self.dict[lowername]
        else:
            text = name + ": " + default
            for line in text.split("\n"):
                self.headers.append(line + "\n")
            self.dict[lowername] = default
            return default

    def has_key(self, name):
        """Determine whether a message contains the named header."""
        return name.lower() in self.dict

    def __contains__(self, name):
        """Determine whether a message contains the named header."""
        return name.lower() in self.dict

    def __iter__(self):
        return iter(self.dict)

    def keys(self):
        """Get all of a message's header field names."""
        return self.dict.keys()

    def values(self):
        """Get all of a message's header field values."""
        return self.dict.values()

    def items(self):
        """Get all of a message's headers.

        Returns a list of name, value tuples.
        """
        return self.dict.items()

    def __str__(self):
        return ''.join(self.headers)

    def __repr__(self):
        return repr(self.items())

class HttpRequest(object):
    def __init__(self, command, uri, version_major, version_minor, headers,
                 raw_request = None):
        self.command = command
        self.raw_request = raw_request
        self.uri = uri
        self.version = (version_major, version_minor)
        self.headers = headers

    def __str__(self):
        req = []
        req.append("%s %s HTTP/%d.%d" %
                   (self.command, self.uri, self.version[0], self.version[1]))
        for k, v in self.headers.items():
            req.append("%s: %s" % (k.lower(), v))
        return "\r\n".join(req)

    @classmethod
    def from_string(klass, raw_request):
        """
        Parse a HTTP request to extract the command (i.e. verb), URI, HTTP version
        and any headers included in the request.

        NOTE: This  makes GET-specific assumptions (i.e. everything after the first
        line will be headers). This will probably fail (violently) if it attempts to
        munge a POST or PUT request.
        """
        line_separator = '\r\n'
        request_idx = -1

        try:
            request_idx = raw_request.index(line_separator) + 2
        except ValueError:
            line_separator = '\n'
            request_idx = raw_request.find(line_separator) + 1

        # If we can't find a record separator (strictly, '\r\n',
        # but '\n' is cool too), bail.
        if (request_idx == 0):
            return False

        request_line = raw_request[:request_idx].strip()
        hdrs = raw_request[request_idx:]

        command = None
        request_version = None
        close_connection = 1

        words = request_line.split()
        if len(words) == 3:
            [command, path, ver] = words
            if ver[:5] != 'HTTP/':
                return False
            try:
                base_version_number = ver.split('/', 1)[1]
                version = [int(x) for x in base_version_number.split(".")]
                # RFC 2145 section 3.1 says there can be only one "." and
                #   - major and minor numbers MUST be treated as
                #      separate integers;
                #   - HTTP/2.4 is a lower version than HTTP/2.13, which in
                #      turn is lower than HTTP/12.3;
                #   - Leading zeros MUST be ignored by recipients.
                if len(version) != 2:
                    raise ValueError
            except (ValueError, IndexError):
                return False
            if version >= (1, 1):
                close_connection = 0
            if version >= (2, 0):
                return False
        elif len(words) == 2:
            [command, path] = words
            close_connection = 1
            if command != 'GET':
                return False
        elif not words:
            return False
        else:
            return False

        headers = HttpHeaders.from_string(hdrs)
        uri = urlparse.urlsplit(path)

        return klass(command, uri, version[0], version[1], headers, raw_request)

class HttpResponse(object):
    def __init__(self):
        self.msg = None
        self.raw_response = None

        # from the Status-Line of the response
        self.version = _UNKNOWN # HTTP-Version
        self.status = _UNKNOWN  # Status-Code
        self.reason = _UNKNOWN  # Reason-Phrase

        self.chunked = _UNKNOWN         # is "chunked" being used?
        self.length = _UNKNOWN          # number of bytes left in response
        self.will_close = _UNKNOWN      # conn will close at end of response

    def __str__(self):
        req = []
        req.append("%s %s %s" % (self.version, self.status, self.reason))
        for k, v in self.msg.items():
            req.append("%s: %s" % (k.lower(), v))
        return "\r\n".join(req)

    @classmethod
    def from_string(klass, h_string):
        k = klass()
        k.parse(h_string)
        return k

    def parse(self, head_str):
        self.raw_response = head_str
        header_offset = self.__parse_status()
        self.msg = HttpHeaders.from_string(head_str[header_offset:])
        self.__check_chunked()
        self.__check_content_length()
        self.will_close = self.__should_close_connection()

        if not self.will_close and \
           not self.chunked and \
           self.length is None:
            self.will_close = 1

    def append_content(self, data):
        pass

    def __parse_status(self):
        line_separator = '\r\n'
        request_idx = -1

        try:
           raw_response_idx = self.raw_response.index(line_separator)
        except ValueError:
            line_separator = '\n'
            raw_response_idx = self.raw_response.find(line_separator)

        if (raw_response_idx < 0):
            return False

        raw_response_idx += len(line_separator)

        response_line = self.raw_response[:raw_response_idx].strip()
        parsed_status = response_line.split(None, 2)

        # Apparently, some web servers may fail to provide a reason to accompany
        # their status; would this be better handled with a regular expression?
        if len(parsed_status) == 2:
            self.version, self.status = parsed_status
        else:
            self.version, self.status, self.reason = parsed_status
        return raw_response_idx

    def __check_chunked(self):
        tr_enc = self.msg.getheader('transfer-encoding')
        if tr_enc and tr_enc.lower() == "chunked":
            self.chunked = 1
        else:
            self.chunked = 0

    def __check_content_length(self):
        # do we have a Content-Length?
        # NB: We only care about this if we're not receiving chunked data
        length = self.msg.getheader('content-length')
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
            else:
                if self.length < 0:  # ignore nonsensical negative lengths
                    self.length = None
        else:
            self.length = None

        #TODO: What on earth does this do?
        # does the body have a fixed length? (of zero)
        #if (self.status == status.NO_CONTENT or self.status == status.NOT_MODIFIED or
        #    100 <= self.status < 200 or      # 1xx codes
        #    self.method == 'HEAD'):
        #    self.length = 0

    def __should_close_connection(self):
        conn = self.msg.getheader('connection')

        if self.version == 'HTTP/1.1':
            conn = self.msg.getheader('connection')
            if conn and "close" in conn.lower():
                return True
            return False

        if self.msg.getheader('keep-alive'):
            return False

        if conn and "keep-alive" in conn.lower():
            return False

        pconn = self.msg.getheader('proxy-connection')
        if pconn and "keep-alive" in pconn.lower():
            return False

        return True

