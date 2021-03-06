# -*- test-case-name: tests.test_factories -*-
"""API factories and constructor definitions"""

import datetime
import base64
from twisted.protocols.basic import LineReceiver
from twisted.internet import protocol
from twisted.python import log


class _BaseProtocol(LineReceiver):
    """Base protocol for implementing socket APIs"""
    delimiter = b'\n'

    def lineReceived(self, line):
        """Method called when received new line from client"""
        self.sendLine(self.factory.processLine(line.strip()))


class _BaseFactory(protocol.ServerFactory):
    """Factory instantiating base protocol instances
    and implementing API logic"""
    protocol = _BaseProtocol

    def __init__(self, service):
        self.service = service

    def processLine(self, line):
        """Abstract method that should be implemented in child classes
        and contain logic for building response for API calls"""
        raise NotImplementedError(
            'Method lineReceived should be implemented in subclass')


class ValidatorFactory(_BaseFactory):
    """API used by squid for validating proxy users"""
    valid_response = 'OK'
    invalid_response = 'ERR'

    def processLine(self, line):
        auth_params = self.parseAuthString(line)
        if not auth_params:
            log.msg('Bad auth string format')
            return self.invalid_response
        if self.service.validateUser(auth_params):
            return self.valid_response
        return self.invalid_response

    @staticmethod
    def parseAuthString(auth_str):
        """Method to extract user access params from response string"""
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
            return parts[0], credentials[0], credentials[1]
        except:
            return None


class SessionFactory(_BaseFactory):
    """Optional API for checking if user already seen welcome page"""
    valid_response = 'OK'
    invalid_response = 'ERR'

    def processLine(self, line):
        user = self.service.getActiveUserByIp(line)
        if not user:
            return self.invalid_response
        elif not user.seen_welcome:
            user.seen_welcome = True
            return self.invalid_response
        return self.valid_response


class IpCheckerFactory(_BaseFactory):
    """API for getting user ID of current proxy users"""
    def processLine(self, line):
        return str(self.service.getActiveUserIdByIp(line))


class IpInfoFactory(_BaseFactory):
    """API for getting more detailed info about active proxy users"""
    allowed_fields = ['login', 'dept_id', 'admin_level']

    def processLine(self, line):
        return str(self.buildResponseString(line))

    def buildResponseString(self, line):
        """Constructs response string depending on response format"""
        if not len(line):
            return -1
        separator = line[0]
        parts = line.split(separator)
        if len(parts) < 3:
            return -1
        user = self.service.getActiveUserByIp(parts[1])
        if not user:
            return 0
        return self.getUserParams(user, parts[2:], separator)

    def getUserParams(self, user, params, separator):
        """Returning user params for proper request, -1 otherwise"""
        user_params = []
        for param in params:
            if param in self.allowed_fields:
                user_params.append(getattr(user, param))
            else:
                return -1
        user_params.insert(0, user.user_id)
        return separator.join(map(str, user_params))


class APIConstructor:
    """API builder class implementing factory design pattern
    that instantiates API instances for application"""
    validator = ValidatorFactory
    ip_checker = IpCheckerFactory
    ip_info = IpInfoFactory
    session = SessionFactory

    @classmethod
    def construct(cls, factory_name, service):
        return getattr(cls, factory_name)(service)
