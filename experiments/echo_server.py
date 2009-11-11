import asyncore
import asynchat
import socket
import logging

class EchoHandler(asynchat.async_chat):
    """Handles echoing messages from a single client.
    """

    def __init__(self, sock):
        self.received_data = []
        self.logger = logging.getLogger('EchoHandler%s' % str(sock.getsockname()))
        asynchat.async_chat.__init__(self, sock)
        # Start looking for the ECHO command
        self.process_data = self._process_command
        self.set_terminator('\n')
        return

    def collect_incoming_data(self, data):
        """Read an incoming message from the client and put it into our outgoing queue."""
        self.logger.debug('collect_incoming_data() -> (%d)\n"""%s"""', len(data), data)
        self.received_data.append(data)

    def found_terminator(self):
        """The end of a command or message has been seen."""
        self.logger.debug('found_terminator()')
        self.process_data()

    def _process_command(self):
        """We have the full ECHO command"""
        command = ''.join(self.received_data)
        self.logger.debug('Received command: "%s"', command)
        self.logger.debug('Echoing:\n"""%s"""', command)
        self.push("\n>>> " + command + "\n")
        self.received_data = []
        # self.close_when_done()

    def handle_close(self):
        self.logger.debug('Closing...')
        self.close()

class EchoServer(asyncore.dispatcher):
    """Receives connections and establishes handlers for each client.
    """

    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.listen(1)
        self.handler = None
        return

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        EchoHandler(sock=client_info[0])
        # We only want to deal with one client at a time,
        # so close as soon as we set up the handler.
        # Normally you would not do this and the server
        # would run forever or until it received instructions
        # to stop.
        # self.handle_close()
        return

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s',)
    l = logging.getLogger('main')

    address = ('localhost', 8081)
    server = EchoServer(address)
    l.info("Created EchoServer; connect with\nnc %s %d" % server.address)

    try:
        asyncore.loop(timeout=2)
    except KeyboardInterrupt:
        l.warn('Caught keyboard interrupt; shutting down')

