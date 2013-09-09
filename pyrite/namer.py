from twisted.internet.defer import inlineCallbacks
from twisted.python import log

from pyrite.errors import FileNotFound, MultipleMatches


def make_target(filepath, data, s):
    """
    Extend a filepath with some data and a formatting string.
    """

    formatted = s.format(**data)
    for segment in formatted.split("/"):
        filepath = filepath.child(segment)
    return filepath


class Namer(object):
    """
    One which gives names to files.
    """

    _dr = True
    _slash = "~"

    def __init__(self, guru, formatter, dry_run=None, slash=None):
        self._g = guru
        self._f = formatter

        if dry_run is not None:
            self._dr = dry_run

        if slash is not None:
            self._slash = slash

    def _rename(self, source, target):
        """
        Move a file from one location to another, if they aren't the same path.
        """

        if source == target:
            log.msg("%s is already named correctly" % source)
            return False

        if self._dr:
            log.msg("Dry-run; not moving %s to %s" % (source, target))
            return False

        parent = target.parent()
        if not parent.exists():
            log.msg("Making directory %s" % parent)
            parent.makedirs()
        log.msg("Moving %s to %s" % (source, target))
        source.moveTo(target)

        return True

    def _lookup(self, source):
        d = self._g.lookup(source)

        def cb(data):
            for k in data:
                # Replace all slashes.
                data[k] = data[k].replace("/", self._slash)
            return data

        d.addCallback(cb)

        return d

    def augment(self, data, filepath):
        root, ext = filepath.splitext()
        data["ext"] = ext[1:]

    @inlineCallbacks
    def rename(self, source, dest):
        for path in source.walk():
            if path.isfile():
                try:
                    data = yield self._lookup(path)
                    self.augment(data, path)
                    target = make_target(dest, data, self._f)
                    yield self._rename(path, target)
                except FileNotFound:
                    log.msg("File %s not found" % path)
                except MultipleMatches:
                    log.msg("Can't deal with multiple matches yet")
                except OSError as e:
                    log.msg("OS error: %s" % e)
