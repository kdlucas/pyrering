#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""A basic shell runner class which implements FrameworkAdaptor.

This module contains only one class BaseRunner which implemented
PyreRingFrameworkAdaptor.

"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import logging
import os
import re
import sys
import time
import traceback

from lib import common_util
from lib import constants
from lib import emailmessage
from lib import filesystemhandlerextend
from lib import pyreringconfig
from lib import pyreringutil
from lib import reporter_txt
from lib import scanscripts

global_settings = pyreringconfig.GlobalPyreRingConfig.settings

logger = logging.getLogger('PyreRing')
DEBUG = common_util.DebugLog

ScanScriptsError = scanscripts.ScanScriptsError

WARNING_PATTERN = re.compile(r'warn', re.I)
ERROR_PATTERN = re.compile(r'error', re.I)
FATAL_PATTERN = re.compile(r'fatal', re.I)
CATCHING_LIST = [FATAL_PATTERN, ERROR_PATTERN, WARNING_PATTERN]

SETUP_SUITE = ['SETUP.sh', 'SETUP.py', 'SETUP.par', 'SETUP.suite']
SETUP_SUITE_SET = set(SETUP_SUITE)
TEARDOWN_SUITE = ['TEARDOWN.sh', 'TEARDOWN.py', 'TEARDOWN.par',
                  'TEARDOWN.suite']
TEARDOWN_SUITE_SET = set(TEARDOWN_SUITE)


