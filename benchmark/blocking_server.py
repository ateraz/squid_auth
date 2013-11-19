import MySQLdb, socket

def respond(sock, cursor):
    cursor.execute('SELECT * FROM users_all WHERE login=%s AND passwd=%s',
          ('user', 'pass'))
    print cursor.fetchone()
    sock.sendall('OK\r\n')
    sock.close()


if __name__ == '__main__':
    db = MySQLdb.connect(db='squid_auth', user='root')
    cursor = db.cursor()

    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('localhost', 9999))
    listen_socket.listen(100)
    while True:
        sock, addr = listen_socket.accept()
        respond(sock, cursor)
