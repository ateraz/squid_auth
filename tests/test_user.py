import datetime
from nose.tools import assert_equal, assert_less, assert_raises
from lib.user import User


class TestUser(object):
    def test_new_user(self):
        user_id = 1
        user = User(user_id=user_id)
        assert_equal(user.user_id, user_id)
        assert_equal(user.is_authrorized, False)

    def test_user_attributes(self):
        user = User()
        with assert_raises(AttributeError):
            user.ip
        user.ip = 1
        try:
            user.ip
        except AttributeError:
            self.fail("Unexpected AttributeError!")

    def test_set_unknown_attributes(self):
        with assert_raises(AttributeError):
            User(unknown_property=1)
        user = User()
        with assert_raises(AttributeError):
            user.unknown_property = 1

    def test_user_connection(self):
        user, ip = User(), '127.0.0.1'
        user.connectFrom(ip)
        assert_equal(user.ip, ip)
        assert_equal(user.is_authrorized, True)
        assert_less(user.login_time, datetime.datetime.now())

    def test_user_as_dict(self):
        user_id = 1
        user = User(user_id=user_id)
        assert_equal(user['user_id'], user_id)
        assert_equal(user['ip'], '')
