# -*- test-case-name: tests.test_connection_pool -*-
"""Mysql connection pool with error handling"""

import MySQLdb
from twisted.enterprise import adbapi


class ConnectionPool(adbapi.ConnectionPool):
    """Async MySQL connection pool.
    Provides error handling possibilities."""
    _pool = adbapi.ConnectionPool

    def __init__(self, config):
        self._pool.__init__(
            self, 'MySQLdb', host=config['host'], db=config['name'],
            user=config['user'], passwd=config['passwd'])
        self.error_handler = None

    def setErrorHandler(self, error_handler):
        """Error handler setter for connection pool."""
        self.error_handler = error_handler

    def _runInteraction(self, interaction, *args, **kw):
        """Wrapper of twisted's method with error handling."""
        try:
            return self._pool._runInteraction(
                self, interaction, *args, **kw)
        except MySQLdb.OperationalError as e:
            if self.error_handler:
                return self.error_handler(e)
            raise e
