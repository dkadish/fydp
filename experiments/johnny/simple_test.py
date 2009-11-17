import urllib2
import simple_cache

class SimpleTest(object):

    def getUrl(self, url):
        """
        Attempt to get a response from url argument. Returns response.
        """

        request = urllib2.Request(url)
        response = urllib2.urlopen(request) 

        return response

url ='http://www.neckbeard.ca/'
test = SimpleTest()
response = test.getUrl(url)

# print response.info()

johnny = simple_cache.SimpleCache()
johnny.updateResource(url,response)
resource = johnny.getResource(url)


for row in resource:
    print "Id: %s, Headers: %s, Content: %s" % (row[0], repr(str(row[1])), repr(str(row[2])))

print "All finished"

# TODO Put in asserts on row.info() and row.read()
