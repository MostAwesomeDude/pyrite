from collections import deque
from datetime import timedelta

from twisted.internet.defer import Deferred, DeferredLock
from twisted.internet.protocol import DatagramProtocol
from twisted.python import log

class Log(object):

    @staticmethod
    def msg(s):
        print repr(s)

log = Log()


class Trickling(object):

    def __init__(self, reactor, transport):
        self.reactor = reactor
        self.transport = transport

        self.timestamp = reactor.seconds()

    def write(self, packet):
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
        return "%s %s\n" % (s, pack(d))
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

        self._ds = deque()
        self._lock = DeferredLock()

    def startProtocol(self):
        self.transport.connect(self.address, 9000)
        self.transport = Trickling(self.reactor, self.transport)

    def datagramReceived(self, packet, remote):
        log.msg("< %r" % packet)

        d = self._ds.popleft()
        d.callback(packet)

        # Lock--
        self._lock.release()

        return

        code, data = packet.split(" ", 1)
        code = int(code)
        data = data.strip()

        if False:
            pass
        elif code == 200 or code == 201:
            # LOGIN ACCEPTED
            session, stuff = data.split(" ", 1)
            self.session = session

            log.msg("Logged in; session %s" % session)

            # Immediately after logging in, set the encoding for the session,
            # and get some information from the server.
            self.encoding()
            self.version()
            self.uptime()
        elif code == 203 or code == 403:
            # LOGGED OUT, NOT LOGGED IN
            self.session = None

            log.msg("Logged out")
        elif code == 208:
            # UPTIME
            print data
            stuff, uptime = data.split("\n", 1)
            uptime = timedelta(milliseconds=int(uptime))

            log.msg("Server uptime: %s" % uptime)
        elif code == 219:
            # ENCODING CHANGED
            pass
        elif code == 220:
            # FILE
            print data
            pass
        elif code == 300:
            # PONG
            pass
        elif code == 320:
            # NO SUCH FILE
            pass
        elif code == 500:
            # LOGIN FAILED
            raise Exception("Login failed")
        elif code == 519:
            # ENCODING NOT SUPPORTED
            pass
        elif code == 998:
            # VERSION
            print data
            stuff, version = data.split("\n", 1)

            log.msg("Server version: %s" % version)
        else:
            print packet
            raise Exception(packet)

    def write(self, packet):
        """
        Write a packet of data, eventually.
        """

        log.msg("> %r" % packet)

        # Lock++
        d = self._lock.acquire()
        d.addCallback(lambda lock: self.transport.write(packet))

        return d

    def ping(self):
        payload = request("PING")
        self.write(payload)

        d = Deferred()
        self._ds.append(d)

        return d

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

    def encoding(self):
        data = {
            "s": self.session,
            "name": "UTF8",
        }
        payload = request("ENCODING", data)
        self.write(payload)

    def version(self):
        payload = request("VERSION")
        self.write(payload)

    def uptime(self):
        if self.session:
            payload = request("UPTIME", {"s": self.session})
            self.write(payload)

    def lookup(self, size, ed2k):
        d = Deferred()
        self.lookups[size, ed2k] = d

        data = {
            "ed2k": ed2k,
            "size": size,
            "amask": "a020a040",
            "fmask": "00a0000000",
            "s": self.session,
        }

        payload = request("FILE", data)
        self.write(payload)

        return d


def makeProtocol(reactor):
    d = reactor.resolve("api.anidb.info")

    @d.addCallback
    def cb(address):
        protocol = AniDBProtocol(reactor, address)
        reactor.listenUDP(0, protocol)
        return protocol

    return d
