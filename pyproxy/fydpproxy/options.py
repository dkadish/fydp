import json

PROXY_DEFAULTS = {
    'debugMode' : False,
    'loggingLevel' : 'ERROR'
    }

HTTP_DEFAULTS = {
    'maxConnections' : 10,
    'sslEnabled' : False,
    'port' : 8081,
    'verbose' : False,
    }

CACHE_DEFAULTS = {
    'cacheSize' : 10,
    'compressCache' : True,
    }

class Config(object):
    """
    This class encapsulates configuration information shared across
    components throughout the proxy. User-modifiable config
    information is stored in a JSON document with different objects
    for each software component.
    """
    def __init__(self, path):
        self.proxy = {}
        self.http = {}
        self.cache = {}
        with open(path) as f:
            config = json.load(f)

        self.proxy.update(PROXY_DEFAULTS)
        self.http.update(HTTP_DEFAULTS)
        self.cache.update(CACHE_DEFAULTS)
        self.proxy.update(config['proxy'])
        self.http.update(config['http'])
        self.cache.update(config['cache'])

        if self.proxy['debugMode']:
            self.proxy['loggingLevel'] = 'DEBUG'
        elif self.proxy['verbose']:
            self.proxy['loggingLevel'] = 'INFO'
