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
