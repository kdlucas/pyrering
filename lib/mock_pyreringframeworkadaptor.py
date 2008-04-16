#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.

"""One-line documentation for mock_PyreRingFrameworkAdaptor module.

A detailed description of mock_PyreRingFrameworkAdaptor.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

from lib import pyreringutil


class MockPyreRingFrameworkAdaptor(pyreringutil.PyreRingFrameworkAdaptor):
  """Mock for PyreRingFrameworkAdaptor."""

  def __init__(self):
    self.name = 'mock_pyrering_framewor_adaptor'
    self.result = 0

  def Prepare(self):
    pass

  def CleanUp(self):
    pass

  def Run(self, suite_list, email_flag):
    return self.result 

  def GetFrameworkName(self):
    return self.name

  def CheckFramework(self):
    return True

  def SetResult(self, result):
    self.result = result
