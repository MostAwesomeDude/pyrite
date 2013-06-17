from argparse import ArgumentParser
import sys

from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react
from twisted.python import log
from twisted.python.filepath import FilePath

from pyrite.guru import AniDBGuru
from pyrite.namer import Namer


@inlineCallbacks
def main(reactor, username, password, s, source, dest):
    source = FilePath(source)
    dest = FilePath(dest)

    guru = AniDBGuru()
    namer = Namer(guru, s, True)
    yield guru.start(reactor, username, password)

    try:
        yield namer.rename(source, dest)
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
