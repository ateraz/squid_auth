squid_auth
==========

Service for IP based squid auth and session checking.

Squid config:
```
# ACL for users without credentials
acl defaultUser ident user
http_access allow defaultUser
# Custom authenticator that always returns "OK" and links to the external acl
auth_param basic program <project_path>/fake_auth_client.py
auth_param basic children 2
# ip_based_auth's dependence on %LOGIN is required for triggering authentication and, thus, setting %{Proxy-Authorization}.
external_acl_type ip_based_auth children=2 %SRC %{Proxy-Authorization} %LOGIN <project_path>/auth_client.py
acl verifiedUsers external ip_based_auth
http_access allow verifiedUsers
# Mapping requests to different outgoing IPs if performed with directives
#tcp_outgoing_address <IP_for_users_without_credentials> defaultUser
#tcp_outgoing_address <IP_for_users_with_credentials> verifiedUsers
