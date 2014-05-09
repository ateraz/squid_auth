from twisted.trial import unittest
from lib import ConnectionPool


class TestConnectionPool(unittest.TestCase):
    def setUp(self):
        self.pool = ConnectionPool({'host': '', 'name': '', 'user': '',
                                    'passwd': ''})

    def test_with_error_handler(self):
        error = 'error'
        self.pool.setErrorHandler(lambda e: error)
        d = self.pool.runQuery('')
        d.addCallback(self.assertEqual, error)
        return d

    def test_without_error_handler(self):
        d = self.pool.runQuery('')
        # Fail test if query succeeded, pass otherwise.
        d.addCallbacks(self.fail, lambda f: None, callbackArgs='no exception')
        return d
