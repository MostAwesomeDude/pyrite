# Copyright (C) 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from argparse import (ArgumentDefaultsHelpFormatter,
                      RawDescriptionHelpFormatter, ArgumentParser)
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

def pick_style(args):
    """
    From command-line arguments, determine which guru and formatter to use.
    """

    guru = None
    formatter = None

    if args.anime:
        guru = "anidb"
        formatter = "{series}/{series} - {eid:02d} - {title} - [{group}].{fext}"
    elif args.movie:
        guru = "osdb"
        formatter = "{title} ({year}).{ext}"
    elif args.tv:
        guru = "osdb"
        formatter = "{sid:02d}x{eid:02d} - {title}.{ext}"

    if not guru:
        print "WARNING: Guru not specified; defaulting to OSDB"
        guru = "osdb"
    elif guru not in gurus:
        raise ValueError("Unknown guru: " + args.guru)

    if not formatter:
        raise ValueError("No formatter specified!")

    print "Using formatter: %r" % formatter
    print "Using guru: %s" % guru

    guru = gurus[guru]()

    return guru, formatter


def main():
    args = argv_parser()

    # Determine which guru and formatter we're using.
    guru, formatter = pick_style(args)

    source = FilePath(args.source)
    dest = FilePath(args.dest)

    namer = Namer(guru, formatter, dry_run=args.dry_run, replace=args.replace,
                  slash=args.slash)

    log.startLogging(sys.stdout)
    react(react_main, (guru, namer, source, dest, args))


@inlineCallbacks
def react_main(reactor, guru, namer, source, dest, args):
    yield guru.start(reactor, args.username, args.password)

    try:
        yield namer.rename(source, dest)
    finally:
        yield guru.stop()


formatter_help = """
Help on Formatters
------------------

Formatters are standard Python string formatting strings.

Available keys on all gurus (builtin):
    * ext: Original file extension

Available keys on all gurus (standard):
    * title: Title of episode or section
    * eid: Episode number

Additional keys for "osdb":
    * sid: Season number

Additional keys for "anidb":
    * series: Name of series
    * fid: Unique file ID
    * fext: Actual file extension
    * eid_total: Total number of episodes
    * eid_highest: Highest known episode number
    * group: Name of subtitle or release group
"""


class PyriteFormatter(ArgumentDefaultsHelpFormatter,
                      RawDescriptionHelpFormatter):
    """
    A hack to keep the epilog from being mangled while still making the help
    nice and pretty.
    """


def argv_parser():
    # The formatter_class kwarg changes the parser's help output to include
    # default information. Helpful, right?
    parser = ArgumentParser(formatter_class=PyriteFormatter,
                            epilog=formatter_help)
    parser.add_argument("-n", "--dry-run",
                        help="Dry run mode (no filesystem changes)",
                        action="store_true")
    parser.add_argument("-r", "--replace",
                        help="Enable replacement of existing files",
                        action="store_true")
    parser.add_argument("-g", "--guru", help="Which database to access")
    parser.add_argument("-f", "--formatter", help="Formatting string to use")
    parser.add_argument("-s", "--slash",
                        help="Character which replaces forward slashes",
                        default="~")
    presets = parser.add_mutually_exclusive_group()
    presets.add_argument("--anime",
                         help="Use AniDB and simple anime name formatting",
                         action="store_true")
    presets.add_argument("--movie",
                         help="Use OSDB and simple film name formatting",
                         action="store_true")
    presets.add_argument("--tv",
                         help="Use OSDB and simple tv name formatting",
                         action="store_true")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("source")
    parser.add_argument("dest")
    return parser.parse_args()
