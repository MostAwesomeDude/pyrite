from struct import Struct

from twisted.web.xmlrpc import Proxy

from pyrite.errors import FileNotFound


def checksum(data):
    s = Struct("<Q")
    m = 2 ** 64
    i = 0

    for offset in range(0, len(data), s.size):
        i += s.unpack_from(data, offset=offset)[0]
        i %= m

    return i


def derphash(handle):
    """
    Calculate the unnamed custom hash of a file.

    The hash is the sum of the file size, the first 64 KiB, and the last 64
    KiB, modulo 2**64. It is only defined for files at least 64 KiB or larger.

    This function does not need a writeable handle.

    This function seeks; reseek the handle afterwards if necessary.
    """

    m = 2 ** 64

    handle.seek(0, 0)
    data = handle.read(64 * 1024)
    i = checksum(data)

    handle.seek(-64 * 1024, 2)
    data = handle.read(64 * 1024)
    i += checksum(data)

    size = handle.tell()
    i += size

    return "%016x" % (i % m)


API = "http://api.opensubtitles.org/xml-rpc"


def consider(data):
    """
    Determine whether the request should be considered an error even though
    data was retrieved.
    """

    status = data["status"]
    code = status.split()[0]

    if code != "200":
        raise Exception(status)

    print status, data["seconds"]

    del data["seconds"]
    del data["status"]

    return data


class OSDB(object):
    """
    A proxy to OpenSubtitles.
    """

    token = None

    def __init__(self):
        self.p = Proxy(API)

    def login(self, username, password):
        d = self.p.callRemote("LogIn", username, password, "und",
                              "OS Test User Agent")

        d.addCallback(consider)

        @d.addCallback
        def cb(data):
            print "Logged in!"
            self.token = data["token"]

        return d

    def logout(self):
        d = self.p.callRemote("LogOut", self.token)

        d.addCallback(consider)

        @d.addCallback
        def cb(data):
            print "Logged out!"
            self.token = None

        return d

    def search(self, derp):
        d = self.p.callRemote("CheckMovieHash2", self.token, [derp])

        d.addCallback(consider)

        @d.addCallback
        def cb(data):
            vs = data["data"].values()
            # We only want that first result. Since we asked for only one
            # search, we will get either zero or one results.
            if vs:
                return vs[0]
            else:
                raise FileNotFound()

        return d
