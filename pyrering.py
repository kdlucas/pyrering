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


"""The PyreRing runner to execute tests.

This is the entry point of PyreRing test framework. PyreRing is a universal
script management system, used for running any set of tests with a given
framework. Currently, it is being provided with a default baserunner framework,
which starts a python subshell inside which test commands can be executed.

Usage:
  ./pyrering.par <options> <suite | directory | script names>
    Multiple suites, directories, scripts separated by spaces. There arguments
    are either relative to the source_dir value or absolute paths.

  Options
  --conf_file: point the path to the config file. The default is
    ./conf/pyrering.conf. PyreRing will create this file if it doesn't exist.
  --email_recipients: the email recipients, separated by commas
  --file_errors: send failing testcase errors and output to a separate file.
  --log_file: the name of the log file. It should not include the path.
    The default value is pyrering.log and it will always be found at
    <report_dir>/<host_name>_<log_file>.
  --project_name: the name of the project. It will show up at the report file
    and email subject part.
  --report_dir: the path of all report files. The default location is ./reports
  --reset: If it is true, pyrering.conf will be overwritten with command
    arguments and default values. Default is False.
  --runner: <test execution framework> (Right now the only available and default
    value is 'baserunner').
  --sendmail: send the report via email. Default is False.
  --nosendmail: do not send the report via email.
  --source_dir: the top directory for test scripts. No default value.
  --version: print out PyreRing version information and quit when set.

  Arguments should be space separated suite/directory/script names with the
  relative path to source_dir or the absolute paths. PyreRing will treat each
  argument as an individual suite run and one report/email will be generated
  after all suites run. If you want to group test runs into one suite, make a
  suite file and use PyreRing to run that suite file.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import logging
import optparse
import os
import sys

from lib import baserunner
from lib import pyreringconfig
from lib import pyreringutil

import release_info

logger = logging.getLogger('PyreRing')

global_settings = pyreringconfig.GlobalPyreRingConfig.settings


class Error(Exception):
  """Base exception class."""
  pass


class UnrecognizedRunnerError(Error):
  """Raised if the runner is not recognized by PyreRing."""
  pass


def SetLogger():
  """Set valid options."""
  hdlr = logging.FileHandler(os.path.join(global_settings['report_dir'],
                                          global_settings['log_file']))
  formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
  hdlr.setFormatter(formatter)
  logger.addHandler(hdlr)

  debug = global_settings.get('log_level', 'info').lower()
  if debug == 'debug':
    logger.setLevel(logging.DEBUG)
  elif debug == 'info':
    logger.setLevel(logging.INFO)
  elif debug == 'warning':
    logger.setLevel(logging.WARNING)
  elif debug == 'error':
    logger.setLevel(logging.ERROR)
  elif debug == 'critical':
    logger.setLevel(logging.CRITICAL)
  else:
    logger.setLevel(logging.INFO)


def ParseArgs():
  """Get user options."""
  parser = optparse.OptionParser()
  parser.add_option('--report_dir',
                    help='report_directory',
                    dest='report_dir')
  parser.add_option('--conf_file',
                    help='config file name',
                    dest='conf_file')
  parser.add_option('--project_name',
                    help='name of your project',
                    dest='project_name')
  parser.add_option('--file_errors',
                    help='store stderr/stdout to file on test errors',
                    action='store_true',
                    default=False,
                    dest='file_errors')
  parser.add_option('--sendmail',
                    help='send email report or not',
                    action='store_true',
                    dest='sendmail')
  parser.add_option('--nosendmail',
                    help='do not email report',
                    action='store_true',
                    dest='nosendmail')
  parser.add_option('--email_recipients',
                    help='recipients of email',
                    dest='email_recipients')
  parser.add_option('--log_file',
                    help='help log file name',
                    dest='log_file')
  parser.add_option('--reset',
                    help='reset the conf file to default',
                    action='store_true',
                    default=False,
                    dest='reset')
  parser.add_option('--runner',
                    help='runner name',
                    dest='runner')
  parser.add_option('--version',
                    help='display version info',
                    action='store_true',
                    default=False,
                    dest='version')
  parser.add_option('--source_dir',
                    help='top level directory for test scripts.',
                    dest='source_dir',)

  return parser.parse_args()


def main(args):
  """The pyrering main entrance.

  Takes various user command line arguments and initializes a runner as
  specified by the --runner command line flag. Currently 'baserunner' is the
  only runner available.

  Returns:
    None.

  Raises:
    UnrecognizedRunnerError: If the runner is not recognized by PyreRing.
  """
  user_args = {}
  pyrering_root_path = os.path.abspath(os.path.split(args[0])[0])
  options, args = ParseArgs()
  if options.version:
    print release_info.VERSION
    return
  # initialize GloalPyreRingConfig with the pyrering root path and user args
  # then GlobalPyreRingConfig.settings is ready to be used.
  if options.log_file:
    user_args['log_file'] = options.log_file
  if options.runner:
    user_args['runner'] = options.runner
  if options.reset:
    user_args['reset'] = True
  if options.email_recipients:
    user_args['email_recipients'] = options.email_recipients
  if options.source_dir:
    user_args['source_dir'] = os.path.abspath(options.source_dir)
  if options.project_name:
    user_args['project_name'] = options.project_name
  if options.report_dir:
    user_args['report_dir'] = os.path.abspath(options.report_dir)
  if options.conf_file:
    user_args['conf_file'] = os.path.abspath(options.conf_file)
  if options.sendmail:
    user_args['sendmail'] = True
  if options.nosendmail:
    user_args['sendmail'] = False
  if options.file_errors:
    user_args['file_errors'] = True


  pyreringconfig.Init(pyrering_root_path, user_args)
  # Need to have the report dir ready before logging can happen.
  if not os.path.isdir(global_settings['report_dir']):
    os.makedirs(global_settings['report_dir'])
  SetLogger()
  print ('log has been redirected to %s' %
         os.path.join(global_settings['report_dir'],
                      global_settings['log_file'])
         )

  logger.info('PyreRing run instance started')
  logger.debug(str(global_settings))

  # now set the runner to user specified runner and start the test.
  failure_count = 0
  if len(args) >= 1:
    if global_settings['runner'] == 'baserunner':
      runner = baserunner.BaseRunner()
    else:
      # I don't have other runners to use now.
      raise UnrecognizedRunnerError('Other Runners pending ;-)')
    logger.info('run test suites: %s' % str(args))
    suite_runner = pyreringutil.PyreRingSuiteRunner(runner, args)
    suite_runner.SetUp()
    failure_count = suite_runner.Run(global_settings['sendmail'])
    logger.info('exit pyrering with %d' % failure_count)
  else:
    print __doc__

  if failure_count:
   sys.exit(1)
  else:
    return


if __name__ == '__main__':
  main(sys.argv)
