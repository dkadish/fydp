import httpmsg
import unittest

class TestHttpRequestParser(unittest.TestCase):
    def setUp(self):
        pass

    def testParseHappyHeaders(self):
        with open("test/data/sampleRequest.txt") as f:
            data = f.read()

        result = httpmsg.HttpRequest.from_string(data)

        self.assertNotEqual(result, False)
        self.assertEqual(result.command, 'GET')
        self.assertEqual(len(result.headers), 9)
        self.assertEqual(result.headers['Proxy-Connection'], 'keep-alive')
