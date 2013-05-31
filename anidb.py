from twisted.internet.protocol import DatagramProtocol
from twisted.internet.defer import Deferred


class AniDBProtocol(DatagramProtocol):
    """
    A protocol for communicating with AniDB.
    """

    d = None
    timestamp = 0
    next_state = "default"

    def __init__(self, reactor, address):
        self.reactor = reactor
        self.address = address

    def startProtocol(self):
        self.transport.connect(self.address, 9000)

    def datagramReceived(self, data, remote):
        handler = getattr(self, "recv_%s" % self.next_state)
        handler(data)

    def recv_default(self, data):
        print data

    def recv_pong(self, data):
        print data
        self.d.callback(data.startswith("300"))

    def write(self, packet):
        """
        Write a packet of data, eventually.
        """

        current = self.reactor.seconds()
        diff = current - self.timestamp

        if diff >= 4:
            # We're good to send right now.
            self.transport.write(packet)
            self.timestamp = current
        else:
            # We'll send in the future, when it's safe.
            target = 4 - diff
            self.reactor.callLater(target, self.transport.write, packet)
            self.timestamp = current + target

    def ping(self):
        self.d = Deferred()
        self.write("PING")
        self.next_state = "pong"
        return self.d


def makeProtocol(reactor):
    d = reactor.resolve("api.anidb.info")

    @d.addCallback
    def cb(address):
        protocol = AniDBProtocol(reactor, address)
        reactor.listenUDP(0, protocol)
        return protocol

    return d
