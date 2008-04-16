#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.

"""mock_reporter mocks reporter_test.py.

For testing purpose this module will mock the reporter_txt.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

from lib import reporter_txt


class MockTxtReporter(reporter_txt.TxtReporter):
  """Mock TxtReporter class for testing purpose."""

  def AttachHeader(self, msg, unused_length=10):
    """Mock AttachHeader method."""
    self.header = msg
