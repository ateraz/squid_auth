import mock
from twisted.trial import unittest
from lib.factories import _BaseProtocol, _BaseFactory, APIConstructor


class TestBaseFactory(unittest.TestCase):
    def test_process_line(self):
        factory = _BaseFactory(None)
        self.assertRaises(NotImplementedError, factory.processLine, '')


class _TestAPIFactory(unittest.TestCase):
    factory_name = ''

    def setUp(self):
        self.service = mock.Mock()
        if not self.factory_name:
            raise AttributeError('Test should have factory_name attribute')
        self.factory = APIConstructor.construct(self.factory_name,
                                                self.service)
        self.processLine = self.factory.processLine


class TestValidationFactory(_TestAPIFactory):
    factory_name = 'validator'

    def test_parse_auth(self):
        parse = self.factory.parseAuthString
        self.assertEqual(None, parse(''))
        self.assertEqual(None, parse('invalid string'))
        ip, login, passwd = parse('ip type dXNlcjpwYXNz')
        self.assertEqual('ip', ip)
        self.assertEqual('user', login)
        self.assertEqual('pass', passwd)

    def test_empty_line(self):
        self.assertEqual(self.processLine(''), self.factory.invalid_response)

    def test_valid_line(self):
        self.assertEqual(self.processLine('ip type dXNlcjpwYXNz'),
                         self.factory.valid_response)

    def test_not_authorized_user(self):
        self.service.validateUser.return_value.is_authorized = False
        self.assertEqual(self.processLine('ip type dXNlcjpwYXNz'),
                         self.factory.invalid_response)


class TestSessionFactory(_TestAPIFactory):
    factory_name = 'session'

    def test_wrong_format(self):
        self.assertEqual(self.factory.invalid_response, self.processLine(''))

    def test_no_active_user(self):
        self.service.getActiveUserByIp.return_value = None
        self.assertEqual(self.factory.invalid_response,
                         self.processLine('a b'))

    def test_wrong_login(self):
        self.assertEqual(self.factory.invalid_response,
                         self.processLine('a b'))

    def test_not_seen_welcome_page(self):
        self.service.getActiveUserByIp.return_value.login = 'b'
        self.service.getActiveUserByIp.return_value.seen_welcome = False
        self.assertEqual(self.factory.invalid_response,
                         self.processLine('a b'))

    def test_seen_welcome_page(self):
        self.service.getActiveUserByIp.return_value.login = 'b'
        self.assertEqual(self.factory.valid_response, self.processLine('a b'))


class TestIpCheckerFactory(_TestAPIFactory):
    factory_name = 'ip_checker'

    def test_process_line(self):
        user_id = '1'
        self.service.getActiveUserIdByIp.return_value = user_id
        self.assertEqual(self.processLine(''), user_id)


class TestIpInfoFactory(_TestAPIFactory):
    factory_name = 'ip_info'

    def test_user_params(self):
        user = mock.Mock()
        user.user_id = 1
        user.dept_id = 2
        get_params = self.factory.getUserParams
        self.assertEqual(-1, get_params(user, ('unknown_param',), ''))
        self.assertEqual('1 2', get_params(user, ('dept_id',), ' '))

    def test_wrong_request(self):
        self.assertEqual(self.processLine(''), '-1')
        self.assertEqual(self.processLine('_1_'), '-1')

    def test_inactive_user(self):
        self.service.getActiveUserByIp.return_value = None
        self.assertEqual(self.processLine('_1_login'), '0')

    def test_active_user(self):
        self.service.getActiveUserByIp.return_value.user_id = 2
        self.service.getActiveUserByIp.return_value.login = 'user'
        self.assertEqual(self.processLine('_1_login'), '2_user')


class TestAPIConstructor(unittest.TestCase):
    def setUp(self):
        self.constructor = APIConstructor

    def test_unknown_api(self):
        self.assertRaises(AttributeError,
                          self.constructor.construct, 'unknown_api', None)
