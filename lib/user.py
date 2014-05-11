# -*- test-case-name: tests.test_user -*-
"""Proxy user class definition"""

import datetime


class User(object):
    """Repsesents user that needs to be authorized and queried in API calls."""
    __slots__ = ['ip', 'user_id', 'dept_id', 'login', 'passwd', 'admin_level',
                 'created', 'updated', 'login_time', 'last_active',
                 'is_authorized', 'seen_welcome']

    def __init__(self, **kwargs):
        """Creates new user, sets default values."""
        for field in kwargs:
            setattr(self, field, kwargs[field])
        self.created = datetime.datetime.now()
        self.is_authorized = False
        self.seen_welcome = False

    def connectFrom(self, ip):
        """Sets authorized user ip, remembers login time
        and marks user as valid.
        """
        self.ip = ip
        self.last_active = self.login_time = datetime.datetime.now()
        self.is_authorized = True

    def _updateField(self, field, value):
        if getattr(self, field, '') != value:
            setattr(self, field, value)
            return True
        return False

    def update(self, **fields):
        updated = False
        for field in fields:
            updated += self._updateField(field, fields[field])
        if updated:
            self.updated = datetime.datetime.now()

    def updateLastActivity(self):
        self.last_active = datetime.datetime.now()

    # Used in callback command string formatting
    def __getitem__(self, key):
        return getattr(self, key, '')
