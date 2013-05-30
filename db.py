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

'''This file provides APSW-driven database access through Sqlite. There are
a few things to know; read the comment below for details.'''

'''Right now, there is NO cache consistency code. I scrapped it all, after a
nice conversation with the devs. The current state of things is that I need
to come up with some new algorithms for optimizing and choosing cache repairs
and invalidations, so for now just be aware that the cache doesn't know about
what's good and what's not. I'm relying on udp.anime() and oaframe.gui_anime()
to be sane; this will change in the future.'''

'''LIDs (mylist IDs) are global, apparently. Thus, there is no longer code
here, and I need to come up with something else. *maniacal cough*'''

'''As tempting as it is, do not use BEGIN and COMMIT, since the time needed
to open the DB, scan it, and find an insertion point is nothing compared to
the two-second UDP delay; if populating the cache with a batch statement,
there will be plenty of time to update the DB while waiting in the next thread
for a reply from AniDB. The added complexity of transaction construction is
just too much.'''

import os.path

# import apsw
apsw = None

db = "anime.db"

if not os.path.exists(db):
    # Gotta recreate the database!
    regenaid()
    regeneid()
    regenfid()

def regenaid():
    '''Regenerates/flushes the anime table. Does NOT regenerate the
    entire database. Use with caution, since it takes a while to
    build up.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    try:
        cursor.execute("drop table anime")
    except apsw.SQLError:
        # This will happen; just ignore it.
        pass
    cursor.execute("vacuum")
    cursor.execute("create table anime(aid, eps, epcount, spcount, rating, votes, tmprating, tmpvotes, average, ratings, year, type, romaji, kanji, english, other, shorts, synonyms, cats)")
    handle.close()

def addaid(animel):
    '''Adds an anime to the cache.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    # Pass one: Turn int4 into int
    for i in range(10):
        animel[i] = int(animel[i])
    # Pass two: turn str into unicode
    for i in range(len(animel)):
        if type(animel[i]) == str:
            animel[i] = animel[i].strip().decode('utf8')
    cursor.execute("insert into anime values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", animel)
    handle.close()

def findaid(aid=0, aname=u''):
    '''Find an anime record in the cache.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    '''Lemme explain this line and the one after it, okay? This is for posterity.
    So, the list comprehension returns a list of tuples. We need to check to see
    whether or not we got a row back. The if: after this line tests for that. If
    we got no result, then we wasted an SQL statement; such is life. We search
    again, this time by aname.'''
    result = [row for row in cursor.execute("select * from anime where aid=? limit 1", (aid,))]
    if result != []:
        # Cache hit!
        handle.close()
        return list(result[0])
    else:
        # Miss; try again.
        result = [row for row in cursor.execute("select * from anime where romaji=? or kanji=? limit 1", (aname,aname))]
        # Finished; close the handle.
        handle.close()
        if result != []:
            # Cache hit!
            return list(result[0])
        else:
            # Miss. We're finished here.
            return None

def rmaid(aid=0):
    '''Remove a record from the anime cache.'''
    handle = apsw.Connection(db)
    handle.cursor().execute("delete from anime where aid=?", (aid,))
    handle.close()

def allanime(sort):
    '''Returns the aid and aname columns of the anime table.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    dictformat = ["aid", "eps", "epcount", "spcount", "rating", "votes", "tmprating", "tmpvotes", "average", "ratings", "year", "type", "romaji", "kanji", "english", "other", "shorts", "synonyms", "cats"]
    if sort == 0:
        result = [dict(zip(dictformat,row)) for row in cursor.execute("select * from anime order by aid asc")]
    elif sort == 1:
        result = [dict(zip(dictformat,row)) for row in cursor.execute("select * from anime order by romaji asc")]
    handle.close()
    return result

