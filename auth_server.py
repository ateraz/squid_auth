from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.application import internet, service
from twisted.python import log, usage
from twisted.enterprise import adbapi
from base64 import b64decode


class AuthServerOptions(usage.Options):

    optParameters = [
        ['port', 'p', 9999, 'The port number to listen on.'],
        ['iface', None, 'localhost', 'The interface to listen on.']]


class AuthProtocol(LineReceiver):

    def lineReceived(self, auth_str):
        self.factory.service.validate(auth_str, self.writeResponse)

    def writeResponse(self, user):
        if user:
            message = 'OK'
        else:
            message = 'ERR'
        self.sendLine(message)


class AuthFactory(ServerFactory):

    protocol = AuthProtocol

    def __init__(self, service):
        self.service = service


class AuthService(service.Service):

    def startService(self):
        service.Service.startService(self)
        self.dbpool = adbapi.ConnectionPool('MySQLdb', db='squid_auth')

    def validate(self, auth_str, auth_callback):
        user = self.get_user(auth_str)
        if user:
            self.dbpool.runQuery(
                'SELECT * FROM users_all WHERE login=%s AND passwd=%s',
                (user['login'], user['password'])
            ).addCallback(auth_callback)
        else:
            auth_callback(None)

    @staticmethod
    def get_user(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = b64decode(parts[2]).split(':')
            return {
                'login': credentials[0],
                'password': credentials[1],
                'ip': parts[0]}
        except:
            log.msg('Bad auth string format')
            return None
