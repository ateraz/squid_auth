from twisted.internet import reactor, defer, protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.threads import deferToThread
from time import time

class ClientProtocol(LineReceiver):

    def connectionMade(self):
        self.sendLine('ip type dXNlcjpwYXNz')

    def dataReceived(self, data):
        self.factory.update()


class ClientFactory(protocol.ClientFactory):

    protocol = ClientProtocol

    def __init__(self, jobs, clients):
        self.proceeded = 0
        self.jobs= jobs
        self.clients = clients
        self.started = time()

    def update(self):
        self.proceeded += 1
        if self.proceeded == self.jobs:
            print 'Got {0} responses for {1} clients in {2} s'.format(
                self.jobs, self.clients, time() - self.started)

def measure(jobs, clients):
    reactor.suggestThreadPoolSize(clients)
    factory = ClientFactory(jobs, clients)
    for i in range(jobs):
        deferToThread(reactor.connectTCP, 'localhost', 9999, factory)

if __name__ == '__main__':
    clients = 50
    jobs = 10000
    measure(jobs, clients)
    reactor.run()
