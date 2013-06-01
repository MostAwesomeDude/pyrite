from twisted.internet.protocol import DatagramProtocol


def pack(d):
    """
    Pack a dict into a str.
    """

    return "&".join("%s=%s" % t for t in d.items())


def request(s, d=None):
    """
    Make a request from a request type and dict of arguments.
    """

    if d:
        return "%s %s" % (s, pack(d))
    return s


class AniDBProtocol(DatagramProtocol):
    """
    A protocol for communicating with AniDB.
    """

    session = None
    timestamp = 0

    def __init__(self, reactor, address):
        self.reactor = reactor
        self.address = address

        self.lookups = {}

    def startProtocol(self):
        self.transport.connect(self.address, 9000)

    def datagramReceived(self, packet, remote):
        code, data = packet.split(" ", 1)
        code = int(code)

        if False:
            pass
        elif code == 200 or code == 201:
            # LOGIN ACCEPTED
            session, stuff = data.split(" ", 1)
            self.session = session
        elif code == 203 or code == 403:
            # LOGGED OUT, NOT LOGGED IN
            self.session = None
        elif code == 300:
            # PONG
            pass
        elif code == 500:
            # LOGIN FAILED
            raise Exception("Login failed")
        else:
            print packet
            raise Exception(packet)

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
        self.write("PING")

    def login(self, username, password):
        data = {
            "user": username,
            "pass": password,
            "protover": 3,
            "client": "openanidb",
            "clientver": 2,
        }

        payload = request("AUTH", data)
        self.write(payload)

    def logout(self):
        if self.session:
            payload = request("LOGOUT", {"s": self.session})
            self.write(payload)


def makeProtocol(reactor):
    d = reactor.resolve("api.anidb.info")

    @d.addCallback
    def cb(address):
        protocol = AniDBProtocol(reactor, address)
        reactor.listenUDP(0, protocol)
        return protocol

    return d
