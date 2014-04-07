from twisted.internet import protocol, defer, utils, task
from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, usage, failure
from twisted.enterprise import adbapi
from datetime import datetime, timedelta
import yaml, base64, string


class User(object):

    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
        'login_time']

    def __init__(self, login, passwd, ip):
        self.login = login
        self.passwd = passwd
        self.ip = ip
        self.login_time = datetime.now()

    def update(self, **kwargs):
        for field in kwargs:
            setattr(self, field, kwargs[field])
        return self

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')

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


class BaseFactory(protocol.ServerFactory):

    protocol = BaseProtocol

    def __init__(self, service):
        self.service = service

    def lineReceived(self, line):
        raise NotImplementedError(
            'Method lineReceived should be implemented in subclass')


class ValidatorFactory(BaseFactory):

    successResponse = 'OK'
    failResponse = 'ERR'
    formatter = string.Formatter()

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
        return self.__executeCallback('success', user)

    def failCallback(self, user):
        return self.__executeCallback('fail', user)

    def __executeCallback(self, completed, user):
        command = self.__formatCommand(
            self.service.config['validator']['callback'][completed], user)
        if command:
            utils.getProcessValue(command)
        return getattr(self, completed + 'Response')

    def __formatCommand(command, mapping):
        return self.formatter.vformat(command, None, mapping)


class IpCheckerFactory(BaseFactory):

    def lineReceived(self, line):
        d, user_id, ip = defer.Deferred(), 0, line.strip()
        if ip in self.service.users:
            user_id = self.service.users[ip].user_id
        d.callback(str(user_id))
        return d


class IpInfoFactory(BaseFactory):

    def lineReceived(self, line):
        d, user_id, ip = defer.Deferred(), 0, line.strip()
        if ip in self.service.users:
            user_id = self.service.users[ip].user_id
        d.callback(str(user_id))
        return d


class AuthOptions(usage.Options):

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthConfig(dict):

    def __init__(self, config_path):
        dict.__init__(self, yaml.load(file(config_path)))

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)


class AuthService(service.Service):

    users = {}

    def __init__(self, config):
        self.config = config
        self.login_timeout = self.config['validator']['login_timeout']

    def startService(self):
        service.Service.startService(self)
        db = self.config['database']
        self.db = adbapi.ConnectionPool(
            'MySQLdb', host=db['host'], db=db['name'],
            user=db['user'], passwd=db['pass'])
        task.LoopingCall(self.checkUsersTimeout).start(self.login_timeout)

    def validateUser(self, user):
        # Note space at the end of the query first row. It's significant.
        return self.db.runQuery(
            'SELECT user_id, dept_id, admin_level FROM users_all '
            'WHERE login=%s AND passwd=%s', (user.login, user.passwd)
        ).addCallback(self.__validateQueryResult, user)

    def __validateQueryResult(self, results, user):
        if len(results) == 0 or (user.ip in self.users and
                self.users[user.ip].login != user.login):
            return failure.Failure(user)
        return user.update(user_id=results[0][0], dept_id=results[0][1],
                           admin_level=results[0][2])

    def addUser(self, user):
        self.users[user.ip] = user
        return user

    def checkUsersTimeout(self):
        deadline = datetime.now() - timedelta(seconds=self.login_timeout)
        for ip, user in self.users.items():
            if user.login_time < deadline:
                del self.users[ip]
