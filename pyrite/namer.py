from twisted.internet.defer import inlineCallbacks
from twisted.python import log


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

    def __init__(self, guru, formatter, dry_run):
        self._g = guru
        self._f = formatter
        self._dr = dry_run

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

        @d.addErrback
        def eb(e):
            log.msg("File %s not found" % source)

        return d

    @inlineCallbacks
    def rename(self, source, dest):
        for path in source.walk():
            if path.isfile():
                data = yield self._lookup(path)
                target = make_target(dest, data, self._f)
                yield self._rename(path, target)
