from pprint import pformat
import email

class HttpMessage(object):
    pass

class HttpRequest(HttpMessage):
    def __init__(self, raw_request, command, uri, version_major, version_minor, headers):
        self.command = command
        self.raw_request = raw_request
        self.uri = uri
        self.version = (version_major, version_minor)
        self.headers = headers

    def __str__(self):
        rep = {
            'command' : self.command,
            #'raw_request' : self.raw_request,
            'uri' : self.uri,
            'version' : self.version,
            'headers' : self.headers.items()
        }
        return pformat(rep)

class HttpResponse(HttpMessage):
    def __init__(self, raw_response, version_major, version_minor, status, headers, content):
        self.raw_response = raw_response
        self.version = (version_major, version_minor)
        self.status = status
        self.headers = headers
        self.content = content

    def __str__(self):
        return pformat(self.__dict__)

def parse_http_request(raw_request):
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

    headers = __parse_headers(hdrs)

    return HttpRequest(raw_request, command, path, version[0], version[1], headers)

def parse_http_response(raw_response):
    line_separator = '\r\n'
    request_idx = -1

    try:
        raw_response_idx = raw_response.index(line_separator) + 2
    except ValueError:
        line_separator = '\n'
        raw_response_idx = raw_response.find(line_separator) + 1

    print raw_response_idx

    if (raw_response_idx == 0):
        return False

    response_line = raw_response[:raw_response_idx].strip()
    hdrs = raw_response[raw_response_idx:]

    headers = __parse_headers(hdrs)
    [version, status, status_str] = response_line.split(None, 2)

    return HttpResponse(None, None, None, status, headers, None)

def __parse_headers(headers):
    return email.message_from_string(headers)

