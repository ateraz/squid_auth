from twisted.application import internet, service
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.python import usage
from lib import Config, ConnectionPool, APIConstructor, AuthService


class AuthOptions(usage.Options):
    """Console options parser"""

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthServiceMaker(object):
    """Service objects factory"""
    implements(service.IServiceMaker, IPlugin)
    tapname = 'squid_auth'
    description = 'A service for IP based squid auth and session checking.'
    options = AuthOptions

    def makeService(self, options):
        """Method for constructing service objects"""
        # Parent object for all services, Starts child services when necessary
        top_service = service.MultiService()
        config = Config(options['config_path'])
        connection_pool = ConnectionPool(config['database'])

        # Authentification service used by external APIs
        auth_service = AuthService(config['service'], connection_pool)
        auth_service.setServiceParent(top_service)

        for server in config['servers']:
            # Constructing APIs from config
            internet.TCPServer(
                int(config['servers'][server]['port']),
                APIConstructor.construct(server, auth_service),
                interface=config['servers'][server]['interface']
            ).setServiceParent(top_service)

        return top_service


# Objects that creates plugin service object
serviceMaker = AuthServiceMaker()
