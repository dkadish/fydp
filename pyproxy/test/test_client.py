import asyncore
import logging
import time
import async_http
import httpmsg
import unittest

class MockReceiver(object):
    def __init__(self):
        self.data = []

    def push(self, d):
        print repr(d)
        #self.data.append(d)

    def close(self):
        print "Closing..."

class TestClient(unittest.TestCase):
    def test_pushRequest(self):
        logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s',)

        headers = httpmsg.HttpHeaders()
        headers['Host'] = 'localhost'
        headers['Connection'] = 'close'

        m = MockReceiver()

        c = async_http.Client(m)
        c.conn('localhost')
        c.make_request('GET', 'http://localhost/', headers)

        asyncore.loop()
        self.assertTrue(True)
