"""Mysql connection pool with error handling"""

import MySQLdb
from twisted.enterprise import adbapi


class ConnectionPool(adbapi.ConnectionPool):
    """Async MySQL connection pool.
    Provides error handling possibilities."""
    def __init__(self, config):
        adbapi.ConnectionPool.__init__(
            self, 'MySQLdb', host=config['host'], db=config['name'],
            user=config['user'], passwd=config['passwd'])

    def setErrorHandler(self, error_handler):
        self.error_handler = error_handler

    def _runInteraction(self, interaction, *args, **kw):
        try:
            return adbapi.ConnectionPool._runInteraction(
                self, interaction, *args, **kw)
        except MySQLdb.OperationalError as e:
            return self.error_handler(e)
