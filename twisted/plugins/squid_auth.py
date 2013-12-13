from twisted.application.service import ServiceMaker

squid_auth_service = ServiceMaker(
    'Squid auth',
    'twisted.tap.squid_auth',
    'A service for IP based squid auth and session checking.',
    'squid_auth')