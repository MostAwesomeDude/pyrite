from argparse import ArgumentParser
import sys

from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react
from twisted.python import log
from twisted.python.filepath import FilePath

from pyrite.anidb import make_target, rename
from pyrite.guru import AniDBGuru


def lookup_and_rename(guru, s, source, dest):
    d = guru.lookup(source)

    def cb(values):
        target = make_target(dest, values, s)
        rename(source, target)

    def eb(e):
        log.msg("File %s not found" % source)

    d.addCallbacks(cb, eb)
    d.addCallback(lambda none: guru)

    return d


@inlineCallbacks
def rename_directory(guru, s, source, dest):
    for path in source.walk():
        if path.isfile():
            yield lookup_and_rename(guru, s, path, dest)


def teardown(protocol):
    return protocol.logout()


@inlineCallbacks
def main(reactor, username, password, s, source, dest):
    source = FilePath(source)
    dest = FilePath(dest)

    guru = AniDBGuru()
    yield guru.start(reactor, username, password)

    try:
        yield rename_directory(guru, s, source, dest)
    except:
        log.err()

    yield guru.stop()


def argv_parser():
    parser = ArgumentParser()
    parser.add_argument("-n", "--dry-run",
                        help="Dry run mode (no filesystem changes)",
                        action="store_true")
    parser.parse_args()


def app():
    log.startLogging(sys.stdout)
    argv_parser()
    react(main, sys.argv[1:])
