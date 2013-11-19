from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.application import internet, service
from auth_server import AuthService, AuthFactory, AuthServerOptions


class AuthServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'squid_auth'
    description = 'A service for IP based squid auth and session checking.'
    options = AuthServerOptions

    def makeService(self, options):
        top_service = service.MultiService()

        auth_service = AuthService()
        auth_service.setServiceParent(top_service)

        tcp_service = internet.TCPServer(
            int(options['port']), AuthFactory(auth_service),
            interface=options['iface'])
        tcp_service.setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()