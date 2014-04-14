#!/usr/bin/env python
import sys, select
from auth_client import trigger_on_stdin


@trigger_on_stdin
def fake_auth_client(auth_str):
    return 'OK\n'

if __name__ == '__main__':
    fake_auth_client()
