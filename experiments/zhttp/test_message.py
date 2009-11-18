import message
import unittest

class TestHttpRequestParser(unittest.TestCase):
    def setUp(self):
        pass

    def testParseHappyHeaders(self):
        with open("../sampleRequest.txt") as f:
            data = f.read()

        result = message.parse_http_request(data)

        self.assertNotEqual(result, False)
        self.assertEqual(result.command, 'GET')
        self.assertEqual(len(result.headers), 9)
        self.assertEqual(result.headers['Proxy-Connection'], 'keep-alive')

