from twisted.application import internet, service
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.python import usage
from auth_server import AuthService, AuthConfig, ServiceFactory


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
        config = AuthConfig(options['config_path'])

        auth_service = AuthService(config)
        auth_service.setServiceParent(top_service)

        for server in config['servers']:
            internet.TCPServer(
                int(config['servers'][server]['port']),
                ServiceFactory.construct(server, auth_service),
                interface=config['servers'][server]['interface']
            ).setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()