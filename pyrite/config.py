#!/usr/bin/env python
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

import ConfigParser

class config:
    '''This class wraps ConfigParser without inheriting from it. The
    point is to have a semi-stateful and simple config class that keeps
    openanidb.py from worrying about silly things like config file
    locations or value conversion.'''
    def __init__(self):
        # Config file(s)
        self.files = ["openanidb.ini"]
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read(self.files)
        if not self.parser.has_section("OpenAniDB"):
            self.parser.add_section("OpenAniDB")
    
    def reload(self):
        self.parser.read(self.files)
        if not self.parser.has_section("OpenAniDB"):
            self.parser.add_section("OpenAniDB")
    
    def save(self):
        self.parser.write(file("openanidb.ini", "w"))
    
    def get(self, key):
        '''Gets key's value, or None if not set.'''
        try:
            retval = self.parser.get("OpenAniDB", key)
            if retval == "True":
                return True
            elif retval == "False":
                return False
            else:
                return retval
        except ConfigParser.NoOptionError:
            return None
    
    def set(self, key, value):
        '''Sets key to value.'''
        self.parser.set("OpenAniDB", key, str(value))
