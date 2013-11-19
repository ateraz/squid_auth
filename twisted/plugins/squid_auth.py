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
        users = [
            ('user_with_access', 'pass', '127.0.0.1'),
            ('user_without_access', 'pass', '127.0.0.1')]

        top_service = service.MultiService()

        auth_service = AuthService(users)
        auth_service.setServiceParent(top_service)

        tcp_service = internet.TCPServer(
            int(options['port']), AuthFactory(auth_service),
            interface=options['iface'])
        tcp_service.setServiceParent(top_service)

        return top_service


serviceMaker = AuthServiceMaker()