class BaseRunner(pyreringutil.PyreRingFrameworkAdaptor):
  """The basic shell runner.

  This class implemented some PyreRingFramworkAdaptor methods to be able
  to run simple shell commands
  It implemented Prepare, CleanUp, Run, GetFrameworkName, GetFrameworkType
  """

  @DEBUG
  def __init__(self,
               name='/bin/sh',
               scanner=None,
               email_message=emailmessage.EmailMessage(),
               filesystem=filesystemhandlerextend.FileSystemHandlerExtend(),
               reporter=None):
    """Init the BaseRunner with a name.
    
    It should get a name from the init call of this instance. The name is not
    used currently.
    
    Args:
      name: a unique name to identify this instance, the default is /bin/sh.
      scanner: an initialized scanner with source_dir.
      email_message: An email constructor object.
      filesystem: an instance of filesystem. Default to Matt's filesystem.
      reporter: a report file generator.
    """
    super(BaseRunner, self).__init__()
    # framework_type should be the command to invoke the framework
    self.framework_type = '/bin/sh'
    self.name = name
    # Get a reference to the global prop
    self.prop = global_settings
    # Init a scanner using the source_dir
    if scanner:
      self.scanner = scanner
    else:
      self.scanner = scanscripts.ScanScripts(self.prop['source_dir'])
    # Init a filesystem for interact with shell
    self.filesystem = filesystem
    self.email_message = email_message

    # Init a reporter for generating a report
    self.reporter = reporter or (
        reporter_txt.TxtReporter(global_settings['project_name']))

    self.failed = 0
    self.passed = 0
    self.timeout = 0
    self.error = 0
    self.notrun = 0

  @DEBUG
  def Prepare(self):
    """This is to prepare the test run.

    Prepare the reporter ready to do report.
    """
    log_name = '%s_%s' % (global_settings['host_name'],
                          global_settings['log_file'])
    result_name = ''.join([os.path.splitext(log_name)[0],
                           global_settings['time'],
                           '.txt'])
    report_file = os.path.join(global_settings['report_dir'], result_name)
    self.reporter.SetReportFile(report_file)
    
  @DEBUG
  def CleanUp(self):
    """This is used to clean up its own.

    For base runner, nothing to do, so just implement the method with empty
    body.
    """
    pass

  def _RunSuites(self, suites):
    """Run a list of suites.
    
    It runs suites given. If any test in SETUP_SUITE fails, it will return 1
    to mark it is a setup failure. Otherwise, return 0 for all.
    Args:
      suites: <list> names of test suite/cases.
      
    Returns:
      int: 1 if a setup test case failed; otherwise 0
    """
    for test in suites:
      try:
        logger.debug('running %s' % test)
        test_fail_flag = self._RunSingleSuite(test)[0]
        # if the test failed and test is one of SETUP_SUITE, stop the rest of
        # testing.
        if test_fail_flag and test in SETUP_SUITE_SET:
          logger.warning('Setup test "%s" failed. No other test executed.' %
                         test)
          return 1
      except ScanScriptsError:
        # If the test doesn't exist or not supported, _RunSingleSuite will
        # throw out ScanScriptsError. Ignore the error, just go do next test
        # case.
        continue
    return 0

  def _AddUserInfo(self):
    """Add user specific information to report file.
    
    It will try to find a pre-defined header_file and attach it to the report
    file header part.
    """
    header_info_file = os.path.join(global_settings['source_dir'],
                                    global_settings['header_file'])
    try:
      header_info = open(header_info_file).readlines()
      self.reporter.AttachHeader(''.join(header_info))
      logger.info('user info file: %s added to the report' % header_info_file)
    except IOError:
      # It is OK if I don't find this file, log and ignore the error.
      logger.info('Did not find header_file: %s, did not attach it to the'
                  ' report. Moving on.' % header_info_file)

  def _Run(self, suite_list):
    """Actually run the suite_list method.

    Args:
       suite_list: a list of suite/testcases.

    Returns:
      None.
    """
    self.reporter.StartTest(str(suite_list),
                            global_settings['host_name'],
                            global_settings['tester'],
                            os.getuid(),
                            str(os.uname()))
    # Now try to find and run the setup test case if any.
    if global_settings['skip_setup']:
      logger.info('setup skipped')
    else:
      logger.info('setup suite runs')
      result = self._RunSuites(SETUP_SUITE)
      # If the SETUP_SUITE has any failed test cases, stop the test right away.
      if result:
        return result

    # Now is a good time to attach some header info,
    # if user wants to plug in some header info into the report.
    # It is OK, if this file does not exist. It will just ignore it and move
    # on.
    self._AddUserInfo()

    # TODO(mwu): need to remove setup and teardown test cases from
    # suite_list. So I will not run them twice.
    self._RunSuites(suite_list)

    if global_settings['skip_setup']:
      logger.info('teardown skipped')
    else:
      self._RunSuites(TEARDOWN_SUITE)

    self._SummaryToLog()
    self.reporter.EndTest()
    log_messages = [
        'End of this test run.',
        '=====' * 10,
        ]
    for message in log_messages:
      logger.info(message)

  def _SummaryToLog(self):
    """Summary the test result and write to log."""
    total_test = (self.failed + self.timeout + self.error + self.notrun +
                  self.passed)
    log_messages = [
        'TOTAL TESTS: %d' % total_test,
        '%s: %d' % (constants.PASS, self.passed),
        '%s: %d' % (constants.FAIL, self.failed),
        '%s: %d' % (constants.TIMEOUT, self.timeout),
        '%s: %d' % (constants.ERROR, self.error),
        '%s: %d' % (constants.NOTRUN, self.notrun),
        ]
    for message in log_messages:
      logger.info(message)

  @DEBUG
  def Run(self, suite_list, email_flag=True):
    """The public method to invoke the test.

    The suite list should be run and reports will be generated under report_dir
    directory as set in the global settings. Also email should go out if
    email_flag is set to True.
    
    Args:
      suite_list: a list of suites/tests understandable to the framework.
      email_flag: a boolean value to indicate if an email is needed for the
        report.

    Returns:
      The count of non-successful test cases.
    """
    try:
      self._Run(suite_list)
    finally:
      if email_flag and (self.failed + self.timeout + self.error + self.notrun):
        self._SendMail(suite_list)
      else:
        if email_flag:
          log_message = 'email is not sent since all test cases have passed.'
        else:
          log_message = 'email is not sent since email_flag is not set.'
        logger.info(log_message)

    return self.failed + self.timeout + self.error + self.notrun

  def _SendMail(self, suite_list):
    """Send out email after test.

    Args:
      suite_list: the user input list of suites.

    Returns:
      None.
    """
    from_address = self.prop['tester']
    to_address = self.prop['email_recipients']
    title = 'project:%s suites:%s' %(self.prop['project_name'], suite_list)
    if  self.failed or self.timeout or self.error or self.notrun:
      title = '%s is RED' % title
    else:
      title = '%s is GREEN' % title
    body = 'Here is the report:\n'
    content_file = self.reporter.GetReportFile()
    
    self.email_message.SetMessage(from_address,
                                  to_address,
                                  title,
                                  body,
                                  content_file)
    log_message = self.email_message.Send()
    if log_message:
      logger.info(log_message)
    else:
      logger.info('email sent to %s' % to_address)

  @DEBUG
  def _RunSingleSuite(self, one_suite):
    """Runs a given suite/test case one by one.

    This method is going to disassemble the given one suite to test cases and
    run each one test case in a subshell sequentially and collect return code,
    also write the results to report and log all output to log_pipe for
    further inspection.

    Args:
      one_suite: a test suite/test case name.

    Returns:
      A tuple of an overall return code and a dict of individual return codes
    """
    results = {}
    # This is used to check the suite pass or fail.
    suite_fail_flag = False
    for one_script_dict in self.scanner.BaseScan(one_suite):
      try:
        result = 0
        cmd = one_script_dict['TEST_SCRIPT']
        time_out = one_script_dict['TIMEOUT']
        args = ''
        logger.info('Test: %s......' %  cmd)
        result = self._CommandStreamer(cmd, args, time_out)
      except KeyboardInterrupt:
        err_msg = 'Keyboard interrupt'
        logger.critical('Test: %s got Keyboard interrupt' % (cmd, err_msg))
        self.reporter.TestCaseReport(cmd, constants.ERROR)
        self.error += 1
        suite_fail_flag = True
        # Set this test as ERROR out.
        result = one_script_dict['ERROR']
        try:
          err_msg = """
          Current test %s was interrupted by keyboard interrupt.  Another ctrl+c
          in 5 seconds will stop PyreRing, otherwise test will move on to the
          next test.
          """ % cmd
          print err_msg
          logger.info(err_msg)
          time.sleep(5)
        except KeyboardInterrupt:
          err_msg = """PyreRing stopped by KeyboardInterrupt."""
          print err_msg
          logger.critical(err_msg)
          raise
      # Eat any other exceptions and keep going to the next test.
      except Exception:
        err_msg = ('Exception[%s] on command[%s]. \n\tSTACK TRACE:\n%s'
                   % (sys.exc_type, cmd, traceback.format_exc()))
        log_message = 'Test: %s got Exception %s' % (cmd, err_msg)
        logger.warn(log_message)
        # Here the exception must come from executing the test, since I can't
        # decide what might be the cause here. Just fail it and keep going to
        # the next test.
        self.reporter.TestCaseReport(cmd, constants.ERROR)
        self.error += 1
        # Set this test as ERROR out.
        result = one_script_dict['ERROR']
        suite_fail_flag = True
        continue

      results[cmd] = result
      # Be careful about short circuit "or", need to _ReportTestCase first.
      suite_fail_flag = (self._CheckAndReportResult(one_script_dict, result) or
                         suite_fail_flag
                        )

    if suite_fail_flag:
      self.reporter.SuiteReport(one_suite, constants.FAIL)
    else:
      self.reporter.SuiteReport(one_suite, constants.PASS)
    return suite_fail_flag, results

  def _CheckAndReportResult(self, one_script_dict, result):
    """Check and report test result to reporter.
    
    After run finished for the test, send the result to reporter and return a
    decision if the test passed or not.
    Here in Unix shell, the exit code is stored in a Byte which is 8 bits and
    range from -127 to 127. when
    a cmd exit with a negative number, the return code is actually the positive
    complement number. So when we compare the results with expected values, we
    need to mode 256 on the expected value to make them match.
    For example: -1 will be stored as 10000001 and the complement is 01111111
    which is 255. For the command 'exit -1', the actual value you will get
    from the shell is -1%256 = 255. And the expected value if set as '-1', we
    can't compare the 2 values directly. So (result == expected%256) is the
    right way to do it. mode 256 will have no effect on positive values under
    256 which is desired. This is true on 32 bit system, not verified on 64 bit
    system yet.
    
    Args:
      one_script_dict: <dict> test case dictionary.
      result: None/int based on the test return.
      
    Returns:
      Boolean: True if the test is not a pass.
    """
    test_fail_flag = False
    cmd = one_script_dict['TEST_SCRIPT']
    if result is None:
      # If it is timeout, None is returned.
      logger.warn('Test: %s timeout' % cmd)
      self.reporter.TestCaseReport(cmd, constants.TIMEOUT)
      self.timeout += 1
      test_fail_flag = True
    elif result == one_script_dict['EXPECTED_RETURN']%256:
      # This is a pass.
      logger.info('Test: %s %d' % (cmd, result))
      self.reporter.TestCaseReport(cmd, constants.PASS)
      self.passed += 1
    elif result == one_script_dict['ERROR']%256:
      # This is a test error.
      logger.warn('Test: %s %d' % (cmd, result))
      self.reporter.TestCaseReport(cmd, constants.ERROR)
      self.error += 1
      test_fail_flag = True
    else:
      logger.warn('Test: %s %d' % (cmd, result))
      self.reporter.TestCaseReport(cmd, constants.FAIL)
      self.failed += 1
      test_fail_flag = True

    return test_fail_flag
    
  @DEBUG
  def _CommandStreamer(self, cmd, args, time_out):
    """Run the run command with a timeout.

    This method will spawn a subshell to run the command and log the output to
    the log_pipe.

    Args:
      cmd: <string> the sys command to execute
      args: <string> the args to follow the command
      time_out: <int> a time limit for this cmd in seconds

    Returns:
      the return code of the execution.
    """
    logger.info('-----running test %s %s... with timeout:%s' % (cmd, args,
                                                                time_out))
    # Back up current path.
    current_path = os.getcwd()
    # Run into a bug: if cmd = 'touch /pyrering.txt' and no args. Then
    # os.path.split(cmd)[0] will return a head = 'touch' and try to
    # ChDir(head), that will cause me problem. So in case the cmd already have
    # some arguments enbed. split the cmd first.
    head = os.path.split(cmd.split()[0])[0]
    # Go to the script dir to run it locally.
    if head:
      self.filesystem.ChDir(head)

    try:
      # Now run the test and collect return code and output message.
      ret, message = self.filesystem.RunCommandToLoggerWithTimeout(
          cmd, time_out)
      fatal_strings = global_settings.get('FATAL_STRING').split(',')
      # This is to check if the screen output contains any FATAL_STRING, then
      # test should be failed automatically, no matter what is the return code.
      for line in message.splitlines():
        if not ret:
          for fatal_string in fatal_strings:
            if fatal_string and fatal_string in line:
              ret = -1
              self.reporter.ExtraMessage('%s failed by fatal string:\n\t%s\n' %
                                         (cmd, line))
              logger.warn('%s failed by fatal string:\n\t%s' % (cmd, line))
              break
        else:
          for catch_string in CATCHING_LIST:
            # Catch suspicious output messages to log and reporter.
            if catch_string.search(line):
              self.reporter.ExtraMessage('%s:\n\t%s\n' % (cmd, line))
              logger.warn('Caught one suspicous string: %s')
              break
  
      logger.info('-----completed test %s %s with return code %s' % (cmd,
                                                                     args,
                                                                     ret))
    finally:
      self.filesystem.ChDir(current_path)
    return ret

  @DEBUG
  def GetFrameworkName(self):
    """Return the instance's name.

    Returns:
      the instance's name
    """
    return self.name
  
  @DEBUG
  def GetFrameworkType(self):
    """Return the framework type which is the command to invoke the framework.

    Returns:
      the string command to invoke the framework
    """
    return self.framework_type

  @DEBUG
  def CheckFramework(self):
    """Return True always."""
    return True
