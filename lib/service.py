"""Service used by auth APIS"""

import datetime
import string
from twisted.internet import task, reactor, defer, utils
from twisted.application import service
from twisted.python import log
from user import User


class AuthService(service.Service):
    """Service used by APIs to query, store and exchange info about users."""
    active_users = {}
    all_users = {}
    formatter = string.Formatter()

    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.db.setErrorHandler(self.processDbError)

    def startService(self):
        service.Service.startService(self)
        task.LoopingCall(self.getAllUsers).start(
            self.config['database_update_timeout'])
        task.LoopingCall(self.checkActiveUsersTimeout).start(
            self.config['login_timeout'])

    def validateUser(self, auth_params):
        ip, login, passwd = auth_params
        if ((login, passwd) not in self.all_users or
                self.ipUsedByAnotherUser(ip, login)):
            user = User(ip=ip, login=login, passwd=passwd)
        else:
            user = self.addActiveUser(self.all_users[(login, passwd)], ip)
        self.executeCallback(user)
        return user


    def ipUsedByAnotherUser(self, ip, login):
        return ip in self.active_users and self.active_users[ip].login != login

    def addActiveUser(self, user, ip):
        user.connectFrom(ip)
        self.active_users[ip] = user
        return user

    def getActiveUserByIp(self, ip):
        return self.active_users[ip] if ip in self.active_users else None

    def getActiveUserIdByIp(self, ip):
        return getattr(self.getActiveUserByIp(ip), 'user_id', 0)

    def checkActiveUsersTimeout(self):
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['login_timeout'])
        for ip, user in self.active_users.items():
            if user.login_time < deadline:
                user.is_authrorized = False
                del self.active_users[ip]

    @defer.inlineCallbacks
    def getAllUsers(self):
        users = yield self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level '
            'FROM users_all'
        )
        if users:
            self.all_users = {}
            for user in users:
                self.all_users[(user[0], user[1])] = User(
                    login=user[0], passwd=user[1], user_id=user[2],
                    dept_id=user[3], admin_level=user[4])

    def executeCallback(self, user):
        status = 'success' if user.is_authrorized else 'fail'
        callback = self.config['callbacks'][status]
        executable = callback['executable']
        if executable:
            args = self.formatArgs(callback['args'], user)
            # Runs system call in separate thread.
            # Doesn't care about results.
            utils.getProcessValue(executable, args)

    def formatArgs(self, args, mapping):
        return [self.formatter.vformat(arg, None, mapping) for arg in args]

    def processDbError(self, error):
        if self.all_users:
            log.msg("Users not updated from db!")
        else:
            log.msg("Unable to fetch users from db, exiting...")
            reactor.stop()
