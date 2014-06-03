#!/usr/bin/env python
import sys, select
from auth_client import trigger_on_stdin


@trigger_on_stdin
def fake_auth_client(auth_str):
    """Dummy authentifiaction function for Squid that always returns 'OK'.
    See auth_client.py for `trigger_on_stdin` decorator definition"""
    return 'OK\n'

if __name__ == '__main__':
    fake_auth_client()
