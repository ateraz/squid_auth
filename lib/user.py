"""Proxy user class definition"""

import datetime


class User(object):
    """Repsesents user that needs to be authorized and queried in API calls."""
    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
                 'login_time', 'is_authrorized']

    def __init__(self, **kwargs):
        for field in kwargs:
            setattr(self, field, kwargs[field])
        self.is_authrorized = False

    def connectFrom(self, ip):
        """Sets authorized user ip, remembers login time
        and marks user as valid.
        """
        self.ip = ip
        self.login_time = datetime.datetime.now()
        self.is_authrorized = True

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')
