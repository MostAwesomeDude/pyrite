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

def s2d(string):
	'''Convenience function. Convert a string to a dictionary.'''
	templ = string.split("&")
	dic = dict()
	for pair in templ:
		(key, val) = pair.split("=")
		dic[key] = val
	return dic

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

def ping(outbound, inbound):
	'''Ping the database. We do not need a login for this.
	Returns True on success, otherwise False.'''
	# sock.sendto("PING", (server, port))
	# data = sock.recv(256)
	outbound.put("PING")
	data = inbound.get()
	(code, data) = data.split(" ",1)
	if code == "300":
		# PONG!
		return True
	else:
		# No pong? Doesn't matter why, just that it failed...
		return False

def login(outbound, inbound, user, passwd):
	'''Start a session. Returns session id on success, None on failure.'''
	command = "AUTH user=" + user.lower() + "&pass=" + passwd + "&protover=3&client=openanidb&clientver=1"
	outbound.put(command)
	data = inbound.get()
	(code, data) = data.split(" ", 1)
	if code == "200":
		# Logged in, yay.
		(retval, trash) = data.split(" ", 1)
		return retval
	elif code == "500":
		# Failed...
		return False
	elif code == "201":
		# New version available; FIXME: make this apparent in the retval
		(retval, trash) = data.split(" ", 1)
		return retval
	else:
		# Some other code. Not important right now
		# FIXME: implement all other codes!
		return None

def logout(outbound, inbound, session):
	'''End a session.'''
	if session == None:
		# Why is sanity checking here? Whatever...
		return False
	command = "LOGOUT s=" + session
	outbound.put(command)
	data = inbound.get()
	(code, data) = data.split(" ", 1)
	if code == "203":
		# Logged out successfully.
		return True
	elif code == "403":
		# Well, the session wasn't good, but the end result is the same, I guess.
		return True
	else:
		return False

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
	# Since ID is more accurate than name, it gets done first...
	if aid != 0:
		command = "ANIME aid=" + str(aid) + "&s=" + session
	else:
		command = "ANIME aname=" + aname + "&s=" + session
	''' I'm gonna rant for a second here.
	So, the MTU (and max. datagram size) for AniDB is 1400 bytes. This is
	absolutely insane. Why? Well, first off, the modern stack implementation
	can send a whole datagram at sizes of 4096 bytes minimum. This means
	that even if fragmentation occurs, the actual hardware can still buffer
	this larger packet without problems. Normally, I wouldn't care, but they
	would rather truncate data than bother trusting IP fragmentation. Sheesh.'''
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
	# Since ID is more accurate than name, it gets done first...
	if eid != 0:
		command = "EPISODE eid=" + str(eid) + "&s=" + session
	else:
		# Sanest way to pass epno
		command = "EPISODE aid=" + str(aid[0]) + "&epno=" + str(aid[1]).lstrip("0") + "&s=" + session
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
	if fid != 0:
		command = "FILE fid=" + str(fid) + "&s=" + session
	else:
		command = "FILE size=" + str(file[1]) + "&ed2k=" + file[0].lower() + "&s=" + session
		print command
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

def encoding(outbound, inbound, session):
	'''Sets session encoding. There is no reason to change it away from
	UTF8 Unicode, so don't touch!'''
	command = "ENCODING name=UTF8&s=" + session
	outbound.put(command)
	code = inbound.get()[0:3]
	if code == "219":
		return True
	else:
		return False