from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, usage, failure
from twisted.internet import protocol, defer
from twisted.enterprise import adbapi
from base64 import b64decode
import yaml


class AuthServerOptions(usage.Options):

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthConfigurator(object):

    def __init__(self, config_path):
        self.config = yaml.load(file(config_path))
        print self.config

    def __getitem__(self, key):
        return self.config[key]


class AuthProtocol(LineReceiver):

    def lineReceived(self, auth_str):
        self.factory.service.validate(auth_str, self.writeResponse)

    def writeResponse(self, user):
        self.sendLine('OK' if user else 'ERR')


class AuthFactory(protocol.ServerFactory):

    protocol = AuthProtocol

    def __init__(self, service):
        self.service = service


class AuthService(service.Service):

    def __init__(self, config):
        self.users, self.config = {}, config
        print config

    def startService(self):
        service.Service.startService(self)
        db = self.config['database']
        self.db = adbapi.ConnectionPool('MySQLdb', db=db['name'],
                                        user=db['user'], passwd=db['pass'])

    def validate(self, auth_str, auth_callback):
        user = self.getUserParams(auth_str)
        if not user:
            return auth_callback(None)
        d = self.db.runQuery(
            'SELECT login FROM users_all WHERE login=%s AND passwd=%s',
            (user['login'], user['password']))
        d.addCallback(self.checkUser, user)
        d.addCallbacks(self.successCallback, self.failCallback)
        d.addCallback(auth_callback)

    def checkUser(self, results, user):
        ip, login = user['ip'], user['login']
        if len(results) == 0 or (ip in self.users and self.users[ip] != login):
            return failure.Failure(user)
        self.users[user['ip']] = user['login']
        return user

    def successCallback(self, user):
        c =  self.config['auth_callback']['success'].format(**user)
        print c
        return user

    def failCallback(self, user):
        c = self.config['auth_callback']['fail'].format(**user)
        print c
        # Method shouldn't return anything

    @staticmethod
    def getUserParams(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = b64decode(parts[2]).split(':')
        except:
            log.msg('Bad auth string format')
            return None
        return {
            'login': credentials[0],
            'password': credentials[1],
            'ip': parts[0],
            'time': ''}
