#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import select
import socket

def check(auth_str, sock):
    sock.sendall(auth_str)
    return sock.recv(1024)

def try_on_stdin(auth_func):
    def _auth_func(*args):
        while True:
            _ = select.select([sys.stdin], [], [])
            data = auth_func(sys.stdin.readline(), *args)
            sys.stdout.write(data)
            sys.stdout.flush()
    return _auth_func

@try_on_stdin
def auth_client(auth_str, sock):
    sys.stderr.write('Got request ' + auth_str)
    return check(auth_str, sock)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 9999))
    auth_client(sock)

if __name__ == '__main__':
    sys.exit(main())
