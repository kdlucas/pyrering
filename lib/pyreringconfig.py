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

"""A module to control the application global properties.

This module will manage a singleton object for the PyreRing global
properties. These properties include: root_dir, testdatabase etc.
These properties are stored as a dictionary which is referred through a global
variable and managed by some module level methods in this module.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import getpass
import os
import time

from lib import filesystemhandlerextend


# Runtime configuration keys, user can't overwrite through config file.
NON_OVERWRITTEN_KEYS = ['time', 'tester', 'host_name']


class PyreRingConfig(object):
  """A class to store PyreRing runtime config info in a dict.

  This class is used to manage the pyrering related configuration data
  and it will have a dictionary to hold them and pushed to global. It should be
  maintained as a single instance.
  During the whole test run, this is the only one copy of the properties.
  It will contain a dictionary with key value pairs from the config file and
  some extra items generated automatically, namely:

  Automatically set by PyreRing, not user configurable:
    root_dir: PyreRing root directory.
              PyreRing automatically discovers it.
    host_name: The machine name PyreRing is running on.
               PyreRing automatically discovers it.
    tester: The user account PyreRing is running as.
            PyreRing automatically discovers it.
    time: The time string identifies the pyrering was started.
          PyreRing automatically discovers it.

  Managed by config file only, not through command line:
    log_level: The logging level as defined in Python logging module.
               default value is INFO
    skip_setup: If True, PyreRing will skip user setup suite.
                default value is False.
    header_file: User specified report header file which will be insert into
                 PyreRing report.
                 default value is <root_dir>/header_info.txt
    FATAL_STRING: a string contains comma separated substrings. If any
                  substring is found in the test output, the test will fail,
                  regardless of the return code of the test.
    default_suite: The name of default test suite, not currently used.
                   No default value.

  Managed by config file and user can overwrite through command line options:
    report_dir: the PyreRing report and log directory.
                default value <root_dir>/reports/
    conf_file: the name of PyreRing config file with path. If a non_absolute
               path provided, the actual value will be os.path.join(ed) with
               '<root_dir>/conf'
               default name is pyrering.conf
    project_name: The name of a project PyreRing will test on.
    sendmail: a boolean value if PyreRing should send out email report or not.
              default value is False. Note: there will be no email if all test
              passed regardless of this flag.
    email_recipients: comma separated email addresses as email recipients.
                      default value is the same as tester.
    log_file: the name of the log file. If a non_absulte path provided, the
              the actual value will be os.path.join(ed) with
              '<root_dir>/report'
              default name is pyrering.log
    reset: a boolean value user sets from the command line. If true, the run
           time configuration will replace existing configuration file. It has
           no effect in the conf file.
  """

  def __init__(self,
               filesystem=filesystemhandlerextend.FileSystemHandlerExtend()):
    self.settings = {}
    self.filesystem = filesystem

  def _CreateConfig(self):
    """Create a config file based on user config plus default config.
    
    This method should create a new config file using some runtime information.
  
    Returns:
      None. The constructed info write to conf_file
    """
    key_list = sorted(self.settings.keys())
    output = ''.join(['%s=%s\n' % (key, self.settings[key])
                      for key in key_list])
    self.filesystem.WriteToFile(self.settings['conf_file'], output)
    print """
