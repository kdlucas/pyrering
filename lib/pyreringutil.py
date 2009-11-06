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

"""PyreRing Utility Classes.

This package is the lib file for PyreRing
It contains the following classes:
  PyreRingFrameworkAdaptor:
    An abstract class. It defines the interface of a framework. All
    frameworks which need to be able to plug into PyreRing need to implement
    this adaptor's methods.

  PyreRingSuiteRunner:
    The runner class to invoke the actual test framework to run the test.

  PRConfigParser:
    The config parser to parser the content of script files to figure out some
    running configuration for the test scripts.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import glob
import logging
import os
import sys
import tarfile
import traceback

from lib import common_util
from lib import filesystemhandlerextend
from lib import pyreringconfig

global_settings = pyreringconfig.GlobalPyreRingConfig.settings
logger = logging.getLogger('PyreRing')
DEBUG = common_util.DebugLog

START_SIGN = '# PR_START'
END_SIGN = '# PR_END'
BINARY_SUFFIXES = ['.par']


class PyreRingFrameworkAdaptor(object):
  """Abstract class defined the pyrering framework interface.

  Any new framework which needs to plug into pyrering needs to implement this
  adaptor. It defines the general methods will be invoked by runner.
  """

  def Prepare(self):
    """This method should be implemented to prepare the framework to run.

    Like prepare test directory, prepare test data. It will depend on the
    framework to make up the mind.
    """
    
    raise NotImplementedError('Prepare method not implemented.')

  def CleanUp(self):
    """This method should be implemented to clean up after the test.
    
    Like delete foot print, put things back, etc. It is up to the
    implementation to decide what to clean.
    """
    raise NotImplementedError('CleanUp method not implemented.')

  def Run(self, suite_list, email_flag):
    """This method will be invoked to actualy run the test.
    
    It should take a list of tests/suites as the argument and a flag for
    sending email report.

    Args:
      suite_list: a list of test/suites understandable by the framework.
      email_flag: a boolean for email result or not.

    Returns:
      None.
    """
    raise NotImplementedError('Run method not implemented.')

  def GetFrameworkName(self):
    """Get the framework name.

    Ideally each instance should have a unique name. But this is not used at
    current stage.
    """
    raise NotImplementedError('GetFrameworkName method not implemented.')

  def GetFrameworkType(self):
    """This should be implemented to return the framework type."""
    raise NotImplementedError('GetFrameworkType method not implemented.')

  def CheckFramework(self):
    """Check if the framework is avaiable to use.

    Returns:
      True if it is ready to use
    """
    raise NotImplementedError('CheckFramework method not implemented.')
  

class PyreRingSuiteRunner(object):
  """This class is a univeral runner.

  It is supposed to be constructed with any test framework which has implemented
  PyreRingFrameworkAdaptor abstract class.
  It takes care of populating the environment variables: PYTHONPATH and PATH,
  feeding a list of test suites to the framework it is constructed with and
  archiving test result files.
  """

  def __init__(self, framework, suite_list):
    """Init the runner to a specific test framework.

    The Runner will be inited to a given framework with a list of test suites
    which are to be run by the framework.

    Args:
      framework: any test framework as long as it implements
        PyreRingFramworkAdaptor.
      suite_list: a list of test suites passed by user command line, the suite
        names should be recognizable by the framework.

    Returns:
      None
    """
    self.framework = framework
    self.run_suite = suite_list
    self.prop = global_settings
    # This is the list of log or report types will be generated at report_dir.
    # It will be used to do archiving and also clean up previous leftover.
    self.report_types = ['.txt']

  @DEBUG
  def SetUp(self):
    """The method will try to setup the test environment.
    
    Specifically, it will clean up the report directory for new reports and
    call the framework's Prepare method to let it prepare itself.

    Returns:
      None
    """
    report_dir = self.prop['report_dir']
    if not os.path.isdir(report_dir):
      os.makedirs(report_dir)
    host_name = self.prop['host_name']
    report_file_list = [os.path.join(report_dir, host_name + '*' + x)
                        for x in self.report_types]
    self.CleanFiles(report_file_list)
    self.framework.Prepare()

  @DEBUG
  def TearDown(self):
    """It will give the test framework a chance to clean up after itself.

    Basically it just calls the framework's Cleanup method.
    """
    self.framework.Cleanup()

  def _SetEnvironment(self):
    """Called by Run to set up environment variables.
    
    there are some environment variables we need to pass on to the subshell
    which will be used to run the actual test scripts.
    1. the source_dir: this variable defines the root directory of the project
    specific directory. testcase scripts should be under a subdir of this dir.
    And all other project specific things should be put under this dir.
    Also users can refer os.environ['source_dir'] to get the absolute path and
    looking around the file system for other files.

    2. PYTHONPATH: here we will add the use defined python libs to python path,
    so user will not need to bother with python path management. The default
    one is $source_dir, also user can add any other path by defining
    'python_lib_dir' variable in the configure file.
    So in the test script, pythonpath will be set automatically, user can drop
    their lib files to $source_dir as the top level and follow the import
    format of python import rule or any where they define in
    python_lib_dir

    3. PERL5LIB: Similar as PYTHONPATH with extra 'perl_lib_dir' for user to
    define extra libary path.

    Returns:
      None
    """
    environment_path_list = (
        ('PYTHONPATH', 'python_lib_dir'),
        ('PATH', 'shell_lib_dir'),
        ('PERL5LIB', 'perl_lib_dir'),
        )

    # Setting up environment first, these variables will be passed on to the
    # subshell which is used to run the actual test scripts.

    # This is default lib path we need to add on
    lib_path = self.prop['source_dir']
    os.environ['source_dir'] = lib_path

    for environment_path, user_var in environment_path_list:
      self._AttachEnvironmentPath(environment_path, [lib_path])
      if user_var in self.prop:
        self._AttachEnvironmentPath(
            environment_path,
            self.prop[user_var].split(os.pathsep))

  def _AttachEnvironmentPath(self, env_var, new_paths):
    """Attach new_path to the environment path variable.
    
    This method is used to update path environment variables.
    It will append a list of paths to the given environment variable.

    Args:
      env_var: <string> the target environment variable to be appended to.
      new_paths: <list> a list of pathes to append the env_var.

    Returns:
      None.
    """
    for new_path in new_paths:
      try:
        path = os.environ[env_var]
        # Attach the new_path if it is not already in it.
        if not new_path in path.split(os.pathsep):
          path = os.pathsep.join([path, new_path])
          os.environ[env_var] = path
      except KeyError:
        # There is no such variable in environment.
        os.environ[env_var] = new_path
      logger.debug('%s is updated to: %s' %(env_var, new_path))

  @DEBUG
  def Run(self, email_flag=True):
    """The public method to start the test.

    The actual runner to invoke the test framework to run a set of tests,
    then it will try to collect all types of files in report directory and
    archive them. Remember the archive is not actual log file. Just an archive
    with all the junks generated during the test run. You might need them
    later, who knows.

    Args:
      email_flag: a boolean value to state if an email is expected or not. But
      it is up to the framwork implementer to decide if email will come or
      not.

    Returns:
      The count of non-successful test cases.
    """
    self._SetEnvironment()
    failure_count = self.framework.Run(self.run_suite, email_flag)
    # After the test run, try to go to report directory collect all log files
    # and archive them.
    archive_name = os.path.join(self.prop['report_dir'], '%s_%s.tar.gz' %
                                (self.prop['host_name'], self.prop['time']))
    keep_log = True
    report_dir = self.prop['report_dir']
    host_name = self.prop['host_name']
    report_file_list = [os.path.join(report_dir, host_name + '*' + x)
                        for x in self.report_types]
    self.TarReports(archive_name, report_file_list, keep_log)
    return failure_count

  @DEBUG
  def TarReports(self, archive_file, report_file_list, keep=True):
    """Generate an tar.gz archive file.
    
    This method will generate a tar.gz file using the given the list of file
    patterns to collect. The purpose of this method is to archive all the files
    logs generated during the test run. It is not a log nor a report, just an
    archive.

    Args:
      archive_file: the file name to generate, it should end with tar.gz, since
      the generate file will be tar.gz format.
      report_file_list: the list of files/pattern to collect in the archive
      keep: a boolean value to identify if the original log file should be
      removed or not after the archive.

    Returns:
      None. The archive file should be created as specified.
  
    """
    tar = tarfile.open(archive_file, 'w:gz')
    for name in report_file_list:
      for onefile in glob.glob(name):
        os.chdir(os.path.dirname(onefile))
        tar.add(os.path.basename(onefile))
        if not keep:
          os.remove(onefile)
    tar.close()

  @DEBUG
  def CleanFiles(self, report_file_list):
    """Remove a list of files/patterns.
    
    It is used to clean up leftover reports/log files from previous run.

    Args:
      report_file_list: the list of file names, patterns to clean

    Returns:
      None
    """
    for name in report_file_list:
      for onefile in glob.glob(name):
        os.remove(onefile)


class PRConfigParser(object):
  """A util class to parse pyrering specific runner config.

  It will read in a section of comments in a given text file(normally it should
  be the actual test script or test suite file and the config info is embedded
  as a comment section. the section should look like this:
      # PR_START
      # key1 = value1
      # key2 = value2
      # PR_END
  Currently supported keys are: TIMEOUT, ROOT_ACCESS, EXPECTED_RETURN,
  CONCURRENT, NFS, ERROR. These configs describe how this test script
  should be run with.
  This info will be read in and packed in a dictionary and send to the actual
  runner to execute the script, which has the final decision how the test script
  should be run.
  """

  def __init__(self,
               filesystem=filesystemhandlerextend.FileSystemHandlerExtend()):
    """Provide a empty dictionary and a list of supported keys.

    Args:
      filesystem: a FileSystemHandlerExtend object as a layer between this code
      and the actual filesystem. So I can swap this layer with a mock
      filesystem for testing.
    """
    self.filesystem = filesystem

    # This is the list of currently supported config keys. Any other keys not
    # defined in this list will be take as strings only.
    self.key_list = ['TEST_SCRIPT',
                     'TIMEOUT',
                     'ROOT_ACCESS',
                     'EXPECTED_RETURN',
                     'CONCURRENT',
                     'NFS',
                     'VERSION',
                     'SIZE',
                     'COMMENTS',
                     'FLAGS',
                     'ERROR',
                    ]

  @DEBUG
  def Default(self):
    """Return a config dictionary with default value populated.

    Returns:
      A dictionary of configuration with default value populated.
      The default keys are:
      'TEST_SCRIPT'
      'TIMEOUT'
      'ROOT_ACCESS'
      'EXPECTED_RETURN'
      'CONCURRENT'
      'NFS'
      'VERSION'
      'SIZE'
      'COMMENTS'
      'FLAGS'
      'ERROR'
    """
    test_case_config = {}
    test_case_config['TEST_SCRIPT'] = ''
    test_case_config['TIMEOUT'] = 600
    test_case_config['ROOT_ACCESS'] = False
    test_case_config['EXPECTED_RETURN'] = 0
    test_case_config['CONCURRENT'] = True
    test_case_config['NFS'] = False
    test_case_config['VERSION'] = '1.0'
    test_case_config['SIZE'] = 'SMALL'
    test_case_config['COMMENTS'] = None
    test_case_config['FLAGS'] = None
    test_case_config['ERROR'] = 255 

    return test_case_config

  def _ParseLine(self, line):
    """Assistant method to parse a line of config.

    The line has to start with '#' not '##' and has a key value pair seperated
    by a '=', otherwise the line will be ignored.

    Args:
      line: a line of config file.
      
    Returns:
      A dictionary has one pair of key, value corresponding to the line.

    Raises:
      ValueError: if ROOT_ACCESS, CONCURRENT, NFS are given non-valid boolean
      values or TIMEOUT, EXPECTED_RETURN, ERROR are given none integers.
    """
    temp_dict = {}
    if (not line.startswith('#') or
        line.startswith('##') or
        len(line.split('=')) != 2):
      return temp_dict

    key, value = line[1:].split('=', 1)
    key = key.strip().upper()
    value = value.strip().strip('"').strip("'")
    if key in ['TIMEOUT', 'EXPECTED_RETURN', 'ERROR']:
      try:
        temp_dict[key] = int(value)
      except:
        raise ValueError('Invalid integer %s for key:%s' % (value, key))
    elif key in ['ROOT_ACCESS', 'CONCURRENT', 'NFS']:
      if value.lower().startswith('false'):
        temp_dict[key] = False
      elif value.lower().startswith('true'):
        temp_dict[key] = True
      else:
        raise ValueError('Invalid boolean value %s for key:%s' % (value, key))
    else:
      # Otherwise, just store it as string value
      temp_dict[key] = value
    return temp_dict

  @DEBUG
  def ParseList(self, lines, populate_default=True):
    """Parser a list of lines and return a dictionary of configs.

    The list of lines can come from readlines() of a file or a user defined
    list of info.

    Args:
      lines: a list of lines
      populate_default: boolean value if missing value should be populated
      by default values.

    Returns:
      the dictionary of configuration

    Raises:
      ValueError: if missing end of config sign: END_SIGN.
    """
    # Reset self.test_case_config each time start a new ParseList
    test_case_config = {}
    for i in range(len(lines)):
      one_line = lines[i].strip()
      if one_line.startswith(START_SIGN):
        # Start of PyreRing config section
        for j in range(i+1, len(lines)):
          config_line = lines[j].strip()
          if config_line.startswith(END_SIGN):
            # End of the PyreRing config section
            break
          elif config_line.startswith('#'):
            # This is a config line, parse it
            test_case_config.update(self._ParseLine(config_line))
        else:
          # If no break ever got, it is ill formatted
          raise ValueError('Missing end of %s line' % END_SIGN)
        break
    if populate_default:
      default = self.Default()
      default.update(test_case_config)
      logger.debug('exit PRConfigParser.ParseList with default')
      return default
    else:
      logger.debug('exit PRConfigParser.ParseList with user settings')
      return test_case_config

  @DEBUG
  def ParseFile(self, anyfile, populate_default=True):
    """Given a file parse out the config section.

    Args:
      anyfile: a file path
      populate_default: a boolean value if default value should be given if not
        defined.

    Returns:
      a dictionary of the configuration

    Raises:
      ValueError: if the file has invalid configuration info
    """
    # If this file is a binary file. Don't scan it, populate with default
    # values and return the config.
    if os.path.splitext(anyfile)[1] in BINARY_SUFFIXES:
      configs = self.Default()
      configs['TEST_SCRIPT'] = anyfile
      logger.debug('exit PRConfigParser.ParseFile with binary default')
      return configs

    config_file = self.filesystem.FileOpenForRead(anyfile)
    try:
      try:
        configs = self.ParseList(config_file.readlines(), populate_default)
      except ValueError:
        err_msg = ('Exception[%s] on file: [%s].\n\tSTACK TRACE:\n%s' %
                   (sys.exc_type, anyfile, traceback.format_exc()))
        raise ValueError(err_msg)
    finally:
      self.filesystem.FileClose(config_file)
    # This always overwrites whatever defined in configuration.
    configs['TEST_SCRIPT'] = anyfile
    return configs

  @DEBUG
  def ParseFiles(self, files, populate_default=True):
    """Parse a list of files.

    Args:
      files: a list of files
      populate_default: a boolean value to populate none defined keys with
      default value or not

    Returns:
      a list of dictionaries of configurations.
    """
    config_list = []
    for one_file in files:
      config_list.append(self.ParseFile(one_file, populate_default))
    return config_list

  @DEBUG
  def ParseSuite(self, suite_file, files, populate_default=True):
    """Parse a list of files for a suite.

    The suite file configuration will overwrite the individual files
    configuration if defined.

    Args:
      suite_file: a pyrering suite defination file path
      files: a list of files
      populate_default: boolean value should provide default value if some keys
        are not defined.

    Returns:
      a list of config dictionary with the suite config overwrite script
      config
    """
    config_list = []
    suite_config = self.ParseFile(suite_file, False)
    # Remove the TEST_SCRIPT key, so suite config will not wipe out
    # TEST_SCRIPT key value.
    suite_config.pop('TEST_SCRIPT')
    config_list = self.ParseFiles(files, populate_default)
    for one_config in config_list:
      one_config.update(suite_config)
    return config_list
