from argparse import ArgumentParser
import sys

from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react
from twisted.python import log
from twisted.python.filepath import FilePath

from pyrite.guru import AniDBGuru
from pyrite.namer import Namer


@inlineCallbacks
def main(reactor, args):
    source = FilePath(args.source)
    dest = FilePath(args.dest)

    guru = AniDBGuru()
    namer = Namer(guru, args.formatter, args.dry_run)
    yield guru.start(reactor, args.username, args.password)

    try:
        yield namer.rename(source, dest)
    except:
        log.err()

    yield guru.stop()


def argv_parser():
    formatter = "{series}/{series} - {eid} - {episode} - [{group}].{fext}"
    parser = ArgumentParser()
    parser.add_argument("-n", "--dry-run",
                        help="Dry run mode (no filesystem changes)",
                        action="store_true")
    parser.add_argument("-f", "--formatter", help="Formatting string to use",
                        default=formatter)
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("source")
    parser.add_argument("dest")
    return parser.parse_args()


def app():
    log.startLogging(sys.stdout)
    args = argv_parser()
    react(main, (args,))
