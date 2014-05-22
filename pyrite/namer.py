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
    _replace = False
    _slash = "~"

    def __init__(self, guru, formatter, dry_run=None, replace=None,
                 slash=None):
        self._g = guru
        self._f = formatter

        if dry_run is not None:
            self._dr = dry_run

        if replace is not None:
            self._replace = replace

        if slash is not None:
            self._slash = slash

    def _rename(self, source, target):
        """
        Move a file from one location to another, if they aren't the same path.
        """

        if source == target:
            log.msg("%r is already named correctly" % source.path)
            return False

        if target.exists() and not self._replace:
            log.msg("Not copying over %r" % target.path)
            return False

        if self._dr:
            log.msg("Dry-run; not moving %r to %r"
                    % (source.path, target.path))
            return False

        parent = target.parent()
        if not parent.exists():
            log.msg("Making directory %r" % parent.path)
            parent.makedirs()
        log.msg("Moving %r to %r" % (source.path, target.path))
        source.moveTo(target)

        return True

    def _lookup(self, source):
        d = self._g.lookup(source)

        def cb(data):
            for k in data:
                # Replace all slashes, skipping non-strings.
                try:
                    data[k] = data[k].replace("/", self._slash)
                except AttributeError:
                    continue
            return data

        d.addCallback(cb)

        return d

    def augment(self, data, filepath):
        """
        Add file name information from the original file.
        """

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
                    log.msg("File %r not found" % path.path)
                except MultipleMatches:
                    log.msg("Can't deal with multiple matches yet")
                except OSError as e:
                    log.msg("OS error: %s" % e)
