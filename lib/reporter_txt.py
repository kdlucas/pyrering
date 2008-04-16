#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""The interface and txt implementation classes to do pyrering reports.

This module has an Reporter interface which defines the basic API for PyreRing
report.
Another class TxtReporter is the implementation of the interface. It is ready
to be used to generate a txt report with a fixed format. User can extend from
either the interface or the TxtReporter to generate the report format whatever
they like.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import logging
import time
from lib import common_util
from lib import constants

logger = logging.getLogger('PyreRing')
DEBUG = common_util.DebugLog

HEAD = 1
SUMMARY = 2
PRE_BODY = 3
BODY = 4
EXTRA = 5
APPEND = 6
OVERWRITE = 7

TRUNCATE_MESSAGE = '''
...message truncated. Check the bottom for the full message.
'''


class Error(Exception):
  """Base reporter Exception."""
  pass


class ReporterError(Error):
  """General reporter exception."""
  pass


class Reporter(object):
  """The abstract base class for reporter."""

  def StartTest(self,
                unused_test_name,
                unused_host_name,
                unused_tester,
                unused_uid,
                unused_uname):
    """Called before the real test starts.

    Args:
      unused_test_name: the name of the test, normally should be just a list of
      the tests.
      unused_host_name: the machine runs the test.
      unused_tester: the user executes the test.
      unused_uid: the uid of the tester.
      unused_uname: the uname string of the machine.

    Returns:
      None.
    """
    raise NotImplementedError('Prepare to start a test')

  def EndTest(self):
    """Called after all test completed to wrap up report."""
    raise NotImplementedError('Finish up the test')

  def SuiteReport(self, unused_name, unused_result, unused_msg):
    """Report one suite result.

    Args:
      unused_name: the suite's name
      unused_result: the test result string 'PASS/FAIL'
      unused_msg: extra message to append

    Returns:
      None.
    """
    raise NotImplementedError('Report a suite result')

  def TestCaseReport(self, unused_name, unused_result, unused_msg):
    """Report one test result.

    Args:
      unused_name: the test case name
      unused_result: the result string 'PASS/FAIL/TIMEOUT'
      unused_msg: extra message to append

    Returns:
      None.
    """
    raise NotImplementedError('Report a test case result', msg='')

  def ExtraMessage(self, unused_msg):
    """Extra message needed to append to the report.

    Args:
      unused_msg: a string to append at the end of the report.

    Returns:
      None.
    """
    raise NotImplementedError('Attach extra message at the end of the test')

  def GetReportFile(self):
    """Get the report file name."""
    raise NotImplementedError('Return a file for the test result')

  def SetReportFile(self, unused_file_name):
    """Set the report file."""
    raise NotImplementedError('Set the report file')


