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

"""Unittest for reporter_txt module."""

__author__ = 'mwu@google.com (Mingyu Wu)'

import os
import tempfile
import unittest

from lib import constants
from lib import reporter_txt

print os.environ

class TxtReporterTest(unittest.TestCase):
  def setUp(self):
    self.reporter = reporter_txt.TxtReporter('unitest')
    self.fh, self.file_name = tempfile.mkstemp(text=True)

  def tearDown(self):
    os.remove(self.file_name)

  def testPassOnReportFileName(self):
    """open a report file and write something."""
    self.reporter.SetReportFile(self.file_name)
    self.reporter.StartTest('unittest', 'host_name', 'tester', 'uid', 'uname')
    self.reporter.TestCaseReport('PassOnReportFile',
                                 constants.PASS,
                                 'pass test')
    self.reporter.TestCaseReport('PassOnReportFile',
                                 constants.FAIL,
                                 'fail test')
    self.reporter.TestCaseReport('PassOnReportFile',
                                 constants.TIMEOUT,
                                 'timeout test')
    self.reporter.TestCaseReport('PassOnReportFile',
                                 constants.NOTRUN,
                                 'not run test')
    self.reporter.TestCaseReport('PassOnReportFile',
                                 constants.ERROR,
                                 'error test')
    self.reporter.SuiteReport('PassOnReportFile',
                              constants.PASS,
                              'suite line')
    self.reporter.EndTest()
    self.assertEqual(self.reporter.passed, 1)
    self.assertEqual(self.reporter.failed, 1)
    self.assertEqual(self.reporter.timeout, 1)
    self.assertEqual(self.reporter.notrun, 1)
    self.assertEqual(self.reporter.unknown, 0)
    
    if os.path.isfile(self.file_name) and os.path.getsize(self.file_name) > 0:
      self.assertTrue(1)
    else:
      self.fail('report file is not created or size is 0')

  def testReportFileWriteOutAfterEachSuiteReportReport(self):
    """Report write out after each TestCaseReport call."""
    self.reporter.SetReportFile(self.file_name)
    self.reporter.SuiteReport('PassOnReportFile',
                              constants.PASS,
                              'suite line')
    self.assertTrue(os.path.isfile(self.file_name) and
                    os.path.getsize(self.file_name) > 0)

  def testReportFileWriteOutAfterEachTestCaseReport(self):
    self.reporter.SetReportFile(self.file_name)
    self.reporter.TestCaseReport('PassOneReportFile',
                                 constants.PASS,
                                 'pass test')
    self.assertTrue(os.path.isfile(self.file_name) and
                    os.path.getsize(self.file_name) > 0)

  def testReportFileWriteOutAfterStartTest(self):
    self.reporter.SetReportFile(self.file_name)
    self.reporter.StartTest('unitest', 'host_name', 'tester', 'uid', 'uname')
    self.assertTrue(os.path.isfile(self.file_name) and
                    os.path.getsize(self.file_name) > 0)

  def testReportFileWriteOutAfterEndTest(self):
    self.reporter.SetReportFile(self.file_name)
    self.reporter.EndTest()
    self.assertTrue(os.path.isfile(self.file_name) and
                    os.path.getsize(self.file_name) > 0)


if __name__ == '__main__':
  unittest.main()
