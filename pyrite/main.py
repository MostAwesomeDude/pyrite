from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import sys

from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react
from twisted.python import log
from twisted.python.filepath import FilePath

from pyrite.guru import AniDBGuru, OSDBGuru
from pyrite.namer import Namer

gurus = {
    "anidb": AniDBGuru,
    "osdb": OSDBGuru,
}

@inlineCallbacks
def main(reactor, args):
    source = FilePath(args.source)
    dest = FilePath(args.dest)

    if args.guru not in gurus:
        raise ValueError("Unknown guru: " + args.guru)
    guru = gurus[args.guru]()

    namer = Namer(guru, args.formatter, dry_run=args.dry_run,
                  replace=args.replace, slash=args.slash)

    yield guru.start(reactor, args.username, args.password)

    try:
        yield namer.rename(source, dest)
    finally:
        yield guru.stop()


def argv_parser():
    formatter = "{series}/{series} - {eid} - {episode} - [{group}].{fext}"
    # The formatter_class kwarg changes the parser's help output to include
    # default information. Helpful, right?
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n", "--dry-run",
                        help="Dry run mode (no filesystem changes)",
                        action="store_true")
    parser.add_argument("-r", "--replace",
                        help="Enable replacement of existing files",
                        action="store_true")
    parser.add_argument("-f", "--formatter", help="Formatting string to use",
                        default=formatter)
    parser.add_argument("-s", "--slash",
                        help="Character which replaces forward slashes",
                        default="~")
    parser.add_argument("guru")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("source")
    parser.add_argument("dest")
    return parser.parse_args()


def app():
    args = argv_parser()
    log.startLogging(sys.stdout)
    react(main, (args,))
