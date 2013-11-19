from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.application import internet, service
from twisted.python import log, usage
from base64 import b64decode


class AuthServerOptions(usage.Options):

    optParameters = [
        ['port', 'p', 9999, 'The port number to listen on.'],
        ['iface', None, 'localhost', 'The interface to listen on.']]


class AuthProtocol(LineReceiver):

    def lineReceived(self, auth_str):
        if self.factory.service.validate(auth_str):
            message = 'OK'
        else:
            message = 'ERR'
        self.sendLine(message)


class AuthFactory(ServerFactory):

    protocol = AuthProtocol

    def __init__(self, service):
        self.service = service


class AuthService(service.Service):

    def __init__(self, users):
        self.users = users

    def startService(self):
        service.Service.startService(self)

    def validate(self, auth_str):
        if self.decode_auth_str(auth_str) in self.users:
            return True
        return False

    @staticmethod
    def decode_auth_str(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        if len(parts) > 2:
            credentials = b64decode(parts[2]).split(':')
            credentials.append(parts[0])
            return tuple(credentials)
        log.msg('Bad auth string format')
        return None
