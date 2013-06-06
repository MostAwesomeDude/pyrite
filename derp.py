import sys

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import react
from twisted.python import log
from twisted.python.filepath import FilePath

from pyrite.anidb import make_protocol, make_target, rename
from pyrite.hashing import size_and_hash


@inlineCallbacks
def setup(reactor, username, password):
    p = yield make_protocol(reactor)

    yield p.login(username, password)
    yield p.encoding()

    returnValue(p)


def lookup_and_rename(protocol, s, source, dest):
    data = size_and_hash(source)
    d = protocol.lookup(*data)

    def cb(values):
        target = make_target(dest, values, s)
        rename(source, target)

    def eb(e):
        log.msg("File %s not found" % source)

    d.addCallbacks(cb, eb)
    d.addCallback(lambda none: protocol)

    return d


@inlineCallbacks
def rename_directory(protocol, s, source, dest):
    for path in source.walk():
        if path.isfile():
            yield lookup_and_rename(protocol, s, path, dest)


def teardown(protocol):
    return protocol.logout()


def main(reactor, username, password, s, source, dest):
    source = FilePath(source)
    dest = FilePath(dest)

    d = setup(reactor, username, password)

    @d.addCallback
    def ready(protocol):
        return rename_directory(protocol, s, source, dest)

    d.addCallback(teardown)

    return d


log.startLogging(sys.stdout)

react(main, sys.argv[1:])
