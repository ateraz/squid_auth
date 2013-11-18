#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, select
from auth_client import trigger_on_stdin


@trigger_on_stdin
def fake_auth_client(auth_str):
    return 'OK\n'

if __name__ == '__main__':
    sys.exit(fake_auth_client())
