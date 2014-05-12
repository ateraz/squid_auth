squid_auth
==========

Service for IP based squid auth and session checking.

Squid 3.2+ config:
```
# Custom authenticator that always returns "OK" and links to the external acl
auth_param basic program <project_path>/clients/fake_auth_client.py
auth_param basic children 2
# ip_based_auth's dependence on %LOGIN is required for triggering authentication and, thus, setting %{Proxy-Authorization}.
external_acl_type ip_based_auth children-max=2 %SRC %{Proxy-Authorization} %LOGIN <project_path>/clients/auth_client.py 9999
acl verifiedUsers external ip_based_auth

# ACL for displaying page after login
external_acl_type welcome_page children-max=2 negative_ttl=1 %SRC <project_path>/clients/auth_client.py 9998
acl seenWelcomePage external welcome_page

acl welcomeUrl url_regex -i ^http://pastebin.com
http_access allow welcomeUrl
http_access deny !verifiedUsers
http_access deny !seenWelcomePage
http_access allow verifiedUsers
http_access deny all
deny_info 302:http://pastebin.com/raw.php?i=p0EtWttr seenWelcomePage

# Mapping requests to different outgoing IPs if performed with directives
#tcp_outgoing_address <IP_for_users_without_credentials> defaultUser
#tcp_outgoing_address <IP_for_users_with_credentials> verifiedUsers
