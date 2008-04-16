#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

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
