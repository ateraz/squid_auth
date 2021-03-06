"""Service used by auth APIS"""

import datetime
import string
from twisted.internet import task, reactor, defer, utils
from twisted.application import service
from twisted.python import log
from user import User


class AuthService(service.Service):
    """Service used by APIs to query, store and exchange info about users."""
    # IP: user hash for storing active users
    active_users = {}
    # (login, pass): user hash for caching all users
    all_users = {}
    # String formatter used in system callbacks formatting
    formatter = string.Formatter()
    callback_handler = utils

    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.db.setErrorHandler(self.processDbError)

    def startService(self):
        service.Service.startService(self)
        # Setting up tasks for periodic users update
        task.LoopingCall(self.getAllUsers).start(
            self.config['timeouts']['database_update'])
        task.LoopingCall(self.checkActiveUsersTimeout).start(
            self.config['timeouts']['login'])
        task.LoopingCall(self.checkSeenWelcomeTimeout).start(
            self.config['timeouts']['show_welcome'])

    def addActiveUser(self, user, ip):
        """Method for updating setting user ip and updating active users list"""
        user.connectFrom(ip)
        self.active_users[ip] = user

    def ipUsedByAnotherUser(self, ip, login):
        """Check if IP is already used"""
        return ip in self.active_users and self.active_users[ip].login != login

    def getActiveUserByIp(self, ip):
        return self.active_users[ip] if ip in self.active_users else None

    def getActiveUserIdByIp(self, ip):
        return getattr(self.getActiveUserByIp(ip), 'user_id', 0)

    def validateUser(self, auth_params):
        """Method used by validation API for checking"""
        ip, login, passwd = auth_params
        is_default_user = login == self.config['default_user']
        wrong_credentials = not is_default_user and (
            login not in self.all_users or
            self.all_users[login].passwd != passwd)
        if wrong_credentials or self.ipUsedByAnotherUser(ip, login):
            # Invalid credentials or IP already in use
            user = User(ip=ip, login=login, passwd=passwd)
        elif ip in self.active_users:
            # User alreaady in active list
            user = self.active_users[ip]
            user.updateLastActivity()
        else:
            # User just connected
            if is_default_user:
                user = User(ip=ip, login=login, passwd=passwd, user_id=0,
                            dept_id=0, admin_level=0)
            else:
                user = self.all_users[login]
            self.addActiveUser(user, ip)
            self.executeCallback(user)
        return user.is_authorized

    def checkActiveUsersTimeout(self):
        """Task for updating active users list"""
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['timeouts']['login'])
        for ip, user in self.active_users.items():
            if user.last_active < deadline:
                user.is_authorized = False
                del self.active_users[ip]

    def checkSeenWelcomeTimeout(self):
        """Task for updating users who have seen welcome page"""
        deadline = datetime.datetime.now() - datetime.timedelta(
            seconds=self.config['timeouts']['show_welcome'])
        # Note that users with login self.config['default_user'] exist only in
        # active_users thus should be also checked for seen_welcome timeout
        for key, user in self.active_users.items() + self.all_users.items():
            if user.last_active < deadline:
                user.seen_welcome = False

    @defer.inlineCallbacks
    def getAllUsers(self):
        """Task for updating all users list"""
        users = yield self.db.runQuery(
            'SELECT login, passwd, user_id, dept_id, admin_level '
            'FROM users_all')
        for user in users:
            login, passwd, user_id, dept_id, admin_level = user[0], user[1], \
                user[2], user[3], user[4]
            if login not in self.all_users:
                # Create new user
                self.all_users[login] = User(
                    login=login, passwd=passwd, user_id=user_id,
                    dept_id=dept_id, admin_level=admin_level)
            else:
                # Update already existing user
                self.all_users[login].update(
                    passwd=passwd, user_id=user_id, dept_id=dept_id,
                    admin_level=admin_level)

    def executeCallback(self, user):
        """Method for executing system callbacks"""
        status = 'success' if user.is_authorized else 'fail'
        callback = self.config['callbacks'][status]
        executable = callback['executable']
        if executable:
            args = self.formatArgs(callback['args'], user)
            # Runs system call in separate thread.
            # Doesn't care about results.
            self.callback_handler.getProcessValue(executable, args)

    def formatArgs(self, args, mapping):
        """System callbacks args formatting"""
        return [self.formatter.vformat(arg, None, mapping) for arg in args]

    def processDbError(self, error):
        """Custom DB error processing"""
        if self.all_users:
            log.msg("Users not updated from db!")
        else:
            log.msg("Unable to fetch users from db, exiting...")
            reactor.stop()
