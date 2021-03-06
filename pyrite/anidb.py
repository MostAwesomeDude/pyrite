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
from collections import deque
from datetime import timedelta

from twisted.internet.defer import Deferred, DeferredLock, fail
from twisted.internet.protocol import DatagramProtocol
from twisted.python import log

from pyrite.errors import FileNotFound


class Trickling(object):

    def __init__(self, reactor, transport):
        self.reactor = reactor
        self.transport = transport

        self.timestamp = reactor.seconds()

    def write(self, packet):
        log.msg("> %r" % packet)

        current = self.reactor.seconds()
        diff = current - self.timestamp

        if diff >= 4:
            # We're good to send right now.
            self.transport.write(packet)
            self.timestamp = current
        else:
            # We'll send in the future, when it's safe.
            target = 4 - diff
            self.reactor.callLater(target, self.transport.write, packet)
            self.timestamp = current + target

        retry = self.reactor.callLater(self.timestamp + 10, self.write,
                                       packet)
        return retry


def pack(d):
    """
    Pack a dict into a str.
    """

    return "&".join("%s=%s" % t for t in d.items())


def request(s, d=None):
    """
    Make a request from a request type and dict of arguments.
    """

    if d:
        return "%s %s\n" % (s, pack(d))
    return s


def postprocess(packet):
    code, data = packet.split(" ", 1)
    code = int(code)
    data = data.strip()
    return code, data


def standard_errors(t):
    code, data = t

    if code == 555:
        # BANNED
        s = "Banned (API server is butthurt; wait an hour)"
        raise Exception(s)

    return code, data

class AniDBProtocol(DatagramProtocol):
    """
    A protocol for communicating with AniDB.
    """

    retry = None
    session = None
    timestamp = 0

    def __init__(self, reactor, address):
        self.reactor = reactor
        self.address = address

        self._ds = deque()
        self._lock = DeferredLock()

    def startProtocol(self):
        self.transport.connect(self.address, 9000)
        self.transport = Trickling(self.reactor, self.transport)

    def datagramReceived(self, packet, remote):
        log.msg("< %r" % packet)

        if self.retry:
            self.retry.cancel()
            self.retry = None

        d = self._ds.popleft()
        d.callback(postprocess(packet))

        # Lock--
        self._lock.release()

    def ds(self):
        d = Deferred()
        d.addCallback(standard_errors)

        self._ds.append(d)

        return d

    def write(self, packet):
        """
        Write a packet of data, eventually.
        """

        # Lock++
        d = self._lock.acquire()
        @d.addCallback
        def cb(lock):
            self.retry = self.transport.write(packet)

        return d

    def ping(self):
        payload = request("PING")
        self.write(payload)

        return self.ds()

    def login(self, username, password):
        data = {
            "user": username,
            "pass": password,
            "protover": 3,
            "client": "openanidb",
            "clientver": 2,
        }

        payload = request("AUTH", data)
        self.write(payload)

        d = self.ds()

        @d.addCallback
        def check(t):
            code, data = t

            if code == 200 or code == 201:
                # LOGIN ACCEPTED
                session, stuff = data.split(" ", 1)
                self.session = session

                log.msg("Logged in; session %s" % session)
            elif code == 500:
                # LOGIN FAILED
                raise Exception("Login failed")

            return self.session

        return d

    def logout(self):
        if not self.session:
            return fail("Already logged out.")

        payload = request("LOGOUT", {"s": self.session})
        self.write(payload)

        return self.ds()

    def encoding(self):
        data = {
            "s": self.session,
            "name": "UTF8",
        }
        payload = request("ENCODING", data)
        self.write(payload)

        d = self.ds()

        @d.addCallback
        def check(t):
            code, data = t

            if code == 219:
                # ENCODING CHANGED
                pass
            elif code == 519:
                # ENCODING NOT SUPPORTED
                raise Exception("UTF-8 encoding not supported!?")

            return "UTF8"

        return d

    def version(self):
        payload = request("VERSION")
        self.write(payload)

        d = self.ds()

        @d.addCallback
        def check(t):
            code, data = t

            if code == 998:
                # VERSION
                stuff, version = data.split("\n", 1)

                log.msg("Server version: %s" % version)
                return version
            else:
                raise Exception("Unexpected return code for version: %d (%s)"
                                % t)

        return d

    def uptime(self):
        if not self.session:
            return fail("Log in before checking uptime.")

        payload = request("UPTIME", {"s": self.session})
        self.write(payload)

        d = self.ds()

        @d.addCallback
        def check(t):
            code, data = t

            if code == 208:
                # UPTIME
                stuff, uptime = data.split("\n", 1)
                uptime = timedelta(milliseconds=int(uptime))

                log.msg("Server uptime: %s" % uptime)

                return uptime
            else:
                raise Exception("Unexpected return code for uptime: %d (%s)" %
                                t)

        return d

    def lookup(self, size, ed2k):
        data = {
            "ed2k": ed2k,
            "size": size,
            "amask": "c020c040",
            "fmask": "00c0010000",
            "s": self.session,
        }

        payload = request("FILE", data)
        self.write(payload)

        d = self.ds()

        @d.addCallback
        def check(t):
            code, data = t

            if code == 220:
                # FILE
                fragments = data.split("\n")[1].split("|")
                keys = [
                    "fid",
                    "size",
                    "ed2k",
                    "fext",
                    "eid_total",
                    "eid_highest",
                    "series",
                    "eid",
                    "title",
                    "group",
                ]
                d = dict(zip(keys, fragments))

                for k in ("eid", "eid_highest", "eid_total", "fid", "size"):
                    d[k] = int(d[k])

                return d
            elif code == 320:
                # NO SUCH FILE
                raise FileNotFound()

        return d


def make_protocol(reactor):
    d = reactor.resolve("api.anidb.info")

    @d.addCallback
    def cb(address):
        protocol = AniDBProtocol(reactor, address)
        reactor.listenUDP(0, protocol)
        return protocol

    return d
