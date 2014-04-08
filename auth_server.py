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
        return self.service.validateUser(user).addCallbacks(
            self.successCallback, self.failCallback)

    def successCallback(self, user):
        return self.__executeCallback('success', user)

    def failCallback(self, user):
        return self.__executeCallback('fail', user)

    def __executeCallback(self, completed, user):
        callback = self.service.config['validator']['callbacks'][completed]
        args = self.__formatArgs(callback['args'], user)
        if callback['executable']:
            utils.getProcessValue(callback['executable'], args)
        return getattr(self, completed + 'Response')

    def __formatArgs(self, args, mapping):
        res = []
        for arg in args:
            res.append(self.formatter.vformat(arg, None, mapping))
        return res


class IpCheckerFactory(BaseFactory):

    def lineReceived(self, line):
        d, user_id, ip = defer.Deferred(), 0, line.strip()
        if ip in self.service.active_users:
            user_id = self.service.active_users[ip].user_id
        d.callback(str(user_id))
        return d


class IpInfoFactory(BaseFactory):

    def lineReceived(self, line):
        d, user_id, ip = defer.Deferred(), 0, line.strip()
        if ip in self.service.active_users:
            user_id = self.service.active_users[ip].user_id
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

    active_users = {}
    all_users = {}

    def __init__(self, config):
        self.config = config
        self.login_timeout = self.config['validator']['login_timeout']

    def startService(self):
        service.Service.startService(self)
        db = self.config['database']
        self.db = adbapi.ConnectionPool(
            'MySQLdb', host=db['host'], db=db['name'],
            user=db['user'], passwd=db['pass'])
        task.LoopingCall(self.getAllUsers).start(
            self.config['validator']['database_update_timeout'])
        task.LoopingCall(self.checkActiveUsersTimeout).start(self.login_timeout)

    def validateUser(self, user):
        d = defer.Deferred()
        if self.__userNotExists(user) or self.__userOnAnotherIp(user):
            d.errback(user)
        else:
            params = self.all_users[(user.login, user.passwd)]
            user.update(user_id=params['user_id'], dept_id=params['dept_id'],
                        admin_level=params['admin_level'])
            self.__addActiveUser(user)
            d.callback(user)
        return d

    def __userNotExists(self, user):
        return (user.login, user.passwd) not in self.all_users

    def __userOnAnotherIp(self, user):
        return (user.ip in self.active_users and
            self.active_users[user.ip].login != user.login)

    def __addActiveUser(self, user):
        self.active_users[user.ip] = user

    def checkActiveUsersTimeout(self):
        deadline = datetime.now() - timedelta(seconds=self.login_timeout)
        for ip, user in self.active_users.items():
            if user.login_time < deadline:
                del self.active_users[ip]

    def getAllUsers(self):
        self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level FROM users_all'
        ).addCallback(self.__updateAllUsers)

    def __updateAllUsers(self, users):
        self.all_users = {}
        for user in users:
            # (login, passwd) => dict with user_id, dept_id, admin_level keys
            self.all_users[(user[0], user[1])] = {
                'user_id': user[2],
                'dept_id': user[3],
                'admin_level': user[4]}
