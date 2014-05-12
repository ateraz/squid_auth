import mock
import datetime
from twisted.trial import unittest
from lib import AuthService


class TestAuthService(unittest.TestCase):
    ip = 'ip'
    another_ip = 'ip1'
    login = 'login'
    another_login = 'login1'
    passwd = 'passwd'
    user_id = 1
    dept_id = 2
    admin_level = 3

    def setUp(self):
        self.service = AuthService({}, mock.Mock())
        self.service.all_users = {}
        self.service.active_users = {}
        self.service.callback_handler = mock.Mock()
        callback = {'executable': 'some_script',
                    'args': []}
        self.service.config['callbacks'] = {'success': callback,
                                            'fail': callback}
        self.service.config['timeouts'] = {'show_welcome': 1,
                                           'login' :1}
        self.service.config['default_user'] = 'default_user'
        self.user = mock.Mock()
        self.service.db = mock.Mock()
        self.service.db.runQuery.return_value = (
            (self.login, self.passwd, self.user_id, self.dept_id,
             self.admin_level),)

    def test_add_active_user(self):
        self.service.addActiveUser(self.user, self.ip)
        self.user.connectFrom.assert_called_once_with(self.ip)
        self.assertEqual(self.service.getActiveUserByIp(self.ip), self.user)

    def test_ip_used_by_user(self):
        self.user.login = self.login
        self.service.addActiveUser(self.user, self.ip)
        self.assertFalse(self.service.ipUsedByAnotherUser(self.ip, self.login))
        self.assertTrue(self.service.ipUsedByAnotherUser(self.ip,
                                                         self.another_login))

    def test_get_active_user_by_ip(self):
        self.service.addActiveUser(self.user, self.ip)
        self.assertEqual(self.service.getActiveUserByIp(self.ip), self.user)
        self.assertEqual(self.service.getActiveUserByIp(self.another_ip), None)

    def test_get_active_user_id_by_ip(self):
        user_id = 1
        self.user.user_id = user_id
        self.service.addActiveUser(self.user, self.ip)
        self.assertEqual(self.service.getActiveUserIdByIp(self.ip), user_id)
        self.assertEqual(self.service.getActiveUserIdByIp(self.another_ip), 0)

    def test_format_args(self):
        mapping = {'key': 'value'}
        res = self.service.formatArgs(['{key}'], mapping)
        self.assertEqual(set(['value']), set(res))
        self.assertRaises(KeyError, self.service.formatArgs, ['{key1}'],
                          mapping)
        self.assertRaises(ValueError, self.service.formatArgs, ['{key}}'],
                          mapping)

    def test_dont_execute_callback(self):
        self.service.config['callbacks']['success']['executable'] = ''
        self.service.executeCallback(self.user)
        self.assertFalse(self.service.callback_handler.getProcessValue.called)

    def test_execute_success_callback(self):
        self.service.executeCallback(self.user)
        self.assertTrue(self.service.callback_handler.getProcessValue.called)
        self.service.callback_handler.getProcessValue.assert_called_once_with(
            self.service.config['callbacks']['success']['executable'],
            [])

    def test_execute_fail_callback(self):
        self.user.is_authorized = False
        self.service.executeCallback(self.user)
        self.assertTrue(self.service.callback_handler.getProcessValue.called)
        self.service.callback_handler.getProcessValue.assert_called_once_with(
            self.service.config['callbacks']['fail']['executable'],
            [])

    def _is_valid(self):
        return self.service.validateUser((self.ip, self.login, self.passwd))

    def test_validate_unknown_user(self):
        self.assertFalse(self._is_valid())

    def test_validate_user_with_bad_passwd(self):
        self.service.all_users = {self.login: self.user}
        self.assertFalse(self._is_valid())

    def test_validate_new_user(self):
        self.user.passwd = self.passwd
        self.service.all_users = {self.login: self.user}
        self.assertTrue(self._is_valid())

    def test_validate_user_from_used_ip(self):
        self.service.all_users = {self.login: self.user}
        self.service.active_users = {self.ip: mock.Mock()}
        self.assertFalse(self._is_valid())

    def test_active_users_timeout(self):
        self.user.last_active = datetime.datetime.now()
        self.service.active_users = {self.ip: self.user}
        self.service.checkActiveUsersTimeout()
        self.assertTrue(self.ip in self.service.active_users)
        self.service.config['timeouts'] = {'login': 0}
        self.service.checkActiveUsersTimeout()
        self.assertTrue(self.ip not in self.service.active_users)

    def test_seen_welcome_timeout(self):
        self.user.last_active = datetime.datetime.now()
        self.service.active_users = {self.ip: self.user}
        self.service.checkSeenWelcomeTimeout()
        self.assertTrue(self.service.active_users[self.ip].seen_welcome)
        self.service.config['timeouts'] = {'show_welcome': 0}
        self.service.checkSeenWelcomeTimeout()
        self.assertFalse(self.service.active_users[self.ip].seen_welcome)

    def test_get_new_users(self):
        self.service.getAllUsers()
        self.assertEqual(len(self.service.all_users), 1)
        self.assertTrue(self.login in self.service.all_users)
        self.assertRaises(AttributeError, getattr,
                          self.service.all_users[self.login], 'updated')
        self.assertEqual(self.service.all_users[self.login].user_id,
                         self.user_id)
        self.assertEqual(self.service.all_users[self.login].dept_id,
                         self.dept_id)
        self.assertEqual(self.service.all_users[self.login].admin_level,
                         self.admin_level)

    def test_update_all_users(self):
        self.service.getAllUsers()
        user = self.service.all_users[self.login]
        before_update = datetime.datetime.now()
        self.service.db.runQuery.return_value = (
            (self.login, 'new_pass', self.user_id, self.dept_id,
             self.admin_level),)
        self.service.getAllUsers()
        after_update = datetime.datetime.now()
        self.assertEqual(self.service.all_users[self.login], user)
        try:
            user.updated
        except AttributeError:
            self.fail("Unexpected AttributeError!")
        self.assertTrue(user.created < before_update < user.updated)
        self.assertTrue(user.updated < after_update)
