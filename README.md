squid_auth
==========

Service for IP based squid auth and session checking.

Squid config:
```
# Custom authenticator that always returns "OK" and
# links to the external acl
auth_param basic program <path_to_project>/fake_auth.py
# ip_based_auth's dependence on %LOGIN is required for triggering
# authentication and, thus, setting %{Proxy-Authorization}.
external_acl_type ip_based_auth %SRC %LOGIN %{Proxy-Authorization} <path_to_project>/auth_client.py
acl verifiedUsers external ip_based_auth REQUIRED
http_access allow verifiedUsers
```