***********Attention Please***************************
Either no configuration file was found at: %s
Or a reset option was issued.
Creating a default configuration file.
User can edit it later to change default values at: %s.
******************************************************
    """ % (self.settings['conf_file'], self.settings['conf_file'])
    
  def _ReadConfig(self):
    """Convert the conf_file to a dictionary.
  
    Returns:
      a dictionary with key value pairs from the conf file.
    """
    settings = {}
    conf_handler = self.filesystem.FileOpenForRead(self.settings['conf_file'])
    for line in conf_handler:
      line = line.strip()
      if (not line) or line.startswith('#') or (not '=' in line):
        continue
      key, value = line.split('=', 1)
      # make it java.util.Properties like property reader.
      # so I have to strip the quotes around the values
      key = key.strip()
      value = value.strip(' \t\r\'"')
      # sendmail, reset and skip_setup should be treated as boolean values,
      # others are treated as strings.
      if key in ['sendmail', 'reset', 'skip_setup']:
        settings[key] = (value.lower().startswith('true') or
                         value.startswith('1'))
      else:
        settings[key] = value
    conf_handler.close()
    # Remove the config we don't need. Most likely they will be generated on the
    # runtime.
    for key in NON_OVERWRITTEN_KEYS:
      settings.pop(key, None)
    return settings
  
  def _AddDefaultConfig(self, pyrering_root):
    """Populate the settings dictionary with default values.
    
    This method will provide a base configuration dictionary for PyreRing.

    Args:
      pyrering_root: path refer to the pyrering root dir.

    Returns:
      None.
    """
    self.settings.update({
        'root_dir': pyrering_root,
        'report_dir': self.filesystem.PathJoin(pyrering_root, 'reports'),
        'conf_file': self.filesystem.PathJoin(pyrering_root,
                                              'conf',
                                              'pyrering.conf'),
        'host_name': self.filesystem.GetHostName(),
        'tester': getpass.getuser(),
        'project_name': '<YOUR PROJECT NAME>',
        'default_suite': 'default_suite',
        'source_dir': '<YOUR TEST SCRIPT TOP DIRECTORY>',
        'sendmail': False,
        'email_recipients': getpass.getuser(),
        'log_file': 'pyrering.log',
        'reset': False,
        'runner': 'baserunner',
        'FATAL_STRING': '',
        'header_file': 'header_info.txt',
        'skip_setup': False,
        'log_level': 'INFO',
        # A timestamp string to identify the time pyrering is started.
        # The format should be yyymmddHHMM
        'time': time.strftime('%Y%m%d%H%M'),
        })

  def Populate(self, pyrering_root, user_settings):
    """Populate settings dictionary.
    
    If the conf file exist, it will use user settings update conf file
    settings and update default settings.
    If the conf file doesn't exist, it will user user settings update default
    settings and export as conf file.

    Args:
      pyrering_root: the path of the project root
      user_settings: user settings dictionary

    Returns:
      None. self.settings will have the effective values.
    """
    pyrering_root = self.filesystem.FindAbsPath(pyrering_root)
    # If config file is not set in the user arguments, use the default one:
    # '<pyrering_root>/conf/pyrering.conf' to populate the default
    # dictionary. Create the directory if it doesn't exist.
    if not user_settings.get('conf_file', None):
      conf_path = self.filesystem.PathJoin(pyrering_root, 'conf')
    else:
      conf_path = os.path.dirname(user_settings.get('conf_file'))
    if not self.filesystem.CheckDir(conf_path):
      self.filesystem.MkDir(conf_path)

    self._AddDefaultConfig(pyrering_root)
    self.settings.update(user_settings)

    # if the conf_file exists, read it, else populate the conf file and inform
    # user to examine.
    if (not user_settings.get('reset', False) and
        self.filesystem.CheckFile(self.settings['conf_file'])):
      # The user_settings coming from the command line will update  the
      # config file settings.
      read_conf_dict = self._ReadConfig()
      read_conf_dict.update(user_settings)
      self.settings.update(read_conf_dict)
    else:
      self._CreateConfig()

    # If after all this settings, the source_dir is still not set, we will
    # temporarily set it as current dir to let user run script from current
    # directory.
    if self.settings['source_dir'] == '<YOUR TEST SCRIPT TOP DIRECTORY>':
      self.settings['source_dir'] = self.filesystem.FindAbsPath('.')


# The GlobalPyreRingConfig should be one and only instance in the PyreRing
# life cycle.
GlobalPyreRingConfig = PyreRingConfig()


def Init(pyrering_root, user_settings):
  """Get settings populated.

  This method will check if settings still empty means it is never initialized,
  then it calls populate to populate the settings for use.

  Args:
    pyrering_root: the path of the root dir of pyrering.py file
    user_settings: a dictionary populated with settings.

  Returns:
    None.
  """
  if not GlobalPyreRingConfig.settings.keys():
    GlobalPyreRingConfig.Populate(pyrering_root, user_settings)
  return


def Update(new_settings):
  """Update the settings with new values."""
  GlobalPyreRingConfig.settings.update(new_settings)


def Reset():
  """Clean up the contents of settings."""
  GlobalPyreRingConfig.settings.clear()
