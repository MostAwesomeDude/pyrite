#!/usr/bin/env python
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

"""
An implementation of ED2K.
"""

from Crypto.Hash import MD4


def ed2k(handle):
    """
    ED2K is a rudimentary tree hash, with a depth of 1 and a leaf size of
    9,728,000 bytes. The hash is MD4, which is not natively available in
    Python, so I use PyCrypto's version instead.
    """

    buf = ''
    hashl = []
    while True:
        buf = handle.read(9728000)
        if buf == '':
            break
        hashl.append(MD4.new(buf).digest())
    hashed = MD4.new(''.join(hashl)).hexdigest()
    return hashed


def size_and_hash(filepath):
    size = filepath.getsize()
    handle = filepath.open("rb")
    hash = ed2k(handle)
    handle.close()
    return size, hash
