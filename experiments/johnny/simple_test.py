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

url ='http://www.google.com' 
test = SimpleTest()
response = test.getUrl(url)

# print response.info()

johnny = simple_cache.SimpleCache()
johnny.updateResource(url,response)
resource = johnny.getResource(url)

print "All finished"

for row in resource:
    print row

# TODO Put in asserts on row.info() and row.read()
