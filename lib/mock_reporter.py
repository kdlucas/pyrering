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
