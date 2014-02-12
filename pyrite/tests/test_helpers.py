from unittest import TestCase

from pyrite.helpers import remap_keys


class TestRemapKeys(TestCase):

    def test_remap_single(self):
        i = {"single": "key"}
        e = {"only": "key"}
        m = {"single": "only"}
        o = remap_keys(m, i)
        self.assertEqual(e, o)

    def test_remap_several(self):
        i = {"first": "key", "second": "keys"}
        e = {"one": "key", "two": "keys"}
        m = {"first": "one", "second": "two"}
        o = remap_keys(m, i)
        self.assertEqual(e, o)
