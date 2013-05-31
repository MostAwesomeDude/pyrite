from twisted.internet.protocol import DatagramProtocol
from twisted.internet.defer import Deferred


class AniDBProtocol(DatagramProtocol):
    """
    A simple protocol for communicating with AniDB.
    """

    d = None
    next_state = "default"

    def __init__(self, address):
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

    def ping(self):
        self.d = Deferred()
        self.transport.write("PING")
        self.next_state = "pong"
        return self.d


def makeProtocol(reactor):
    d = reactor.resolve("api.anidb.info")

    @d.addCallback
    def cb(address):
        port = 9000
        protocol = AniDBProtocol(address)
        reactor.listenUDP(port, protocol)
        return protocol

    return d