class TxtReporter(Reporter):
  """A txt reporter reports test in txt format."""

  def __init__(self, project_name=''):
    """init the test reporter with a project name."""
    super(TxtReporter, self).__init__()
    logger.debug('enter TxtReporter.__init__')
    self.project_name = project_name
    self.report_file = ''
    self.report_pipe = ''

    self.start_time = ''
    self.end_time = 'NOT END YET'

    self.testresults = []
    self.suiteresults = []
    self.passed = 0
    self.failed = 0
    self.timeout = 0
    self.notrun = 0
    self.error = 0
    self.unknown = 0
    self.extra_message = '\nExtra Notes:\n'

    self.header = 'HEADER:\n'
    self.summary = 'SUMMARY:\n'
    self.body = 'BODY:\n'
    self.extra = 'EXTRA:\n'
    self.pre_body = 'PRE_BODY:\n'

    logger.debug('exit TxtReporter.__init__')

  def _WriteToRecord(self, location, msg, mode=APPEND):
    """Save info to record strings.

    This method will store the msg into a string for the test report.

    Args:
      location: one of the constants, HEAD, SUMMARY, BODY, EXTRA.
      msg: a string message.
      mode: one of the constants, APPEND, OVERWRITE.

    Returns:
      None.

    Raises:
      ReporterError: if the location or mode fall out of the expected values.
    """
    if location not in [HEAD, SUMMARY, PRE_BODY, BODY, EXTRA]:
      raise ReporterError('Unknown location: %d' % location)
    if mode not in [APPEND, OVERWRITE]:
      raise ReporterError('Unknown mode: %d' % mode)

    if location == HEAD and mode == APPEND:
      self.header = '%s%s\n' % (self.header, msg)
    elif location == HEAD and mode == OVERWRITE:
      self.header = 'HEADER:\n%s\n' % msg
    elif location == SUMMARY and mode == APPEND:
      self.summary = '%s%s\n' % (self.summary, msg)
    elif location == SUMMARY and mode == OVERWRITE:
      self.summary = 'SUMMARY:\n%s\n' % msg
    elif location == PRE_BODY and mode == APPEND:
      self.pre_body = '%s%s\n' % (self.pre_body, msg)
    elif location == PRE_BODY and mode == OVERWRITE:
      self.pre_body = 'PRE_BODY:\n%s\n' % msg
    elif location == BODY and mode == APPEND:
      self.body = '%s%s\n' % (self.body, msg)
    elif location == BODY and mode == OVERWRITE:
      self.body = 'BODY:\n%s\n' % msg
    elif location == EXTRA and mode == APPEND:
      self.extra = '%s%s\n' % (self.extra, msg)
    elif location == EXTRA and mode == OVERWRITE:
      self.extra = 'EXTRA:\n%s\n' % msg
  
  @DEBUG
  def TestCaseReport(self, name, result, msg=''):
    """Report one test case result.

    This method should be called every time a test is finished. It will log the
    result to the report body part.

    Args:
      name: the testcase name
      result: the result string 'PASS/FAIL/TIMEOUT/ERROR'
      msg: any extra messsage needed to append to the end of this test case.

    Returns:
      None.
    """
    self._WriteToRecord(BODY, 'TESTCASE: %s     %s' % (name, result))
    if msg:
      self._WriteToRecord(BODY, '    %s' % msg)
    # Collect none passed test in PRE_BODY too.
    if result != constants.PASS:
      self._WriteToRecord(PRE_BODY, 'TESTCASE: %s     %s' % (name, result))

    if result == constants.TIMEOUT:
      self.timeout += 1
    elif result == constants.FAIL:
      self.failed += 1
    elif result == constants.PASS:
      self.passed += 1
    elif result == constants.NOTRUN:
      self.notrun += 1
    elif result == constants.ERROR:
      self.error += 1
    else:
      self.unknown += 1

    self._WriteToReport()

  @DEBUG
  def SuiteReport(self, name, result, msg=''):
    """Report one suite result.

    This method should be called every time a test suite is finished. It will
    log the result to the report body part.

    Args:
      name: the suite name to report
      result: the result string 'PASS/FAIL'
      msg: any extra message you want to append to the end of this line.

    Returns:
      None.
    """
    self._WriteToRecord(BODY, '\nSUITE: %s%s%s\n%s%s' %
                        (name, ' ' * 4, result, ' ' * 8, msg))
    self._WriteToReport()

  @DEBUG
  def SetReportFile(self, file_name):
    """Update the report file name and open for writing.
    
    This will set the report file and open it for writing.
    If the report file failed to open, the test should be stopped. So no need
    to catch any exceptions here. Just let it raise up to the top level who
    ever calls it.

    Args:
      file_name: the full path of the report file.

    Returns:
      None.
    """
    self.report_file = file_name

  @DEBUG
  def GetReportFile(self):
    """Return the report file name."""
    return self.report_file

  @DEBUG
  def StartTest(self, test_name, host_name, tester, uid, uname):
    """Called at the start of the test.

    This method be called before the real test gets started. It will mark the
    time and write some prefix info about the test to the report file.

    Args:
      test_name: the name of this test.
      host_name: the machine the test runs on.
      tester: the user executed the test.
      uid: the uid of the tester.
      uname: the uname value of the host.

    Returns:
      None.
    """
    self.start_time = self._GetTimeString()
    self.test_name = str(test_name)

    self._PrefixReport(host_name, tester, uid, str(uname))
    self._WriteToReport()

  @DEBUG
  def EndTest(self):
    """Announce the test is finished, clean up.

    This method should record the end time and write the summary to the report
    file and close it. And it will close whatever pipe the instance is using.
    """
    self.end_time = self._GetTimeString()
    self._SummaryTestToRecord()
    self._WriteToReport()

  def _WriteToReport(self):
    """Write the result to self.report_file."""
    self.report_pipe = open(self.report_file, 'w')
    self.report_pipe.write(''.join(['-' * 40, '\n']))
    for message in [self.header, self.summary, self.pre_body,
                    self.body, self.extra]:
      self.report_pipe.write(message)
      self.report_pipe.write(''.join(['-' * 40, '\n']))
      self.report_pipe.flush()
    self.report_pipe.close()

  def _SummaryTestToRecord(self):
    """Construct a test summary and send to pipe.

    This is an assistant method to calculate and construct a summary info for
    the test run and send to the given pipe.

    Returns:
      None. The constructed info sent to report_pipe.
    """
    total = (self.passed + self.failed + self.timeout + self.notrun +
             self.error + self.unknown)
    if not total:
      percent = '0'
    else:
      percent = str(self.passed * 100 / total)

    self._WriteToRecord(
        SUMMARY,
        '\n'.join(['Test Summary:',
                   'Test %8s:     %d' % (constants.PASS, self.passed),
                   'Test %8s:     %d' % (constants.FAIL, self.failed),
                   'Test %8s:     %d' % (constants.TIMEOUT, self.timeout),
                   'Test %8s:     %d' % (constants.ERROR, self.error),
                   'Test %8s:     %d' % (constants.NOTRUN, self.notrun),
                   'Test Pass rate:     %s%%' % percent,
                   'Test Case Total:     %d' % total,
                   'Test Start Time:     %s' % self.start_time,
                   'Test End Time:       %s' % self.end_time,
                  ]),
        OVERWRITE)
    if self.unknown:
      self._WriteToRecord(SUMMARY, 'Test Result unknown: %d\n' % self.unknown)

  def _GetTimeString(self):
    """Generate a string represent current local time.
    
    TODO(mwu): I am planning to move this method to a common library sometime,
    since it is needed more than one place and it has nothing to do with any
    individual module.

    Returns:
      a string for timestamp.
    """
    return time.strftime('%Y%m%d%H%M')

  def _PrefixReport(self, host_name, tester, uid, uname):
    """Prepare the header section of a test report.

    This method will collect some test running environment and write to a pipe.
    Normally it is used to prefix a test result. Hence the name.

    Args:
      host_name: the name of the machine the test runs
      tester: the user executes the test
      uid: user id of the tester
      uname: uname of the host

    Returns:
      None.
    """
    s = ['PyreRing Test Report',
         'Project: %s' % self.project_name,
         'Suites: %s' % self.test_name,
         'Start Time: %s' % self.start_time,
         'Host Name: %s' % host_name,
         'Tester: %s' % tester,
         'UID: %s' % uid,
         'uname: %s' % str(uname),
         '=' * 80,
        ]

    self._WriteToRecord(HEAD, '\n'.join(s), OVERWRITE)

  @DEBUG
  def AttachHeader(self, msg, length=10):
    """ExtraMessage adds before the body of the report.

    The method will post max 'length' line of msg to the header part and
    reattach the message to EXTRA section if the msg is more than 'length'
    lines.

    Args:
      msg: <string> a string message add to the pre_body part.
      length: <int> the length kept in header part.

    Returns:
      None.
    """
    msg_list = msg.splitlines()
    if len(msg_list) > length:
      # The pre_body part has a limit of 10 lines, if the msg is larger than 10
      # lines, truncate it and attach to the extra part at the bottom.
      self._WriteToRecord(EXTRA, '...full message of header part\n')
      self._WriteToRecord(EXTRA, msg)
      self._WriteToRecord(HEAD, '\n'.join(msg_list[:(length - 1)]))
      self._WriteToRecord(HEAD, TRUNCATE_MESSAGE)
    else:
      self._WriteToRecord(HEAD, msg)

  @DEBUG
  def ExtraMessage(self, msg):
    """ExtraMessage adds to the bottom of the report.

    Args:
      msg: a string message add to the end of the report.

    Returns:
      None.
    """
    self._WriteToRecord(EXTRA, msg)
