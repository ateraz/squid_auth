from twisted.application import internet, service
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.python import usage
from lib import Config, ConnectionPool, APIConstructor, AuthService


class AuthOptions(usage.Options):

    optParameters = [
        ['config_path', 'c', 'settings.yml', 'Configuration file path.']]


class AuthServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'squid_auth'
    description = 'A service for IP based squid auth and session checking.'
    options = AuthOptions

    def makeService(self, options):
        top_service = service.MultiService()
        config = Config(options['config_path'])
        connection_pool = ConnectionPool(config['database'])

        auth_service = AuthService(config['service'], connection_pool)
        auth_service.setServiceParent(top_service)

        for server in config['servers']:
            internet.TCPServer(
                int(config['servers'][server]['port']),
                APIConstructor.construct(server, auth_service),
                interface=config['servers'][server]['interface']
            ).setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()