from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.application import internet, service
from auth_server import AuthService, AuthFactory, AuthServerOptions, AuthConfigurator

class AuthServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'squid_auth'
    description = 'A service for IP based squid auth and session checking.'
    options = AuthServerOptions

    def makeService(self, options):
        top_service = service.MultiService()
        config = AuthConfigurator(options['config_path'])

        auth_service = AuthService(config)
        auth_service.setServiceParent(top_service)

        tcp_service = internet.TCPServer(
            int(config['server']['port']), AuthFactory(auth_service),
            interface=config['server']['interface'])
        tcp_service.setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()