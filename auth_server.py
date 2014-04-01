from twisted.internet import protocol, defer, utils
from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, usage, failure
from twisted.enterprise import adbapi
from datetime import datetime
import yaml, functools, base64


class BaseProtocol(LineReceiver):

    #delimiter = b'\n'

    def lineReceived(self, line):
        self.factory.lineReceived(line).addCallback(self.sendLine)


# Ihnerit from object to enable call of super() in subclasses
class BaseFactory(protocol.ServerFactory, object):

    protocol = BaseProtocol

    def __init__(self, service):
        self.service = service

    def lineReceived(self, line):
        # Need to be implemented in subclasses
        pass


class ValidatorFactory(BaseFactory):

    def lineReceived(self, line):
        return self.service.validate(line)


class CheckerFactory(BaseFactory):

    def lineReceived(self, line):
        return self.service.check(line)


class AuthOptions(usage.Options):

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthConfigurator(object):

    def __init__(self, config_path):
        self.config = yaml.load(file(config_path))

    def __getitem__(self, key):
        return self.config[key]


class AuthService(service.Service):

    successResponse = 'OK'
    failResponse = 'ERR'

    def __init__(self, config):
        self.users, self.config = {}, config

    def startService(self):
        service.Service.startService(self)
        conf = self.config['database']
        self.db = adbapi.ConnectionPool('MySQLdb', db=conf['name'],
                                        user=conf['user'], passwd=conf['pass'])

    def validate(self, line):
        user = self.getUserParams(line)
        if not user:
            d = defer.Deferred()
            d.callback(self.failResponse)
            return d
        d = self.db.runQuery(
            'SELECT id, login FROM users_all WHERE login=%s AND password=%s',
            (user['login'], user['password']))
        d.addCallback(self.validateUser, user)
        return d.addCallbacks(self.successCallback, self.failCallback)

    def check(self, ip):
        d = defer.Deferred()
        user_id = '0'
        if ip in self.users:
            user_id = self.users[ip][1]
        d.callback(str(user_id))
        return d

    def validateUser(self, results, user):
        ip, login = user['ip'], user['login']
        if len(results) == 0 or (ip in self.users and
                self.users[ip][0] != login):
            return failure.Failure(user)
        userid = results[0][0]
        self.users[user['ip']] = (user['login'], userid)
        user['id'] = userid
        return user

    def successCallback(self, user):
        utils.getProcessValue(
            self.config['auth_callback']['success'].format(**user))
        return self.successResponse

    def failCallback(self, user):
        utils.getProcessValue(
            self.config['auth_callback']['fail'].format(**user))
        return self.failResponse

    @staticmethod
    def getUserParams(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
        except:
            log.msg('Bad auth string format')
            return None
        return {
            'login': credentials[0],
            'password': credentials[1],
            'ip': parts[0],
            'time': datetime.now().strftime("%I:%M%p on %B %d, %Y")}
