class ProxyFrontend(object):
    def GET(self):
        """
        Handle a request made to the proxy by an end user.
        """

        return None

class DistributedCache(object):
    def getResource(self, resourceId):
        """
        Attempt to retrieve a resource by ID (i.e. URI) from the distributed
        cache. Returns 'None' if the resource does not exist in the cache.
        """

        return resource

    def updateResource(self, resourceId, resource):
        """
        Push a resource into the distributed cache identified by 'resourceId';
        if a resource with 'resourceId' already exists, update the resource
        pointed to by the resourceId.
        """

        return None

class RetrievalService(object):
    def isConnectionAvailable(self):
        """
        Determine if an active connection to the internet is currently
        available; it will be used to determine if new resources can be
        retrieved by the retrieval service.
        """

        return connection_boolean

    def getResource(self, resourceId):
        """
        Immediately retrieve a resource from the internet, store it in the
        distributed cache and return the resource to the caller.
        """

        return resource

class RequestQueue(object):
    def deleteRequest(self, resourceId):
        """
        Remove a request to retrieve a resource currently placed in the request
        queue. Returns false if the request does not exist in the queue.
        """

        return success_boolean

    def pushRequest(self, resourceId):
        """
        Place a differed retrieval request for a resourceId. This will be called
        if there is no internet connection immediately available.
        """

        return position_in_queue

    def popRequest(self):
        """
        Retrieve a resource corresponding to the first identifier in the queue
        and place it in the distributed cache for later use.
        """

        return None
