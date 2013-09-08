from unittest import TestCase

from zope.interface.verify import verifyObject

from pyrite.guru import IGuru, AniDBGuru, OSDBGuru


class TestInterfaces(TestCase):

    def test_verify_anidbguru(self):
        self.assertTrue(verifyObject(IGuru, AniDBGuru()))

    def test_verify_osdbguru(self):
        self.assertTrue(verifyObject(IGuru, OSDBGuru()))
