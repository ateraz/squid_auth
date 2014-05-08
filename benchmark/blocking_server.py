"""Prototype of blocking tcp server"""

import MySQLdb
import socket


class Connection:

    db = MySQLdb.connect(
        db='squid_auth', user='squid',
        passwd='not_secure_pass', host='91.202.128.106'
    ).cursor()

    def __init__(self, sock):
        self.sock = sock

    def dataReceived(self):
        self.sock.recv(1024)
        self.db.execute(
            'SELECT * FROM users_all WHERE login=%s AND passwd=%s',
            ('login', 'pass'))
        self.respond(self.db.fetchone())

    def respond(self, _):
        self.sock.sendall('OK')
        self.sock.close()


if __name__ == '__main__':
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('localhost', 9999))
    listen_socket.listen(1000)
    while True:
        sock, addr = listen_socket.accept()
        Connection(sock).dataReceived()
