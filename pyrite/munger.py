import os.path
import sys

from parsley import makeGrammar

g = """
boundary = " - " | '.' -> " - "

epSE = 'S' digit{2}:s 'E' digit{2}:e -> (int("".join(s)), int("".join(e)))
epX = digit{1,2}:s ('X' | 'x') digit{1,2}:e
   -> (int("".join(s)), int("".join(e)))
ep = (epSE | epX):ep boundary -> ep

upper = anything:x ?(x == x.upper())
hdtv = "HDTV"
x264 = "x264-" (~boundary upper)+
trash = (hdtv | x264) boundary

eof = ~anything
extension = anything{3,4}:ext eof -> "".join(ext)

piece = letter+:ps boundary -> "".join(ps)
name = (~ep piece)+:ps -> " ".join(ps)
tv = name:n ep:e trash* extension:ext -> (n, e, ext)
"""

Munger = makeGrammar(g, {})

def makeX(info):
    name, ep, ext = info
    season, ep = ep
    return "%s - %dx%02d.%s" % (name, season, ep, ext)

def main():
    argv = sys.argv[2:]
    for name in argv:
        folder, filename = os.path.split(name)
        munged = makeX(Munger(filename).tv())
        print "Old:", filename, "New:", munged

if __name__ == "__main__":
    main()
