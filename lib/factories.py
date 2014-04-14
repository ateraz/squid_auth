"""API factories and constructor definitions"""

import datetime
import base64
from twisted.protocols.basic import LineReceiver
from twisted.internet import protocol
from twisted.python import log


class _BaseProtocol(LineReceiver):
    """Base protocol for implementing socket APIs."""
    delimiter = b'\n'

    def lineReceived(self, line):
        self.sendLine(self.factory.processLine(line.strip()))


class _BaseFactory(protocol.ServerFactory):
    """Factory instantiating base protocol instances
    and implementing API logic."""
    protocol = _BaseProtocol

    def __init__(self, service):
        self.service = service

    def processLine(self, line):
        """Abstract method that should be implemented in child classes.
        Contains logic for building response for API calls."""
        raise NotImplementedError(
            'Method lineReceived should be implemented in subclass')


class ValidatorFactory(_BaseFactory):
    """API used by squid for validating proxy users."""
    valid_response = 'OK'
    invalid_response = 'ERR'

    def processLine(self, line):
        auth_params = self.parseAuthString(line)
        if not auth_params:
            log.msg('Bad auth string format')
            return self.invalid_response
        user = self.service.validateUser(auth_params)
        status = 'valid' if user.is_authrorized else 'invalid'
        return getattr(self, status + '_response')

    @staticmethod
    def parseAuthString(auth_str):
        parts = auth_str.replace('%20', ' ').split()
        try:
            credentials = base64.b64decode(parts[2]).split(':')
            return parts[0], credentials[0], credentials[1]
        except:
            return None


class IpCheckerFactory(_BaseFactory):
    """API for getting user ID of current proxy users."""
    def processLine(self, line):
        return str(self.service.getActiveUserIdByIp(line))


class IpInfoFactory(_BaseFactory):
    """API for getting more detailed info about active proxy users."""
    allowed_fields = ['login', 'dept_id', 'admin_level']

    def processLine(self, line):
        separator = line[0]
        return str(self.buildResponseString(line.split(separator), separator))

    def buildResponseString(self, parts, separator):
        if len(parts) < 3:
            return -1
        user = self.service.getActiveUserByIp(parts[1])
        if not user:
            return 0
        return self.getUserParams(user, parts[2:], separator)

    def getUserParams(self, user, params, separator):
        user_params = []
        for param in params:
            if param in self.allowed_fields:
                user_params.append(getattr(user, param))
            else:
                return -1
        user_params.insert(0, user.user_id)
        return separator.join(map(str, user_params))


class APIConstructor:
    """API builder.
    Class implementing factory design pattern
    that instantiates API instances for application."""
    validator = ValidatorFactory
    ip_checker = IpCheckerFactory
    ip_info = IpInfoFactory

    @classmethod
    def construct(cls, factory_name, service):
        return getattr(cls, factory_name)(service)
