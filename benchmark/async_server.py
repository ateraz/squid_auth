"""Prototype of async tcp server"""

from twisted.internet import reactor, protocol
from twisted.enterprise import adbapi


class Connection(protocol.Protocol):

    db = adbapi.ConnectionPool(
        'MySQLdb', db='squid_auth', user='squid',
        passwd='not_secure_pass', host='91.202.128.106')

    def dataReceived(self, data):
        self.db.runQuery(
            'SELECT * FROM users_all WHERE login=%s AND passwd=%s',
            ('login', 'pass')
        ).addCallback(self.respond)

    def respond(self, _):
        self.transport.write('OK')
        self.transport.loseConnection()


if __name__ == '__main__':
    factory = protocol.ServerFactory()
    factory.protocol = Connection
    reactor.listenTCP(9999, factory)
    reactor.run()
