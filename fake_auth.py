#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import select

def try_on_stdin(auth_func):
    def _auth_func(*args):
        while True:
            _ = select.select([sys.stdin], [], [])
            sys.stdout.write(auth_func(sys.stdin.readline(), *args))
            sys.stdout.flush()
    return _auth_func

@try_on_stdin
def fake_auth(auth_str):
    return 'OK\n'

if __name__ == '__main__':
    sys.exit(fake_auth())
