import json
import async_http
import handler
import cache
import options

"""
Main entry point for the python proxy; more details here to follow.
"""

SHUTDOWN_PERFORMED = 0
CONFIG_FILE = "conf/server.json"

def handle_signal (*ignore):
    shutdown()

def shutdown():
    global SHUTDOWN_PERFORMED

    if not SHUTDOWN_PERFORMED:
        SHUTDOWN_PERFORMED = 1
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

    conf = options.Config(CONFIG_FILE)
    log_level = conf.proxy['loggingLevel']

    logging.basicConfig(level=LOGGING_LEVEL,
                        format='[%(levelname)s] %(asctime)s - %(name)s :: %(message)s',)
    l = logging.getLogger('main')
    address = ('localhost', conf.http['port'])
    proxy_server = async_http.Server(address[0], address[1],
                                     handler.ProxyHttpRequestHandler)

    l.info("Created HTTP proxy server on %s:%d" % server.address)

    asyncore.loop(use_poll = True)
