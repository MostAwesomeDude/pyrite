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
from twisted.internet.defer import fail, inlineCallbacks
from zope.interface import Interface, implements

from pyrite.anidb import make_protocol
from pyrite.errors import FileNotFound, MultipleMatches
from pyrite.hashing import size_and_hash
from pyrite.helpers import remap_keys
from pyrite.osdb import OSDB, derphash


class NotLoggedIn(Exception):
    """
    Not logged in.
    """


class IGuru(Interface):
    """
    A knower of truth and file hashes.
    """

    def start(reactor, username, password):
        pass

    def stop():
        pass

    def lookup(filepath):
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

        return fail(NotLoggedIn())

    def lookup(self, filepath):
        if self._p:
            data = size_and_hash(filepath)
            return self._p.lookup(*data)

        return fail(NotLoggedIn())


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

        return fail(NotLoggedIn())

    def lookup(self, filepath):
        if self._db:
            # Files shorter than 128KiB will not be in the database. As a
            # hack, this also prevents files shorter than 64KiB from breaking
            # the hashing algorithm. Derpy but works.
            if filepath.getsize() < 128 * 1024:
                return fail(FileNotFound())

            with filepath.open("rb") as handle:
                derp = derphash(handle)
            d = self._db.search(derp)

            @d.addCallback
            def cb(data):
                if len(data) > 1:
                    raise MultipleMatches()
                data = data[0]

                # Season and episode IDs will be "0" when movies are looked
                # up, so remapping them is safe.
                mapping = {
                    "SeriesSeason": "sid",
                    "SeriesEpisode": "eid",
                    "MovieName": "title",
                    "MovieYear": "year",
                }

                data = remap_keys(mapping, data)

                for k in ("eid", "sid", "year"):
                    data[k] = int(data[k])

                return data

            return d

        return fail(NotLoggedIn())
