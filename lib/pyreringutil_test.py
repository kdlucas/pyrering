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

"""Unittest for pyreringutil.PRConfigParser.

Unit test cases for PRConfigParser only. The other two classes in
pyreringutil.py have not been tested yet.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'


import os
import shutil
import tempfile
import unittest

from lib import mock_filesystemhandlerextend
from lib import mock_pyreringframeworkadaptor
from lib import pyreringconfig
from lib import pyreringutil

global_settings = pyreringconfig.GlobalPyreRingConfig.settings

DEFAULT_DICT = {'ROOT_ACCESS': False,
                'TIMEOUT': 600,
                'EXPECTED_RETURN': 0,
                'CONCURRENT': True,
                'NFS': False,
                'TEST_SCRIPT': '',
                'SIZE': 'SMALL',
                'VERSION': '1.0',
                'COMMENTS': None,
                'FLAGS': None,
                'ERROR': 255,
               }


class PyreRingUtilPyreRingSuiteRunnerTest(unittest.TestCase):
  def setUp(self):
    self.framework = (
        mock_pyreringframeworkadaptor.MockPyreRingFrameworkAdaptor())
    self.suite_list = ['test1', 'test2']
    self.suite_runner = pyreringutil.PyreRingSuiteRunner(self.framework,
                                                           self.suite_list)
    # Get the global_settings populated with some dummy values.
    self.tmp_dir = tempfile.mkdtemp()
    global_settings.update({'root_dir': self.tmp_dir,
                            'report_dir': os.path.join(self.tmp_dir, 'report'),
                            'conf_file': os.path.join(self.tmp_dir,
                                                      'conf/pyrering.conf'),
                            'host_name': 'testmachine',
                            'tester': 'auto',
                            'project_name': 'unitest',
                            'default_suite': 'default_suite',
                            'source_dir': os.path.join(self.tmp_dir, 'source'),
                            'sendmail': False,
                            'email_report': 'someone,another',
                            'log_file': 'pyrering.log',
                            'runner': 'anyrunner',
                            'FATAL_STRING': '',
                            'time': '20080101',
                           })

  def tearDown(self):
    shutil.rmtree(self.tmp_dir)

  def testSetupMethodCreateReportDirectory(self):
    """SetUp method should create the report directory if it doesnot exist."""
    report_dir = os.path.join(self.tmp_dir, 'report')
    global_settings['report_dir'] = report_dir
    self.suite_runner.SetUp()
    self.assertTrue(os.path.isdir(report_dir))

  def testSetupMethodCleanupReportDirectory(self):
    """Setup should clean up report directory for previous reports."""
    report_dir = os.path.join(self.tmp_dir, 'report')
    global_settings['report_dir'] = report_dir
    if not os.path.isdir(report_dir):
      os.makedirs(report_dir)
    host_name = global_settings['host_name']
    report_file = os.path.join(report_dir, host_name + 'whatever' +
                               self.suite_runner.report_types[0])
    handler = open(report_file, 'a')
    handler.close()
    self.suite_runner.SetUp()
    self.failIf(os.path.isfile(report_file))

  def testRunCheckEnvironment(self):
    """Run method should get environment variable set for 3 variables."""
    global_settings['source_dir'] = self.tmp_dir
    self.suite_runner.SetUp()
    self.suite_runner.Run(False)
    path = os.environ['PATH']
    self.assertTrue(self.tmp_dir in path.split(':'))
    pythonpath = os.environ['PYTHONPATH']
    self.assertTrue(self.tmp_dir in pythonpath.split(':'))
    perl5lib_path = os.environ['PERL5LIB']
    self.assertTrue(self.tmp_dir in perl5lib_path.split(':'))
    self.assertEqual(self.tmp_dir, os.environ['source_dir'])

  def testRunGetBackResults(self):
    """The framework returns an int back and Run should pass on that value."""
    self.framework.SetResult(2)
    self.suite_runner.SetUp()
    self.assertEqual(self.suite_runner.Run(False), 2)

  def testTarReports(self):
    """test Tar report files."""
    tmp_file = os.path.join(self.tmp_dir, 'test.txt')
    tar_file = os.path.join(self.tmp_dir, 'test.tar.gz')
    self.suite_runner.TarReports(tar_file, [tmp_file], keep=False)
    self.assertTrue(os.path.isfile(tar_file))
    self.failIf(os.path.isfile(tmp_file))


class PyreRingUtilPRConfigParserTest(unittest.TestCase):
  def setUp(self):
    self.mock_filesystem = (
        mock_filesystemhandlerextend.MockFileSystemHandlerExtend())
    self.one_parser = pyreringutil.PRConfigParser(self.mock_filesystem)
    
  def _PopulateFileSystem(self, temp_file_system):
    for key, value in temp_file_system.iteritems():
      self.mock_filesystem.WriteToFile(key, value)

  def testNormalFormat(self):
    """A normal test case.

    A normail definition of a PR config. Expected return should be test_dict.
    """
    test_config_lines = ['# PR_START',
                         '# ROOT_ACCESS = False',
                         '# TIMEOUT = 600',
                         '# EXPECTED_RETURN = 0',
                         '# CONCURRENT = True',
                         '# NFS = True',
                         '# PR_END']
    test_dict = {'ROOT_ACCESS': False,
                 'TIMEOUT': 600,
                 'EXPECTED_RETURN': 0,
                 'CONCURRENT': True,
                 'NFS': True}
    results = self.one_parser.ParseList(test_config_lines, False)
    self.assertEqual(results, test_dict)

  def testNoDefinition(self):
    """No config definition, empty dictionary should be returned.

    An empty definition is passed in and the output should be an empty
    dictionary if populating default is False.
    """
    test_config_lines = []
    test_dict = {}
    results = self.one_parser.ParseList(test_config_lines, False)
    self.assertEqual(results, test_dict)

  def testWrongFormat(self):
    """Missing the PR_END line, ValueError should be raised."""
    test_config_lines = ['# PR_START',
                         '# ROOT_ACCESS = False',
                         '# TIMEOUT = 600',
                         '# EXPECTED_RETURN = 0',
                         '# CONCURRENT = True',
                         '# NFS = True']
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)

  def testPartialConfig(self):
    """Not all keys are defined, only partial populated dictionary returned.

    If populate default is set to False, only those defined keys should be
    populated.
    """
    test_config_lines = ['# PR_START',
                         '# ROOT_ACCESS = False',
                         '# TIMEOUT = 600',
                         '# NFS = True',
                         '# PR_END']
    test_dict = {'ROOT_ACCESS': False,
                 'TIMEOUT': 600,
                 'NFS': True}
    results = self.one_parser.ParseList(test_config_lines, False)
    self.assertEqual(results, test_dict)

  def testDefaultConfig(self):
    """An empty section of config definition, default config returned if asked.

    Populate default is set to true, so a dictionary with all default setting
    should be returned
    """
    test_config_lines = []
    results = self.one_parser.ParseList(test_config_lines, True)
    self.assertEqual(results, DEFAULT_DICT)
    
  def testSuiteConfigTakeOverTestConfig(self):
    """Suite Configuration overwrites file configuration."""
    temp_file_system = {
        '/tmp/source/test1.sh': ['# PR_START\n',
                                 '# TIMEOUT = "1000"\n',
                                 '# PR_END\n',
                                ],
        '/tmp/source/config_suite.suite': ['# PR_START\n',
                                           '# TIMEOUT = "3600"\n',
                                           '# PR_END\n',
                                          ],
        }
    self._PopulateFileSystem(temp_file_system)
    results = self.one_parser.ParseSuite('/tmp/source/config_suite.suite',
                                         ['/tmp/source/test1.sh',
                                         ])
    test_dict = self.one_parser.Default()
    test_dict['TEST_SCRIPT'] = '/tmp/source/test1.sh'
    test_dict['TIMEOUT'] = 3600
    self.assertEqual(results[0], test_dict)

  def testTestConfigTakeOverDefault(self):
    """Suite Configuration overwrites file configuration."""
    temp_file_system = {
        '/tmp/source/test1.sh': ['# PR_START\n',
                                 '# TIMEOUT = "1000"\n',
                                 '# PR_END\n',
                                ],
        '/tmp/source/config_suite.suite': ['# PR_START\n',
                                           '# PR_END\n',
                                          ],
        }
    self._PopulateFileSystem(temp_file_system)
    results = self.one_parser.ParseSuite('/tmp/source/config_suite.suite',
                                         ['/tmp/source/test1.sh'])
    test_dict = self.one_parser.Default()
    test_dict['TEST_SCRIPT'] = '/tmp/source/test1.sh'
    test_dict['TIMEOUT'] = 1000
    self.assertEqual(results[0], test_dict)

  def testParfileConfigPopulatedWithDefault(self):
    """A par file should be populated with default config info."""
    temp_file_system = {
        '/tmp/source/test1.par': ['# PR_START\n',
                                  '# TIMEOUT = "1000"\n',
                                  '# PR_END\n',
                                 ],
        }
    self._PopulateFileSystem(temp_file_system)
    result = self.one_parser.ParseFile('/tmp/source/test1.par')
    self.assertEqual(result['TEST_SCRIPT'], '/tmp/source/test1.par')
    result['TEST_SCRIPT'] = ''
    self.assertEqual(result, DEFAULT_DICT)
    
  def testErrorWrapping(self):
    """Errors are wrapped with more info and be kept thrown out."""
    temp_file_system = {'/tmp/source/test1.sh': ['# PR_START\n',
                                                 '# TIMEOUT = "1o"\n'
                                                 '# PR_END\n',
                                                ]
                       }
    self._PopulateFileSystem(temp_file_system)
    self.assertRaises(ValueError,
                      self.one_parser.ParseFiles,
                      ['/tmp/source/test1.sh'],
                      False)

  def testInvalidInteger(self):
    """Invalid integer cast for TIMEOUT and EXPECTED_RETURN."""
    test_config_lines = ['# PR_START',
                         '# TIMEOUT = 10s',
                         '# PR_END',
                        ]
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)

    test_config_lines = ['# PR_START',
                         '# EXPECTED_RETURN = "-1s"',
                         '# PR_END'
                        ]
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)

  def testInvalidBoolean(self):
    """Invalid boolean cast for CONCURRENT, NFS, ROOT_ACCESS."""
    test_config_lines = ['# PR_START',
                         '# CONCURRENT = nottrue',
                         '# PR_END',
                        ]
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)

    test_config_lines = ['# PR_START',
                         '# NFS = "nottrue"',
                         '# PR_END'
                        ]
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)

    test_config_lines = ['# PR_START',
                         '# ROOT_ACCESS = "nottrue"',
                         '# PR_END'
                        ]
    self.assertRaises(ValueError,
                      self.one_parser.ParseList,
                      test_config_lines,
                      False)


if __name__ == '__main__':
  unittest.main()
