import asyncore
import logging
import time
import client
import message
import unittest

class MockReceiver(object):
    def __init__(self):
        self.data = []

    def push(self, d):
        print repr(d)
        #self.data.append(d)

    def close(self):
        print "Closing..."

#class TestSimpleHttpClient(unittest.TestCase):
#    def setUp(self):
#        pass
#
#    def testPushRequest(self):

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s',)

headers = message.HttpHeaders()
headers['Host'] = 'localhost'
headers['Connection'] = 'close'

m = MockReceiver()

c = client.SimpleHttpClient(m)
c.conn('localhost')
c.make_request('GET', 'http://localhost/', headers)

asyncore.loop()
