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
from unittest import TestCase

from pyrite.munger import Munger


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
