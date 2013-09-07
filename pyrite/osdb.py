from struct import Struct

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

    i += handle.tell()

    return i % m
