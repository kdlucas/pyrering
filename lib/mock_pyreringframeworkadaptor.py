#!/usr/bin/python
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
