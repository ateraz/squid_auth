from twisted.internet import protocol, defer, utils
from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, usage, failure
from twisted.enterprise import adbapi
from datetime import datetime
import yaml, functools, base64


class User(object):

    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level', 'login_time']

    def __init__(self, login, passwd, ip):
        self.login = login
        self.passwd = passwd
        self.ip = ip
        self.login_time = datetime.now()

    def updateFromSqlResult(self, result):
        self.user_id = result[0]
        self.dept_id = result[1]
        self.admin_level = result[2]

    def keys(self):
        return self.__slots__

    def __getitem__(self, key):
        return getattr(self, key)

    @classmethod
    def fromAuthString(cls, auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
            return cls(login=credentials[0], passwd=credentials[1],
                       ip=parts[0])
        except:
            return None


class BaseProtocol(LineReceiver):

    delimiter = b'\n'

    def lineReceived(self, line):
        self.factory.lineReceived(line).addCallback(self.sendLine)


# Ihnerit from object to enable call of super() in subclasses
class BaseFactory(protocol.ServerFactory, object):

    protocol = BaseProtocol

    def __init__(self, service):
        self.service = service

    def lineReceived(self, line):
        raise NotImplementedError(
            'Method lineReceived should be implemented in subclass')


class ValidatorFactory(BaseFactory):

    successResponse = 'OK'
    failResponse = 'ERR'

    def lineReceived(self, line):
        user = User.fromAuthString(line)
        if not user:
            log.msg('Bad auth string format')
            d = defer.Deferred()
            d.callback(self.failResponse)
            return d
        return self.service.validateUser(user) \
                   .addCallback(self.service.addUser) \
                   .addCallbacks(self.successCallback, self.failCallback)

    def successCallback(self, user):
        utils.getProcessValue(
            self.service.config['validator']['success_callback'].format(**user))
        return self.successResponse

    def failCallback(self, user):
        utils.getProcessValue(
            self.service.config['validator']['fail_callback'].format(**user))
        return self.failResponse


class IpCheckerFactory(BaseFactory):

    def lineReceived(self, line):
        d, user_id, ip = defer.Deferred(), 0, line.strip()
        if ip in self.service.users:
            user_id = self.service.users[ip].user_id
        d.callback(str(user_id))
        return d


class AuthOptions(usage.Options):

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthConfigurator(object):

    def __init__(self, config_path):
        self.config = yaml.load(file(config_path))

    def __getitem__(self, key):
        return self.config[key]


class AuthService(service.Service):

    def __init__(self, config):
        self.users, self.config = {}, config

    def startService(self):
        service.Service.startService(self)
        db = self.config['database']
        self.db = adbapi.ConnectionPool(
            'MySQLdb', host=db['host'], db=db['name'],
            user=db['user'], passwd=db['pass'])

    def validateUser(self, user):
        return self.db.runQuery(
            'SELECT user_id, dept_id, admin_level FROM users_all '
            'WHERE login=%s AND passwd=%s', (user.login, user.passwd)
        ).addCallback(self.__postValidateUser, user)

    def addUser(self, user):
        self.users[user.ip] = user
        return user

    def userLogined(self, user):
        return user.ip in self.users

    def __postValidateUser(self, results, user):
        if len(results) == 0 or (user.ip in self.users and
                self.users[user.ip].login != user.login):
            return failure.Failure(user)
        user.updateFromSqlResult(results[0])
        return user
