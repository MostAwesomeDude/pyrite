from unittest import TestCase

from pyrite.anidb import pack


class TestPack(TestCase):

    def test_single(self):
        i = {"key": "value"}
        o = "key=value"
        self.assertEqual(pack(i), o)
