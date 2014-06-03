#!/usr/bin/env python
import sys, select, socket, functools


def trigger_on_stdin(auth_func):
    """Decorator for input processing functions"""
    @functools.wraps(auth_func)
    def _auth_func(*args):
        while True:
            # Non-blocking method for waiting for input
            select.select([sys.stdin], [], [])
            sys.stdout.write(auth_func(sys.stdin.readline(), *args))
            sys.stdout.flush()
    return _auth_func

@trigger_on_stdin
def auth_client(auth_str, sock):
    """Function that redirects requests to authentification server
    and outputs server response"""
    sock.sendall(auth_str)
    return sock.recv(1024)

if __name__ == '__main__':
    # Connection to authentification server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', int(sys.argv[1])))
    auth_client(sock)
