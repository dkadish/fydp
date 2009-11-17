import cPickle
import os.path
import sqlite3

class SimpleCache(object):

    def __init__(self):
        self.DB_PATH = os.path.abspath('simple_cache.db')
        self.TABLE_NAME = 'resource'

    def getResource(self, resourceId):
        """
        Attempt to retrieve a resource by ID (i.e. URI) from the distributed
        cache. Returns 'None' if the resource does not exist in the cache.
        """

        conn = sqlite3.connect(self.DB_PATH) 
        c = conn.cursor()

        query_arguments = (resourceId,)

        # What exactly is being copied here?
        query_result = c.execute('select * from %s where resourceId=?' %
                self.TABLE_NAME, query_arguments)

        #for row in c:
        #    print "Result of the query"
        #    print row

        c.close()

        return query_result

    def updateResource(self, resourceId, resource):
        """
        Push a resource into the distributed cache identified by 'resourceId';
        if a resource with 'resourceId' already exists, update the resource
        pointed to by the resourceId. 
        """

        conn = sqlite3.connect(self.DB_PATH) 
        c = conn.cursor()

        # Delete any existing records with same resourceId
        query_arguments = (resourceId,)
        c.execute('DELETE FROM %s WHERE resourceId=?' % self.TABLE_NAME, query_arguments)
        conn.commit()

        #print resource.info()
        #print resource.read()
        # binary = sqlite3.Binary(pickled_header)


        query_arguments = (resourceId, sqlite3.Binary(str(resource.info())), sqlite3.Binary(resource.read()))
        c.execute('''INSERT INTO %s VALUES (?,?,?)''' % self.TABLE_NAME,
                query_arguments)
        conn.commit()

        c.close()

        return None
