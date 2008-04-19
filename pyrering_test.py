#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: mwu@google.com (Mingyu Wu)


"""Unittest for pyrering module."""

__author__ = 'mwu@google.com (Mingyu Wu)'

import unittest
import pyrering


class PyreRingTest(unittest.TestCase):
  """Unit test for pyrering.py module."""

  def testSimpleCall(self):
    """A simple run of pyrering with no arguments.
    
    This will do an actual run of PyreRing with no arguments. The Code should
    exit peacefully with nothing been run.
    """
    pyrering.main(['unitest'])

if __name__ == '__main__':
  unittest.main()
