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
    callback_handler = utils

    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.db.setErrorHandler(self.processDbError)

    def startService(self):
        service.Service.startService(self)
        task.LoopingCall(self.getAllUsers).start(
            self.config['timeouts']['database_update'])
        task.LoopingCall(self.checkActiveUsersTimeout).start(
            self.config['timeouts']['login'])
        task.LoopingCall(self.checkSeenWelcomeTimeout).start(
            self.config['timeouts']['show_welcome'])

    def addActiveUser(self, user, ip):
        user.connectFrom(ip)
        self.active_users[ip] = user
        return user

    def ipUsedByAnotherUser(self, ip, login):
        return ip in self.active_users and self.active_users[ip].login != login

    def getActiveUserByIp(self, ip):
        return self.active_users[ip] if ip in self.active_users else None

    def getActiveUserIdByIp(self, ip):
        return getattr(self.getActiveUserByIp(ip), 'user_id', 0)

    def validateUser(self, auth_params):
        ip, login, passwd = auth_params
        if login not in self.all_users or \
                self.all_users[login].passwd != passwd or \
                self.ipUsedByAnotherUser(ip, login):
            user = User(ip=ip, login=login, passwd=passwd)
        elif ip in self.active_users:
            user = self.active_users[ip]
            user.updateLastActivity()
        else:
            user = self.addActiveUser(self.all_users[login], ip)
            self.executeCallback(user)
        return user

    def checkActiveUsersTimeout(self):
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['timeouts']['login'])
        for ip, user in self.active_users.items():
            if user.last_active < deadline:
                user.is_authorized = False
                del self.active_users[ip]

    def checkSeenWelcomeTimeout(self):
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['timeouts']['show_welcome'])
        for ip, user in self.active_users.items():
            if user.last_active < deadline:
                user.seen_welcome = False

    @defer.inlineCallbacks
    def getAllUsers(self):
        users = yield self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level '
            'FROM users_all'
        )
        for user in users:
            login, passwd, user_id, dept_id, admin_level = user[0], user[1], \
                user[2], user[3], user[4]
            if login not in self.all_users:
                self.all_users[login] = User(
                    login=login, passwd=passwd, user_id=user_id,
                    dept_id=dept_id, admin_level=admin_level)
            else:
                self.all_users[login].update(
                    passwd=passwd, user_id=user_id, dept_id=dept_id,
                    admin_level=admin_level)

    def executeCallback(self, user):
        status = 'success' if user.is_authorized else 'fail'
        callback = self.config['callbacks'][status]
        executable = callback['executable']
        if executable:
            args = self.formatArgs(callback['args'], user)
            # Runs system call in separate thread.
            # Doesn't care about results.
            self.callback_handler.getProcessValue(executable, args)

    def formatArgs(self, args, mapping):
        return [self.formatter.vformat(arg, None, mapping) for arg in args]

    def processDbError(self, error):
        if self.all_users:
            log.msg("Users not updated from db!")
        else:
            log.msg("Unable to fetch users from db, exiting...")
            reactor.stop()
