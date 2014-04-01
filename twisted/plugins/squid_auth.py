from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.application import internet, service
from auth_server import (AuthService, AuthOptions, AuthConfigurator,
    ValidatorFactory, CheckerFactory)

class AuthServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'squid_auth'
    description = 'A service for IP based squid auth and session checking.'
    options = AuthOptions

    def makeService(self, options):
        top_service = service.MultiService()
        config = AuthConfigurator(options['config_path'])

        auth_service = AuthService(config)
        auth_service.setServiceParent(top_service)

        validator = internet.TCPServer(
            int(config['validator']['port']), ValidatorFactory(auth_service),
            interface=config['validator']['interface'])
        validator.setServiceParent(top_service)

        checker = internet.TCPServer(
            int(config['checker']['port']), CheckerFactory(auth_service),
            interface=config['checker']['interface'])
        checker.setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()