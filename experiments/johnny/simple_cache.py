import os.path
import sqlite3

class SimpleCache(object):

    def __init__(self):
        self.TABLE_NAME = 'resource'
        self.conn = sqlite3.connect(":memory:")
        self.c = self.conn.cursor()
        self.FIELD_NAMES = ('resourceId', 'header', 'content')
        self.createTable()

    def __del__(self):
        self.c.close()

    def createTable(self):
        self.c.execute('''create table %s (%s TEXT PRIMARY KEY, %s BLOB, %s
                BLOB)''' % (self.TABLE_NAME
                            ,self.FIELD_NAMES[0]
                            ,self.FIELD_NAMES[1]
                            ,self.FIELD_NAMES[2]) )

    def getResource(self, resourceId):
        """
        Attempt to retrieve a resource by ID (i.e. URI) from the distributed
        cache. Returns 'None' if the resource does not exist in the cache.
        """

        query_arguments = (resourceId,)

        query_result = self.c.execute('select * from %s where resourceId=?' %
                self.TABLE_NAME, query_arguments)

        return query_result

    def updateResource(self, resourceId, resource):
        """
        Push a resource into the distributed cache identified by 'resourceId';
        if a resource with 'resourceId' already exists, update the resource
        pointed to by the resourceId. 
        """

        # Delete any existing records with same resourceId
        query_arguments = (resourceId,)
        self.c.execute('DELETE FROM %s WHERE resourceId=?' % self.TABLE_NAME, query_arguments)
        self.conn.commit()

        # Insert the resource into the table
        query_arguments = (resourceId, sqlite3.Binary(str(resource.info())), sqlite3.Binary(resource.read()))
        self.c.execute('''INSERT INTO %s VALUES (?,?,?)''' % self.TABLE_NAME,
                query_arguments)
        self.conn.commit()

        return None
