#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.internet.protocol import ServerFactory, Protocol
from base64 import b64decode

class AuthProtocol(Protocol):

    def dataReceived(self, data):
        credentials = self.factory.decode_auth_str(data)
        if credentials in self.factory.users:
            message = 'OK'
        else:
            message = 'ERR'
        self.transport.write(message + '\n')

class AuthFactory(ServerFactory):

    protocol = AuthProtocol

    def __init__(self, users):
        self.users = users

    @staticmethod
    def decode_auth_str(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        credentials = b64decode(parts[2]).split(':')
        credentials.append(parts[0])
        return tuple(credentials)

def main():
    from twisted.internet import reactor
    users = [('user', 'pass', '127.0.0.1')]
    port = reactor.listenTCP(9999, AuthFactory(users),
        interface='localhost')
    print 'Listening port %s.' % port.getHost()
    reactor.run()


if __name__ == '__main__':
    main()
