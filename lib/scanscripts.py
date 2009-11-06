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

"""Contains PyreRing's unique test case management class.

The class ScanScripts scans the given directory and manages suites for
PyreRing project.
The class should be created with a valid directory which should be the top dir
of all other test scripts.
the main method to call is BaseScan() with a list of names. The name can be
either a suite file, a test script, a directory with relative path to the top
dir defined at the init time. Then BaseScan will give back a list of
dictionaries containing the name of the script and some properties defined
inside the script about how the script should be run.
For example:
  Define the source_dir as '/tmp/source'
  Then you can call it like this:
  one_instance.BaseScan('one_suite.suite')
  or
  one_instance.BaseScan('dir1/')
  or
  one_instance.BaseScan('dir1/test_script1.py')

  Then BaseScan will return a list of dictionaries and each dictionary will
  contain one test script and how it should be run info.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import logging
import os

from lib import common_util
from lib import filesystemhandlerextend
from lib import pyreringutil

logger = logging.getLogger('PyreRing')
DEBUG = common_util.DebugLog

# Define the currently supported file extentions.
SUITE_SUFFIXES = ['.suite']
SCRIPT_SUFFIXES = ['.sh', '.py', '.par', '.pl']


class Error(Exception):
  """Base Exception class for ScanScript."""
  pass


class ScanScriptsError(Error):
  """General ScanScript Failed."""
  pass


class TestNotFoundError(ScanScriptsError):
  """Failed to find the test."""
  pass


class TestNotSupportedError(ScanScriptsError):
  """File extendtion is not supported."""
  pass


class LoopConditionError(ScanScriptsError):
  """Loop found in suite files."""
  pass


class ScanScripts(object):
  """Utility class to scan files from the filesystem."""

  @DEBUG
  def __init__(self,
               source_dir,
               filesystem=filesystemhandlerextend.FileSystemHandlerExtend()):
    """Init the ScanScripts class with the top test script directory.

    Args:
      source_dir: the top level of the test scripts, it has to be a valid
        dir.
      filesystem: a layer between this code and the file system. So we can
        mock the filesystem for unittest. The default value is a real
        filesystem.

    Raises:
      TestNotFoundError: if source_dir is not a valid path
    """
    self.filesystem = filesystem
    if not self.filesystem.CheckDir(source_dir):
      raise TestNotFoundError('source_dir has to be an existing dir: %s.'
                              % source_dir)
    self.script_dir = os.path.abspath(os.path.normpath(source_dir))

    # These variables are used to monitor a recursion in suite definitions.
    # Whenever the code is going to visit a suite file, it should
    # always check these lists and add the suite to them if it is a new suite.
    # Here we have a list version and a set version of the visited suites. They
    # contain exactly the same suites just in different data structures.
    # The list version is used to keep tracking the sequence of the visiting
    # and the set version is used to do the quick check to see if some suite has
    # been visited before.
    self.including_suite_visited = []
    self.excluding_suite_visited = []

    self.including_suite_visited_set = set()
    self.excluding_suite_visited_set = set()

  @DEBUG
  def BaseScan(self, suite_name):
    """Main method to scan filesystem.
    
    This should scan the given names and return a list of scripts
    corresponding to the suite.

    The logic is this:
    suite_name:
      dir? return all scripts under that dir.
      file?
        script_file? return this script_file
        suite_file? return this suite test cases.
        else: raise TestNotSupportedError
      else:
        I don't know what you want.
        raise TestNotFoundError
      raise ScanScriptError for all other error conditions.
      (TODO(mwu): I will spent more time on categorizing the error cases to
      raise more specific errors.)

    Args:
      suite_name: name of the suite. It should be a relative path to the
        self.script_dir. So os.path.join(script_dir, suite_name) should make an
        absolute path point to the suite file or script file
        For example: it can be
          testsuite1/suite1.suite | testcase.py | suite_directory
          then self.script_dir, suite_name will make an absolute path pointing
          to the file.
          if the suite_name is an empty string or a '.', the method will return
          all scripts under self.script_dir
        This method will figure out what type of the input is and return the
        list accordingly.

    Returns:
      A list of dictionaries corresponding to the suite_name given. Each
      dictionary contains a test script and info for how to run.

    Raises:
      TestNotSupportedError: if given not supported file.
      TestNotFoundError: if given name is not a valid dir/file/suite name.

    Caveats:
      If given a directory, all scripts under this dir and sub-dirs will be
      included. But all suite files will be skipped. If you want to run a suite
      file, you have to specifically give the suite file name.
    """
    test_case_list = []
    full_path = os.path.normpath(os.path.join(self.script_dir, suite_name))
    if self.filesystem.CheckDir(full_path):
      # This is a dir, we should return all script files.
      for dirpath, unused_dnames, filenames in self.filesystem.Walk(full_path):
        for one_file in filenames:
          if os.path.splitext(one_file)[1] in SCRIPT_SUFFIXES:
            test_case_list.append(os.path.join(dirpath, one_file))
      parser = pyreringutil.PRConfigParser(self.filesystem)
      logger.debug('exit ScanScripts.BaseScan with dir results')
      return parser.ParseFiles(test_case_list)

    elif self.filesystem.CheckFile(full_path):
      # If it is a file, need to check if it is a script or a suite.
      if os.path.splitext(full_path)[1] in SCRIPT_SUFFIXES:
        # This is a script.
        parser = pyreringutil.PRConfigParser(self.filesystem)
        logger.debug('exit ScanScripts.BaseScan with file result')
        return parser.ParseFiles([full_path])
      elif os.path.splitext(full_path)[1] in SUITE_SUFFIXES:
        # This is a suite file.
        # Init the visited suite list and put this suite as the first included
        # suite
        self.including_suite_visited = [full_path]
        self.including_suite_visited_set.add(full_path)
        self.excluding_suite_visited = []
        self.excluding_suite_visisted_set = set()
        # Then read the suite file and parse it.
        parser = pyreringutil.PRConfigParser(self.filesystem)
        logger.debug('exit ScanScripts.BaseScan with suite results')
        return parser.ParseSuite(full_path,
                                 list(self._ReadSuiteFiles(full_path)))
      else:
        logger.debug('exit with exception TestNotSupportedError')
        raise TestNotSupportedError('File extension is not supported %s'
                                    % full_path)
    else:
      logger.debug('exit with exception TestNotFoundError')
      raise TestNotFoundError('Wrong suite name: %s' % full_path)
  
  def _ParseOneLine(self, dir_name, one_line):
    """Parse one line of a suite file.

    Given one line from the suite file, trying to put corresponding scripts or
    suites into testcase_set and suite_set, return them.
    The line should point to a file/dir relative to the current directory. For
    example:
      dir1/dir2/testscript.py
      dir1/another.suite
      dir1
    Lines start with '#' will be taken as comments. And empty lines are ignored
    too.
    
    Args:
      dir_name: the suite file resident dir
      one_line: the line get from the suite file, it should point to either
        a dir, script(s) or suite(s) with the starting '-' removed if any.
        dir_name and one_line join together should be an absolute path
      
    Returns:
      A tuple of 2 sets: testcase_set, suite_set. They should be populated based
      on the content of the given line. Either one could be empty.

    Raises:
      ScanScriptsError: if the line is invalid. Invalid means either the path
      doesn't exist or the file extension is not supported.

    Caveats:
      If the line points to a nonexist file with the right extension, it will
      be silently ignored. This case can happen when the real script got
      deleted, renamed or it is a future name.
    """
    testcase_set = set()
    suite_set = set()
    point_path = os.path.normpath(os.path.join(dir_name, one_line))
    suffix = os.path.splitext(one_line)[1]
    
    if self.filesystem.CheckDir(point_path):
      # This is a dir, find all the scripts
      for dpath, unused_dnames, fnames in os.walk(point_path):
        for one_file in fnames:
          if os.path.splitext(one_file)[1] in SCRIPT_SUFFIXES:
            testcase_set.add(os.path.join(dpath, one_file))
    elif suffix in SCRIPT_SUFFIXES:
      # This is a script(s)
      testcase_set.update(self.filesystem.Glob(point_path))
    elif suffix in SUITE_SUFFIXES:
      # This is a suite(s)
      suite_set.update(self.filesystem.Glob(point_path))
    else:
      # Dir does not exist or not supported extension
      msg = ('The file extension is not supported or the directory does not'
             ' exist: %s' % one_line)
      logger.error(msg)
      raise ScanScriptsError(msg)
    return testcase_set, suite_set
  
  def _ReadOneSuiteFile(self, full_path):
    """Parse one suite file, none recursively.
    
    This method will parse one suite file and constructe
    include_testcase_set, include_suite_set, exclude_testcase_set,
    exclude_suite_set to put each line of the suite definition file to the
    correct set.
    There are several scenarios we need to take care:
    1. include a script or scripts with wild char
    2. include a dir
    3. include another suite file
    4. exclude a script or scripts with wild char
    5. exclude a dir
    6. exclude another suite file
    
    Args:
      full_path: a full path of a suite file
      
    Returns:
      include_testcase_set: the testcases for includeing in this suite
      include_suite_set: the suites for including in this suite
      exclude_testcase_set: the testcases excluding from this suite
      exclude_suite_set: the suites excluding from this suite
    """
    include_testcase_set = set()
    include_suite_set = set()
    exclude_testcase_set = set()
    exclude_suite_set = set()
    dir_name = os.path.dirname(full_path)

    suite_handler = self.filesystem.FileOpenForRead(full_path)
    try:
      for one_line in suite_handler:
        one_line = one_line.strip()
        if not one_line or one_line.startswith('#'):
          # This is a comment line, ignore it.
          continue
        elif one_line.startswith('-'):
          # This is exclude case.
          testcase_set, suite_set = self._ParseOneLine(dir_name, one_line[1:])
          exclude_testcase_set.update(testcase_set)
          exclude_suite_set.update(suite_set)
        else:
          # include case
          testcase_set, suite_set = self._ParseOneLine(dir_name, one_line)
          include_testcase_set.update(testcase_set)
          include_suite_set.update(suite_set)
    finally:
      self.filesystem.FileClose(suite_handler)
    # After looping this suite file, return the 4 sets we just populated
    return (include_testcase_set,
            include_suite_set,
            exclude_testcase_set,
            exclude_suite_set)
                
  def _ReadSuiteFiles(self, full_path):
    """Recursively resolve a suite definition file.

    This method will open the suite definition file and read through and
    translate each line to lists of actual scripts. Finally construct a list of
    test scripts.
    One check point is whenever we try to open a suite file, we first need to
    check if it is visited before by checking including_suite_visited or
    excluding_suite_visited. If it was visited before, raise ScanScriptsError.
    If it was not visited before, add it to the list and visit it.

    Args:
      full_path: the path the suite definition file.
      
    Returns:
      A set of scripts according to the suite definition file.

    Raises:
      ScanScriptsError: if a loop found in suite file definitions.
    """
    (include_testcase_set,
     include_suite_set,
     exclude_testcase_set,
     exclude_suite_set) = self._ReadOneSuiteFile(full_path)
    
    # Trying to remove the excluded suites and test cases once.
    include_testcase_set -= exclude_testcase_set
    include_suite_set -= exclude_suite_set

    # If there are still suites not resolved, resolve them
    for one_suite in include_suite_set:
      if one_suite in self.including_suite_visited_set:
        # This suite has been visited before
        msg = ('include loop found: %s at %s' %
               (str(self.including_suite_visited), one_suite))
        logger.error(msg)
        raise ScanScriptsError(msg)
      else:
        self.including_suite_visited.append(one_suite)
        self.including_suite_visited_set.add(one_suite)
        extra_testcase_set = self._ReadSuiteFiles(one_suite)
        include_testcase_set.update(extra_testcase_set)
    for one_suite in exclude_suite_set:
      if one_suite in self.excluding_suite_visited_set:
        # This suite has been visited before
        msg = ('exclude loop found: %s at %s' %
               (str(self.excluding_suite_visited), one_suite))
        logger.error(msg)
        raise ScanScriptsError(msg)
      else:
        self.excluding_suite_visited.append(one_suite)
        self.excluding_suite_visited_set.add(one_suite)
        extra_testcase_set = self._ReadSuiteFiles(one_suite)
        include_testcase_set -= extra_testcase_set
      
    return include_testcase_set
