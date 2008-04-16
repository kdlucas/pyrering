#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""Unittest for pyreringconfig."""

__author__ = 'mwu@google.com (Mingyu Wu)'

import getpass
import unittest

from lib import mock_filesystemhandlerextend
from lib import pyreringconfig


class PyreRingConfigTest(unittest.TestCase):
  """Unit test cases for PowrRingConfigClass.

  This will only test the PyreRingConfig class, those module level methods are
  not tested currently.
  """

  def setUp(self):
    """Create a mock filesystem and init PyreRingConfig with it."""
    self.filesystem = (
        mock_filesystemhandlerextend.MockFileSystemHandlerExtend())
    self.filesystem.fake_env_vars['HOSTNAME'] = 'fake_machine'

    self.settings = pyreringconfig.PyreRingConfig(self.filesystem)

  def _PopulateFileSystem(self, temp_file_system):
    """Assistant method to populate mock file system with a dict."""
    for key, value in temp_file_system.iteritems():
      self.filesystem.WriteToFile(key, value)

  def testEmptySettingsAfterInit(self):
    """As default the settings dict should be created and empty."""
    self.assertEqual(len(self.settings.settings), 0)

  def testCreateConfFileIfNotExist(self):
    """Test conf file should be created if not exist."""
    temp_file_system = {
        '/tmp/placeholder': ''
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp/', {})
    self.assertTrue(self.filesystem.CheckFile('/tmp/conf/pyrering.conf'))

  def testDefaultSettings(self):
    """test default values for settings if nothing specified."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ''
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp/', {})
    self.assertEqual(self.settings.settings['root_dir'], '/tmp')
    self.assertEqual(self.settings.settings['report_dir'],
                     '/tmp/reports')
    self.assertEqual(self.settings.settings['conf_file'],
                     '/tmp/conf/pyrering.conf')
    self.assertEqual(self.settings.settings['host_name'], 'fake_machine')
    self.assertEqual(self.settings.settings['tester'], getpass.getuser())
    self.assertEqual(self.settings.settings['project_name'],
                     '<YOUR PROJECT NAME>')
    self.assertEqual(self.settings.settings['default_suite'], 'default_suite')
    # Due to the limitation of current mock_filesystem. This value can't be
    # tested. The test will set source_dir to current path. But I haven't mock
    # the os.path.abspath yet. I can't get a predictable value to test. It will
    # change based on the current location to run pyrering.
    #self.assertEqual(self.settings.settings['source_dir'],
    #                 '<YOUR TEST SCRIPT TOP DIRECTORY>')
    self.assertFalse(self.settings.settings['sendmail'])
    self.assertEqual(self.settings.settings['email_recipients'],
                     getpass.getuser())
    self.assertEqual(self.settings.settings['log_file'], 'pyrering.log')
    self.assertFalse(self.settings.settings['reset'])
    self.assertEqual(self.settings.settings['runner'], 'baserunner')
    self.assertEqual(self.settings.settings['FATAL_STRING'], '')
    self.assertEqual(self.settings.settings['header_file'], 'header_info.txt')
    self.assertFalse(self.settings.settings['skip_setup'])

  def testFileSettingsOverWriteDefaultSettings(self):
    """Config file take over default values."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['source_dir = "/tmp/source_dir"\n',
                                     'project_name = "unittest project"\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertEqual(self.settings.settings['source_dir'], '/tmp/source_dir')
    self.assertEqual(self.settings.settings['project_name'],
                     'unittest project')

  def testUserSettingsOverWriteDefaultSettings(self):
    """User settings take over all other settings."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['source_dir = "/tmp/source_dir"\n',
                                     'project_name = "unittest project"\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    user_settings = {'project_name': 'user_name'}
    self.settings.Populate('/tmp', user_settings)
    self.assertEqual(self.settings.settings['project_name'], 'user_name')

  def testConfigFileUnOverWriteableConfig(self):
    """Config file can't take over 'host_name' and 'tester' values.

    'host_name' and 'tester' values are gathered at run time. It can't be taken
    over by config file. Another string not tested here 'time'. It is not
    actually used yet.
    """
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['host_name = "nonexist"\n',
                                     'tester = "nonuser"\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertEqual(self.settings.settings['host_name'], 'fake_machine')
    self.assertEqual(self.settings.settings['tester'], getpass.getuser())

  def testUserSettingsOverWriteUnOverWriteableConfig(self):
    """User settings over write anything.
    
    Including those not overwriteable settings by config file.
    """
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['host_name = "nonexist"\n',
                                     'tester = "nonuser"\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    user_settings = {'host_name': 'user_host', 'tester': 'user_tester'}
    self.settings.Populate('/tmp', user_settings)
    self.assertEqual(self.settings.settings['host_name'], 'user_host')
    self.assertEqual(self.settings.settings['tester'], 'user_tester')

  def testSomeStringsTreatedAsBooleanTrue(self):
    """sendmail and reset should be treated as boolean correctly."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['sendmail = True\n',
                                     'reset = True\n',
                                     'skip_setup = True\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertTrue(self.settings.settings['sendmail'])
    self.assertTrue(self.settings.settings['reset'])
    self.assertTrue(self.settings.settings['skip_setup'])

  def testOneTreatedAsBooleanTrue(self):
    """sendmail and reset should be treated as boolean correctly."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['sendmail = 1\n',
                                     'reset = 1\n',
                                     'skip_setup = 1\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertTrue(self.settings.settings['sendmail'])
    self.assertTrue(self.settings.settings['reset'])
    self.assertTrue(self.settings.settings['skip_setup'])

  def testSomeStringsTreatedAsBooleanFalse(self):
    """sendmail and reset should be treated as boolean correctly."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['sendmail = False\n',
                                     'reset = False\n',
                                     'skip_setup = False\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertFalse(self.settings.settings['sendmail'])
    self.assertFalse(self.settings.settings['reset'])
    self.assertFalse(self.settings.settings['skip_setup'])

  def testZeroTreatedAsBooleanFalse(self):
    """sendmail and reset should be treated as boolean correctly."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/conf/pyrering.conf': ['sendmail = 0\n',
                                     'reset = 0\n',
                                     'skip_setup = 0\n',
                                    ]
        }
    self._PopulateFileSystem(temp_file_system)
    self.settings.Populate('/tmp', {})
    self.assertFalse(self.settings.settings['sendmail'])
    self.assertFalse(self.settings.settings['reset'])
    self.assertFalse(self.settings.settings['skip_setup'])

  def testUserCanSpecifyConfigFile(self):
    """User can use nondefault config file."""
    temp_file_system = {
        '/tmp/placeholder': '',
        '/tmp/newconfig/pyrering_new.conf': ['project_name = my_project']
        }
    self._PopulateFileSystem(temp_file_system)
    user_settings = {'conf_file': '/tmp/newconfig/pyrering_new.conf'}
    self.settings.Populate('/tmp', user_settings)
    self.assertEqual(self.settings.settings['project_name'], 'my_project')


if __name__ == '__main__':
  unittest.main()
