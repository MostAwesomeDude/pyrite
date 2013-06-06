#!/usr/bin/env python
############################################################################
#    Copyright (C) 2007 by Corbin Simpson                                  #
#    MostAwesomeDude@gmail.com                                             #
#                                                                          #
#    This program is free software; you can redistribute it and/or modify  #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation; either version 2 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program; if not, write to the                         #
#    Free Software Foundation, Inc.,                                       #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
############################################################################

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