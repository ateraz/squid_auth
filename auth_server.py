from twisted.internet import protocol, defer, utils, task
from twisted.application import internet, service
from twisted.protocols.basic import LineReceiver
from twisted.python import log, failure
from twisted.enterprise import adbapi
import yaml, base64, string, datetime, copy


class User(object):
    """Repsesents user that needs to be authorized and queried in API calls.
    """
    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
                 'login_time', 'status']
    valid = 'valid'

    def __init__(self, **kwargs):
        for field in kwargs:
            setattr(self, field, kwargs[field])
        self.status = ''

    def setIp(self, ip):
        """Sets authorized user ip, remembers login time
        and marks user as valid.
        """
        self.ip = ip
        self.login_time = datetime.datetime.now()
        self.status = self.valid

    def isAuthorized(self):
        """Checks if user is authorized.
        """
        print self.status
        print self.valid
        return self.status == self.valid

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')


class BaseProtocol(LineReceiver):
    """Base protocol for implementing socket APIs.
    """
    delimiter = b'\n'

    def lineReceived(self, line):
        self.sendLine(str(self.factory.processLine(line.strip())))


class BaseFactory(protocol.ServerFactory):
    """Factory instantiating base protocol instances
    and implementing API logic.
    """
    protocol = BaseProtocol

    def __init__(self, service):
        self.service = service

    def processLine(self, line):
        """Abstract method that should be implemented in child classes.
        Contains logic for building response for API calls.
        """
        raise NotImplementedError(
            'Method lineReceived should be implemented in subclass')


class ValidatorFactory(BaseFactory):
    """API used by squid for validating proxy users.
    """
    success_response = 'OK'
    fail_response = 'ERR'
    formatter = string.Formatter()

    def processLine(self, line):
        auth_params = self.parseAuthString(line)
        if not auth_params:
            log.msg('Bad auth string format')
            return self.fail_response
        user = self.service.validateUser(auth_params)
        status = 'success' if user.isAuthorized() else 'fail'
        self.executeCallback(status, user)
        return getattr(self, status + '_response')

    @staticmethod
    def parseAuthString(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
            return parts[0], credentials[0], credentials[1]
        except:
            return None

    def executeCallback(self, status, user):
        callback = self.service.config['callbacks'][status]
        if callback['executable']:
            args = self.formatArgs(callback['args'], user)
            # Runs system call in separate thread.
            # Doesn't care about results.
            utils.getProcessValue(callback['executable'], args)

    def formatArgs(self, args, mapping):
        return [self.formatter.vformat(arg, None, mapping) for arg in args]


class IpCheckerFactory(BaseFactory):
    """API for getting user ID of current proxy users.
    """
    def processLine(self, line):
        return self.service.getActiveUserIdByIp(line)


class IpInfoFactory(BaseFactory):
    """API for getting more detailed info about active proxy users.
    """
    allowed_fields = ['login', 'dept_id', 'admin_level']

    def processLine(self, line):
        separator = line[0]
        parts = line.split(separator)
        return self.buildResponseString(parts, separator)

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
    """API builder.
    Instantiates API instances for application.
    """
    validator = ValidatorFactory
    ip_checker = IpCheckerFactory
    ip_info = IpInfoFactory

    @classmethod
    def construct(cls, factory_name, service):
        return getattr(cls, factory_name)(service)


class AuthConfig(dict):
    """Stored in file application config.
    """
    def __init__(self, config_path):
        dict.__init__(self, yaml.load(file(config_path)))


class AuthService(service.Service):
    """Service used by APIs to query, store and exchange info about users.
    """
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
        if ((login, passwd) not in self.all_users or
                self.ipUsedByAnotherUser(ip, login)):
            return User(ip=ip, login=login, passwd=passwd)
        return self.addActiveUser(self.all_users[(login, passwd)], ip)

    def ipUsedByAnotherUser(self, ip, login):
        return ip in self.active_users and self.active_users[ip].login != login

    def addActiveUser(self, user, ip):
        _user = copy.copy(user)
        _user.setIp(ip)
        self.active_users[ip] = _user
        return _user

    def getActiveUserByIp(self, ip):
        return self.active_users[ip] if ip in self.active_users else None

    def getActiveUserIdByIp(self, ip):
        return getattr(self.getActiveUserByIp(ip), 'user_id', 0)

    def checkActiveUsersTimeout(self):
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['login_timeout'])
        for ip, user in self.active_users.items():
            if user.login_time < deadline:
                del self.active_users[ip]

    @defer.inlineCallbacks
    def getAllUsers(self):
        users = yield self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level FROM users_all'
        )
        self.all_users = {}
        for user in users:
            self.all_users[(user[0], user[1])] = User(
                login=user[0], passwd=user[1], user_id=user[2], dept_id=user[3],
                admin_level=user[4])
