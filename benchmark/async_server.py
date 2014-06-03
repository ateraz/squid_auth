"""Prototype of async tcp server"""

from twisted.internet import reactor, protocol
from twisted.enterprise import adbapi


class Connection(protocol.Protocol):
    """Class that simulates client connection to tcp server"""

    # All instances share same DB pool instance
    # used to perform parallel queries
    db = adbapi.ConnectionPool(
        'MySQLdb', db='squid_auth', user='squid',
        passwd='not_secure_pass', host='91.202.128.106')

    def dataReceived(self, data):
        """Method called when new connection received"""
        self.db.runQuery(
            'SELECT * FROM users_all WHERE login=%s AND passwd=%s',
            ('login', 'pass')
        ).addCallback(self.respond)

    def respond(self, _):
        """Dummy callback to sql query"""
        self.transport.write('OK')
        self.transport.loseConnection()


if __name__ == '__main__':
    # Server that listen for client connections
    factory = protocol.ServerFactory()
    factory.protocol = Connection
    reactor.listenTCP(9999, factory)
    reactor.run()
