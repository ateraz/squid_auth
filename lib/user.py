# -*- test-case-name: tests.test_user -*-
"""Proxy user class definition"""

import datetime


class User(object):
    """Repsesents user that needs to be authorized and queried in API calls."""
    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
                 'login_time', 'is_authorized', 'seen_welcome']

    def __init__(self, **kwargs):
        """Creates new user, sets default values."""
        for field in kwargs:
            setattr(self, field, kwargs[field])
        self.is_authorized = False
        self.seen_welcome = False

    def connectFrom(self, ip):
        """Sets authorized user ip, remembers login time
        and marks user as valid.
        """
        self.ip = ip
        self.login_time = datetime.datetime.now()
        self.is_authorized = True

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')
