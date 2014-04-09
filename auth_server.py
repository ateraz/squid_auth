from twisted.internet import protocol, defer, utils, task
from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, failure
from twisted.enterprise import adbapi
import yaml, base64, string, datetime


class User(object):

    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
                 'login_time']

    def __init__(self, **kwargs):
        for field in kwargs:
            setattr(self, field, kwargs[field])

    def setIp(self, ip):
        self.ip = ip
        self.login_time = datetime.datetime.now()

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')


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

    success_response = 'OK'
    fail_response = 'ERR'
    formatter = string.Formatter()

    def lineReceived(self, line):
        auth_params = self.parseAuthString(line)
        if not auth_params:
            log.msg('Bad auth string format')
            d = defer.Deferred()
            d.callback(self.fail_response)
            return d
        return self.service.validateUser(auth_params).addCallbacks(
            self.successCallback, self.failCallback)

    @staticmethod
    def parseAuthString(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
            return parts[0], credentials[0], credentials[1]
        except:
            return None

    def successCallback(self, user):
        return self.executeCallback('success', user)

    def failCallback(self, user):
        return self.executeCallback('fail', user)

    def executeCallback(self, completed, user):
        callback = self.service.config['callbacks'][completed]
        if callback['executable']:
            args = self.formatArgs(callback['args'], user)
            utils.getProcessValue(callback['executable'], args)
        return getattr(self, completed + '_response')

    def formatArgs(self, args, mapping):
        return [self.formatter.vformat(arg, None, mapping) for arg in args]


class IpCheckerFactory(BaseFactory):

    def lineReceived(self, line):
        d, ip = defer.Deferred(), line.strip()
        user_id = self.service.getActiveUserIdByIp(ip)
        d.callback(str(user_id))
        return d


class IpInfoFactory(BaseFactory):

    allowed_fields = ['login', 'dept_id', 'admin_level']

    def lineReceived(self, line):
        d, request = defer.Deferred(), line.strip()
        separator = request[0]
        parts = request.split(separator)
        res = self.buildResponseString(parts, separator)
        d.callback(str(res))
        return d

    def buildResponseString(self, parts, separator):
        if len(parts) < 3:
            return -1
        user = self.service.getActiveUserByIp(parts[1])
        if not user:
            return 0
        return self.getUserParams(user, parts[2:], separator)

    def getUserParams(self, user, params, separator):
        user_params = []
        for param in params:
            if param in self.allowed_fields:
                user_params.append(getattr(user, param))
            else:
                return -1
        user_params.insert(0, user.user_id)
        return separator.join(map(str, user_params))


class ServiceFactory(object):

    validator = ValidatorFactory
    ip_checker = IpCheckerFactory
    ip_info = IpInfoFactory

    def construct(self, factory_name, service):
        return getattr(self, factory_name)(service)


class AuthConfig(dict):

    def __init__(self, config_path):
        dict.__init__(self, yaml.load(file(config_path)))


class AuthService(service.Service):

    active_users = {}
    all_users = {}

    def __init__(self, config):
        self.config = config

    def startService(self):
        service.Service.startService(self)
        db = self.config['database']
        self.db = adbapi.ConnectionPool(
            'MySQLdb', host=db['host'], db=db['name'], user=db['user'],
            passwd=db['pass'])
        task.LoopingCall(self.getAllUsers).start(
            self.config['database_update_timeout'])
        task.LoopingCall(self.checkActiveUsersTimeout).start(
            self.config['login_timeout'])

    def validateUser(self, auth_params):
        ip, login, passwd = auth_params
        d = defer.Deferred()
        if (not self.userExists(login, passwd) or
                self.ipUsedByAnotherUser(ip, login)):
            d.errback(user)
        else:
            user = self.all_users[(login, passwd)]
            self.addActiveUser(user, ip)
            d.callback(user)
        return d

    def userExists(self, login, passwd):
        return (login, passwd) in self.all_users

    def ipUsedByAnotherUser(self, ip, login):
        return ip in self.active_users and self.active_users[ip].login != login

    def addActiveUser(self, user, ip):
        user.setIp(ip)
        self.active_users[ip] = user

    def ipIsUsed(self, ip):
        return ip in self.active_users

    def getActiveUserByIp(self, ip):
        return self.active_users[ip] if self.ipIsUsed(ip) else None

    def getActiveUserIdByIp(self, ip):
        user = self.getActiveUserByIp(ip)
        return user.user_id if user else 0

    def checkActiveUsersTimeout(self):
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['login_timeout'])
        for ip, user in self.active_users.items():
            if user.login_time < deadline:
                del self.active_users[ip]

    def getAllUsers(self):
        self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level FROM users_all'
        ).addCallback(self.updateAllUsers)

    def updateAllUsers(self, users):
        self.all_users = {}
        for user in users:
            self.all_users[(user[0], user[1])] = User(
                login=user[0], passwd=user[1], user_id=user[2], dept_id=user[3],
                admin_level=user[4])
