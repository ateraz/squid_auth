import datetime
from twisted.trial import unittest
from lib.user import User


class TestUser(unittest.TestCase):
    def test_new_user(self):
        user_id = 1
        user = User(user_id=user_id)
        self.assertEqual(user.user_id, user_id)
        self.assertEqual(user.is_authorized, False)

    def test_user_attributes(self):
        user = User()
        self.assertRaises(AttributeError, getattr, user, 'ip')
        user.ip = 1
        try:
            user.ip
        except AttributeError:
            self.fail("Unexpected AttributeError!")

    def test_set_unknown_attributes(self):
        self.assertRaises(AttributeError, User, **{'unknown_property': 1})
        user = User()
        self.assertRaises(AttributeError, setattr, user, 'unknown_property', 1)

    def test_user_connection(self):
        user, ip = User(), '127.0.0.1'
        user.connectFrom(ip)
        self.assertEqual(user.ip, ip)
        self.assertEqual(user.is_authorized, True)
        self.assertLess(user.login_time, datetime.datetime.now())

    def test_user_as_dict(self):
        user_id = 1
        user = User(user_id=user_id)
        self.assertEqual(user['user_id'], user_id)
        self.assertEqual(user['ip'], '')
