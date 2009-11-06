#!/usr/bin/python
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""Mock ScanScripts for testing.

It mocks ScanScripts to return a predefined answer.
Usage: to use it, you will need to call SetConfig to set a pre-cooked answer.
Then inject this mock. When BaseScan is called it will simple return the
pre-cooked answer for testing purpose no matter what name is given.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

from lib import baserunner
from lib import scanscripts

ScanScriptsError = scanscripts.ScanScriptsError
TestNotFoundError = scanscripts.TestNotFoundError


class MockScanScripts(scanscripts.ScanScripts):
  """Mocks ScanScripts.

  Actually here it intercepts BaseScan request and return a pre-cooked list of
  tests.
  """

  def __init__(self):
    self.config = []
    self.setup = []
    self.teardown = []

  def BaseScan(self, name):
    """Mock BaseScan method.

    Return pre-set test lists other than do an actual scan.

    Args:
      name: <string> the name of the test.

    Returns:
      list of test cases.

    Raises:
      TestNotFoundError: if asked name doesn't exist in the pre-cooked lists.
    """
    if name in baserunner.SETUP_SUITE:
      if not self.setup:
        raise TestNotFoundError
      return self.setup
    elif name in baserunner.TEARDOWN_SUITE:
      if not self.teardown:
        raise TestNotFoundError
      return self.teardown
    else:
      if not self.config:
        raise TestNotFoundError
      return self.config

  def SetConfig(self, con, test='testcase'):
    """Saves the config info."""
    if test == 'testcase':
      for one in con:
        self.config.append(one)
    elif test == 'setup':
      for one in con:
        self.setup.append(one)
    elif test == 'teardown':
      for one in con:
        self.teardown.append(one)

  def CleanConfig(self):
    """Resets everything."""
    self.config = []
    self.setup = []
    self.teardown = []
