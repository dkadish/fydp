import unittest
import urllib2
import simple_cache

class SimpleTest(unittest.TestCase):

    def setUp(self):
        pass

    def getUrl(self, url):
        """
        Attempt to get a response from url argument. Returns response.
        """

        request = urllib2.Request(url)
        response = urllib2.urlopen(request) 

        return response

    def testCache(self):
        
        url ='http://www.neckbeard.ca/'
        response = self.getUrl(url)
        
        johnny = simple_cache.SimpleCache()
        johnny.updateResource(url,response)
        resource = johnny.getResource(url)
        
        self.assertEqual(response.info(), resource.info())
        self.assertEqual(response.read(), resource.read())

        #for row in resource:
        #    print "Id: %s, Headers: %s, Content: %s" % (row[0], repr(str(row[1])), repr(str(row[2])))
        #
        #print "All finished"
