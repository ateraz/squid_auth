from twisted.internet.protocol import Protocol, ServerFactory
from twisted.application import internet, service
from twisted.python import log, usage
from base64 import b64decode


class AuthProtocol(Protocol):

    def dataReceived(self, data):
        credentials = self.factory.service.decode_auth_str(data)
        if credentials in self.factory.service.users:
            message = 'OK'
        else:
            message = 'ERR'
        self.transport.write(message + '\n')


class AuthFactory(ServerFactory):

    protocol = AuthProtocol

    def __init__(self, service):
        self.service = service


class AuthService(service.Service):

    def __init__(self, users):
        self.users = users

    def startService(self):
        service.Service.startService(self)

    @staticmethod
    def decode_auth_str(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        if len(parts) > 2:
            credentials = b64decode(parts[2]).split(':')
            credentials.append(parts[0])
            credentials = tuple(credentials)
        else:
            credentials = None
        return credentials


class Options(usage.Options):

    optParameters = [
        ['port', 'p', 9999, 'The port number to listen on.'],
        ['iface', None, 'localhost', 'The interface to listen on.']]


def makeService(options):
    users = [
        ('user_with_access', 'pass', '127.0.0.1'),
        ('user_without_access', 'pass', '127.0.0.1')]

    top_service = service.MultiService()

    auth_service = AuthService(users)
    auth_service.setServiceParent(top_service)

    tcp_service = internet.TCPServer(
        int(options['port']), AuthFactory(auth_service),
        interface=options['iface'])
    tcp_service.setServiceParent(top_service)

    return top_service
