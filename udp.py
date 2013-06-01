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

'''Based upon the UDP API definition, located at
http://wiki.anidb.info/w/UDP_API_Definition'''

'''Note: This implementation handles each API call on a by-call basis.
This means more code, but it also means that each different command can handle
all of the return codes itself.'''

import socket
import time
import threading

import db

server = "api.anidb.info"
port = 9000


def unpack(s):
    """
    Unpack a str into a dict.
    """

    return dict(pair.split("=") for pair in s.split("&"))


def udpsock():
    '''Return a new UDP socket. Be careful with this -- we can't have
    too many sockets floating around!'''
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class udpthread(threading.Thread):
    '''Thread that runs a UDP request queue. Handles timeouts, MTU, and
    flood control automatically. Not bad for datagrams, huh?'''
    def __init__(self, i, o, status):
        threading.Thread.__init__(self)
        # In...
        self.i = i
        # And out...
        self.o = o
        # Statusbar
        self.status = status
        self.sock = udpsock()
        self.sock.settimeout(20)
    def run(self):
        while True:
            if not self.i.empty():
                self.status.SetStatusText("Queued: " + str(self.i.qsize()), 1)
                # This thread's in is the system's out.
                outbound = self.i.get(False)
                print "UDP: Sending", outbound
                self.sock.sendto(outbound, (server, port))
                try:
                    inbound = self.sock.recv(1400)
                    print "UDP: Recieved", inbound
                    self.o.put(inbound.decode("utf8"))
                except socket.timeout:
                    print "UDP: Timeout!"
                    self.o.put(None)
            else:
                self.status.SetStatusText("Idle...", 1)
            time.sleep(2)

def unamp(str):
    '''Unescapes a string.'''
    return str.replace("\n"," ").strip()

def unicodify(l):
    '''Iterates through a list, and turns each UTF8 string into Unicode.'''
    for i in range(len(l)):
        if type(l[i]) == str:
            l[i] = l[i].decode("utf8")
    return l

def anime(outbound, inbound, session, aid=0, aname=None, invalidatecache=False):
    '''Retrieves data for an anime. Does some caching.'''
    if aid == 0 and aname == None:
        # Failed value
        return False
    # Wipe cache first?
    if invalidatecache:
        db.rmaid(aid)
    # Check the cache for this anime.
    cache = db.findaid(aid,aname)
    if cache != None:
        # Cache hit!
        cache.append(u"Yes")
        return cache
    elif session == None:
        # If session is empty, then searching the cache is the limit...
        return None

    data = {"s": session}
    # Since ID is more accurate than name, it is preferred.
    if aid != 0:
        data["aid"] = str(aid)
    else:
        data["aname"] = aname

    payload = pack(data)
    command = "ANIME " + payload

    # I'm gonna rant for a second here.
    # So, the MTU (and max. datagram size) for AniDB is 1400 bytes. This is
    # absolutely insane. Why? Well, first off, the modern stack implementation
    # can send a whole datagram at sizes of 4096 bytes minimum. This means
    # that even if fragmentation occurs, the actual hardware can still buffer
    # this larger packet without problems. Normally, I wouldn't care, but they
    # would rather truncate data than bother trusting IP fragmentation.
    # Sheesh.
    outbound.put(command)
    data = inbound.get()
    data = unamp(data)
    (code, trash, data) = data.split(" ",2)
    if code == "230":
        datal = data.split("|")
        # Cache it!
        db.addaid(datal)
        datal.append("No")
        # return unicodify(datal)
        return datal
    elif code == "330":
        # No such anime.
        return None
    else:
        # FIXME: unsupported return code.
        return None

def episode(outbound, inbound, session, eid=0, aid=(), invalidatecache=False):
    '''Gets an episode. Supports the caching mechanism.'''
    if eid == 0 and aid == ():
        # Failed value
        return False
    # Wipe cache first?
    if invalidatecache:
        db.rmeid(eid)
    # Check the cache for this anime.
    cache = db.findeid(eid,aid)
    if cache != None:
        # Cache hit!
        cache.append(u"Yes")
        return cache
    elif session == None:
        # If session is empty, then searching the cache is the limit...
        return None

    data = {"s": session}
    # Since ID is more accurate than name, it is preferred.
    if eid != 0:
        data["eid"] = eid
    else:
        data["aid"] = str(aid[0])
        data["epno"] = str(aid[1]).lstrip("0")

    payload = pack(data)
    command = "EPISODE " + payload

    outbound.put(command)
    data = inbound.get()
    data = unamp(data)
    (code, trash, data) = data.split(" ",2)
    if code == "240":
        datal = data.split("|")
        # Cache it!
        db.addeid(datal)
        datal.append("No")
        return datal
    elif code == "340":
        # No such episode.
        return None
    else:
        # FIXME: unsupported return code.
        return None

def file(outbound, inbound, session, fid=0, file=(), invalidatecache=False):
    '''Issues a FILE command.'''
    if fid == 0 and file == ():
        # WTF?
        return False
    # Wipe cache first?
    if invalidatecache:
        db.rmfid(fid)
    # Check the cache for this anime.
    cache = db.findfid(fid,file)
    if cache != None:
        # Cache hit!
        cache.append(u"Yes")
        return cache
    elif session == None:
        # If session is empty, then searching the cache is the limit...
        return None

    data = {"s": session}
    if fid != 0:
        data["fid"] = fid
    else:
        data["ed2k"] = str(file[0].lower())
        data["size"] = str(file[1])

    payload = pack(data)
    command = "FILE " + payload

    outbound.put(command)
    data = inbound.get()
    data = unamp(data)
    (code, trash, data) = data.split(" ",2)
    if code == "220":
        datal = data.split("|")
        # Cache it!
        db.addfid(datal)
        datal.append("No")
        return datal
    elif code == "320":
        # No such file.
        return None
    else:
        # FIXME: unsupported return code.
        return None
