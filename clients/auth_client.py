#!/usr/bin/env python
import sys, select, socket, functools


def trigger_on_stdin(auth_func):
    @functools.wraps(auth_func)
    def _auth_func(*args):
        while True:
            select.select([sys.stdin], [], [])
            sys.stdout.write(auth_func(sys.stdin.readline(), *args))
            sys.stdout.flush()
    return _auth_func

@trigger_on_stdin
def auth_client(auth_str, sock):
    sock.sendall(auth_str)
    return sock.recv(1024)

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 9999))
    auth_client(sock)
