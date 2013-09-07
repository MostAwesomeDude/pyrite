from twisted.internet.defer import fail, inlineCallbacks
from zope.interface import Interface, implements

from pyrite.anidb import make_protocol
from pyrite.osdb import OSDB, derphash
from pyrite.hashing import size_and_hash


class IGuru(Interface):
    """
    A knower of truth and file hashes.
    """

    def identify(filepath):
        pass


class AniDBGuru(object):

    implements(IGuru)

    _p = None

    @inlineCallbacks
    def start(self, reactor, username, password):
        self._p = p = yield make_protocol(reactor)

        yield p.login(username, password)
        yield p.encoding()

    def stop(self):
        if self._p:
            d = self._p.logout()
            @d.addCallback
            def cb(chaff):
                self._p = None
            return d

        return fail("Not logged in!")

    def lookup(self, filepath):
        if self._p:
            data = size_and_hash(filepath)
            return self._p.lookup(*data)

        return fail("Not logged in!")


class OSDBGuru(object):

    implements(IGuru)

    _db = None

    def start(self, reactor, username, password):
        # Annoyingly, the XML-RPC Proxy doesn't parameterize the reactor.
        self._db = OSDB()
        return self._db.login(username, password)

    def stop(self):
        if self._db:
            d = self._db.logout()
            @d.addCallback
            def cb(chaff):
                self._db = None
            return d

        return fail("Not logged in!")

    def lookup(self, filepath):
        if self._db:
            derp = derphash(filepath)
            d = self._db.search(derp)

            @d.addCallback
            def cb(data):
                if len(data) > 1:
                    raise Exception("Too many entries")
                return data[0]

        return fail("Not logged in!")