def regeneid():
    '''Regenerates/flushes the episodes table. You should only have to
    call this once, to set up the table. I almost feel like this
    shouldn't be its own function...'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    try:
        cursor.execute("drop table episodes")
    except apsw.SQLError:
        # This will happen; just ignore it.
        pass
    cursor.execute("vacuum")
    cursor.execute("create table episodes(eid, aid, length, rating, votes, epno, english, romaji, kanji)")
    handle.close()

def addeid(epl):
    '''Adds an episode to the cache.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    # Pass one: Turn int4 into int
    for i in range(5):
        epl[i] = int(epl[i])
    # Special case for epno (fuckin' epno...)
    try:
        epl[5] = int(epl[5])
    except ValueError:
        pass
    # Pass two: turn str into unicode
    for i in range(len(epl)):
        if type(epl[i]) == str:
            epl[i] = epl[i].strip().decode('utf8')
    cursor.execute("insert into episodes values(?,?,?,?,?,?,?,?,?)", epl)
    handle.close()

def findeid(eid=0, aid=()):
    '''Find an episode record in the cache.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    result = [row for row in cursor.execute("select * from episodes where eid=? limit 1", (eid,))]
    if result != []:
        # Cache hit!
        handle.close()
        return list(result[0])
    elif aid != ():
        # Miss; try again.
        result = [row for row in cursor.execute("select * from episodes where aid=? and epno=? limit 1", aid)]
        # Finished; close the handle.
        handle.close()
        if result != []:
            # Cache hit!
            return list(result[0])
        else:
            # Miss. We're finished here.
            return None
    else:
        handle.close()
        return None

def rmeid(eid=0):
    '''Remove a record from the anime cache.'''
    handle = apsw.Connection(db)
    handle.cursor().execute("delete from episodes where eid=?", (eid,))
    handle.close()

def alleps(sort):
    '''Returns the aid and aname columns of the episode table.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    dictformat = ["eid", "aid", "length", "rating", "votes", "epno", "english", "romaji", "kanji"]
    if sort == 0:
        result = [dict(zip(dictformat,row)) for row in cursor.execute("select * from episodes order by aid asc")]
    elif sort == 1:
        result = [dict(zip(dictformat,row)) for row in cursor.execute("select * from episodes order by romaji asc")]
    handle.close()
    return result

def regenfid():
    '''Regenerates/flushes the files table. You should only have to
    call this once, to set up the table.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    try:
        cursor.execute("drop table files")
    except apsw.SQLError:
        # This will happen; just ignore it.
        pass
    cursor.execute("vacuum")
    cursor.execute("create table files(fid, aid, eid, gid, state, size, ed2k, filename)")
    handle.close()

def addfid(fpl):
    '''Adds an episode to the cache.'''
    print "Entering addfid..."
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    # Pass one: Turn int4 into int
    for i in range(6):
        fpl[i] = int(fpl[i])
    # Pass two: turn str into unicode
    for i in range(len(fpl)):
        if type(fpl[i]) == str:
            fpl[i] = fpl[i].strip().decode('utf8')
    print fpl
    cursor.execute("insert into files values(?,?,?,?,?,?,?,?)", fpl)
    handle.close()

def findfid(fid=0, h=('',0)):
    '''Find a file record in the cache.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    result = [row for row in cursor.execute("select * from files where fid=? limit 1", (fid,))]
    if result != []:
        # Cache hit!
        handle.close()
        return list(result[0])
    else:
        # Miss; try again.
        result = [row for row in cursor.execute("select * from files where ed2k=? and size=? limit 1", h)]
        # Finished; close the handle.
        handle.close()
        if result != []:
            # Cache hit!
            return list(result[0])
        else:
            # Miss. We're finished here.
            return None


def rmfid(fid=0):
    '''Remove a record from the anime cache.'''
    handle = apsw.Connection(db)
    handle.cursor().execute("delete from files where fid=?", (fid,))
    handle.close()

def allfiles():
    '''Returns stuff from the files table.'''
    handle = apsw.Connection(db)
    cursor = handle.cursor()
    dictformat = ["fid", "aid", "eid", "gid", "state", "size", "ed2k", "filename"]
    result = [dict(zip(dictformat,row)) for row in cursor.execute("select * from files order by fid asc")]
    handle.close()
    return result
