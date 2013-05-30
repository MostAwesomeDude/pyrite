from unittest import TestCase

from pyrite import Munger
from udp import pack, unpack


class TestPack(TestCase):

    def test_single(self):
        i = {"key": "value"}
        o = "key=value"
        self.assertEqual(pack(i), o)


class TestUnpack(TestCase):

    def test_single(self):
        i = "key=value"
        o = {"key": "value"}
        self.assertEqual(unpack(i), o)


class TestTV(TestCase):

    def test_community(self):
        s = "Community.S04E03.HDTV.x264-LOL.mp4"
        name, ep, ext = Munger(s).tv()

        self.assertEqual(name, "Community")
        self.assertEqual(ep, (4, 3))
        self.assertEqual(ext, "mp4")

    def test_parks(self):
        s = "Parks.and.Recreation.S05E12.HDTV.x264-LOL.mp4"
        name, ep, ext = Munger(s).tv()

        self.assertEqual(name, "Parks and Recreation")
        self.assertEqual(ep, (5, 12))
        self.assertEqual(ext, "mp4")
