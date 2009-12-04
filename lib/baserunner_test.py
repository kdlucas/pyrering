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
#
# Author: mwu@google.com (Mingyu Wu)

"""Unittest for baserunner module."""

__author__ = 'mwu@google.com (Mingyu Wu)'

import os
import shutil
import sys
import tempfile
import time
import unittest


from lib import baserunner
from lib import filesystemhandlerextend
from lib import mock_emailmessage
from lib import mock_reporter
from lib import mock_scanscripts
from lib import pyreringconfig
from lib import pyreringutil

global_settings = pyreringconfig.GlobalPyreRingConfig.settings


class BaseRunnerTest(unittest.TestCase):
  """Unit test cases for BaseRunner class."""

  def setUp(self):
    # I should config global_settings here instead of read it from file system.
    self.tempdir = tempfile.mkdtemp()
    root_dir = os.path.abspath(os.path.join(os.path.split(sys.argv[0])[0],
                                            '../'))
    global_settings.update(
        {'report_dir': os.path.join(self.tempdir, 'report'),
         'email_recipients': os.getenv('LOGNAME'),
         'host_name': 'test.host',
         'log_file': 'pyrering.log',
         'file_errors': False,
         'project_name': 'pyrering_unittest',
         'root_dir': root_dir,
         'sendmail': False,
         'runner': 'baserunner',
         'source_dir': os.path.join(root_dir, 'test'),
         'tester': os.getenv('LOGNAME'),
         'FATAL_STRING': 'Fatal:',
         'header_file': 'header_info.txt',
         'time': time.strftime('%Y%m%d%H%M'),
         'skip_setup': False,
        })
    # get a default config and mocks
    self.one_config = pyreringutil.PRConfigParser().Default()
    self.scanner = mock_scanscripts.MockScanScripts()
    self.emailmessage = mock_emailmessage.MockEmailMessage()
    self.reporter = mock_reporter.MockTxtReporter()

    self.runner = baserunner.BaseRunner(
        name='test',
        scanner=self.scanner,
        email_message=self.emailmessage,
        filesystem=filesystemhandlerextend.FileSystemHandlerExtend(),
        reporter=self.reporter)
    self.runner.Prepare()
    if not os.path.isdir(global_settings['report_dir']):
      os.makedirs(global_settings['report_dir'])
    # I don't want the unit test to mess with the original log file.
    global_settings['log_file'] += '.unittest'

  def tearDown(self):
    self.runner.CleanUp()
    self.runner = ''
    pyreringconfig.Reset()
    self.scanner.CleanConfig()
    shutil.rmtree(self.tempdir)

  def testFindHeaderInfoFile(self):
    global_settings['header_file'] = os.path.join(self.tempdir, 'header.txt')
    fh = open(global_settings['header_file'], 'w')
    fh.write('test info')
    fh.close()
    self.one_config['TEST_SCRIPT'] = 'echo 1'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testFindHeaderInfoFile'], False)
    self.assertEqual(self.reporter.header, 'test info')
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)

  # Positive Test Cases:
  def testOneCommand(self):
    """A simple sleep command takes some time to finish."""
    # prepare the test script here
    self.one_config['TEST_SCRIPT'] = 'sleep 3'
    # set the mock scanscript to return this thing.
    self.scanner.SetConfig([self.one_config])

    # now run the test and return should be expected.
    result = self.runner.Run(['testOneCommand'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)

  def testEchoCommand(self):
    """A simple command has output on stdout."""
    self.one_config['TEST_SCRIPT'] = 'echo testEchoCommand'
    self.scanner.SetConfig([self.one_config])

    result = self.runner.Run(['testEchoCommand'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)
    #TODO(mwu): need to check the log file has this hello line

  def testEchoToSTDERRCommand(self):
    """A simple command has output redirect to stderr."""
    self.one_config['TEST_SCRIPT'] = 'echo testEchoToSTDERRCommand >&2'
    self.scanner.SetConfig([self.one_config])

    result = self.runner.Run(['testEchoSTDERRCommand'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)
    #TODO(mwu): need to check the log file has this hello line

  def testRunScript(self):
    """A real script to run."""
    self.one_config['TEST_SCRIPT'] = os.path.join(global_settings['root_dir'],
                                                  'test/test1_echo.sh')
    self.scanner.SetConfig([self.one_config])

    result = self.runner.Run(['testRunScript'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)
    #TODO(mwu): need to check the log file has the echo output

  def testRunScripts(self):
    """2 scripts to be run."""
    self.one_config['TEST_SCRIPT'] = 'echo testRunScripts1'
    config2 = pyreringutil.PRConfigParser().Default()
    config2['TEST_SCRIPT'] = 'echo testRunScripts2'
    self.scanner.SetConfig([self.one_config, config2])

    result = self.runner.Run(['testRunScripts'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 2)
    # TODO(mwu): verify both scripts run fine

  def testEmailSend(self):
    """Test Email should be send."""
    self.one_config['TEST_SCRIPT'] = 'echo send_email_test;exit 1'
    self.scanner.SetConfig([self.one_config])

    try:
      self.runner.Run(['testEmailSend'], True)
    except self.emailmessage.EmailCalledError:
      self.assertTrue(True)
    else:
      self.fail(msg='Send email was not called')

  def testEmailNotSendIfTestPass(self):
    """Test email should not go if all tests pass."""
    self.one_config['TEST_SCRIPT'] = 'echo send_email_test;exit 0'
    self.scanner.SetConfig([self.one_config])

    try:
      self.runner.Run(['testEmailSend'], True)
    except self.emailmessage.EmailCalledError:
      self.fail()

  # Negative Test Cases
  def testTimeoutCommand(self):
    """A command times out."""
    self.one_config['TEST_SCRIPT'] = 'echo timeouttest; sleep 8'
    self.one_config['TIMEOUT'] = 2
    self.scanner.SetConfig([self.one_config])

    result = self.runner.Run(['testTimeoutCommand'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.timeout, 1)

  def testNonExistCommand(self):
    """Test a wrong system command."""
    self.one_config['TEST_SCRIPT'] = 'nonexist_command'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testNonExistCommand'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 1)

  def testNonExistScript(self):
    """Test a nonexist script."""
    self.one_config['TEST_SCRIPT'] = '/tmp/nonexist_script.sh'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testNonExistScript'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 1)

  def testPermissionDenied(self):
    """Test something without permission."""
    self.one_config['TEST_SCRIPT'] = 'touch /pyrering.txt'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testPermissionDenied'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 1)

  def testCatchWarningMessage(self):
    """Test a command has warning output."""
    self.one_config['TEST_SCRIPT'] = 'echo warn message'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testCatchWarningMessage'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)

  def testCatchFatalMessage(self):
    """Test a command has fatal error message even exit code still 0."""
    self.one_config['TEST_SCRIPT'] = 'echo Fatal:;echo anotherline'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testCatchFatalMessage'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 1)

  def testOutputLargeMessage(self):
    """Test a test can have large screen output.

    As default the stdout only has a 4k buffer limit, so the code should clean
    up the buffer while running the test, otherwise the writing to buffer will
    be blocked when the buffer is full.
    """
    self.one_config['TEST_SCRIPT'] = os.path.join(global_settings['root_dir'],
                                                  'test/outputlargetxt.py')
    self.one_config['TIMEOUT'] = 4
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testLargeOutput'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.passed, 1)

  def testExitWithError(self):
    """Test a test have an error exit, which is not a failure."""
    self.one_config['TEST_SCRIPT'] = 'exit 255'
    self.scanner.SetConfig([self.one_config])
    result = self.runner.Run(['testExitWithError'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 0)
    self.assertEqual(self.runner.error, 1)

  def testSetupTestPassed(self):
    """Test a setup test case passes."""
    self.one_config['TEST_SCRIPT'] = 'exit 0'
    self.scanner.SetConfig([self.one_config])
    config2 = pyreringutil.PRConfigParser().Default()
    config2['TEST_SCRIPT'] = 'exit 0'
    self.scanner.SetConfig([config2], 'setup')
    result = self.runner.Run(['testSetupTestFailed'], False)
    self.assertEqual(result, 0)
    self.assertEqual(self.runner.failed, 0)

  def testSetupTestFailed(self):
    """Test a setup test case failed, the test should exit at once."""
    self.one_config['TEST_SCRIPT'] = 'exit 0'
    self.scanner.SetConfig([self.one_config])
    config2 = pyreringutil.PRConfigParser().Default()
    config2['TEST_SCRIPT'] = 'exit 1'
    self.scanner.SetConfig([config2], 'setup')
    result = self.runner.Run(['testSetupTestFailed'], False)
    self.assertEqual(result, 1)
    self.assertEqual(self.runner.failed, 1)

  def testTearDownFailed(self):
    """Test a teardown test case failed, the test still reports."""
    self.one_config['TEST_SCRIPT'] = 'exit 0'
    self.scanner.SetConfig([self.one_config])
    config2 = pyreringutil.PRConfigParser().Default()
    config2['TEST_SCRIPT'] = 'exit 1'
    self.scanner.SetConfig([config2], 'teardown')
    result = self.runner.Run(['testTearDownTestFailed'], False)
    self.assertEqual(result, 4)
    self.assertEqual(self.runner.failed, 4)


if __name__ == '__main__':
  unittest.main()
