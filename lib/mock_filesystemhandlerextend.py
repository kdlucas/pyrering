#!/usr/bin/python2.4
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

"""This is an extended mock_filesystemhandler from Matt's FileSystemHandler.

I need some more functions which aren't included in Matt's original code.
So I extended them by myself. This is mock part.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import os
import re

from lib import mock_filesystem_handler


class MockFileSystemHandlerExtend(
    mock_filesystem_handler.MockFileSystemHandler):
  """Extended new methods from MockFileSystemHandler.

  The original MockFilesystemHandler missing some methods I need. So I extended
  it.
  """

  def __init__(self):
    """Added a list for Walk in the class.

    Tester has to populate the list before he really uses it.
    """
    mock_filesystem_handler.MockFileSystemHandler.__init__(self)

    # this is used to pre-cook a return value for os.walk()
    self.walk_list = []
    
  def CheckDir(self, path):
    """Check if the given path is an existing dir against fake_files dict.
    
    Args:
      path: the path to check
      
    Returns:
      True if the given path exists in the fake_files dict
    """
    for key in self.fake_files.iterkeys():
      if os.path.split(key)[0].startswith(path):
        return True
    return False
  
  def LookupEnvVariableWithDefault(self, var, value):
    """Mock an environ variable lookup with default value."""
    return self.fake_env_vars.get(var, value)

  def Glob(self, path):
    """A simple pattern match if the path match any file/dir in fake_files.
    
    Args:
      path: a pattern of path
      
    Returns:
      a list of all files if its body match the pattern given
    """
    pattern_path = path.replace('*', '[^/]*').replace('?', '[^/]')
    pattern = re.compile(pattern_path)
    return [key for key in self.fake_files.iterkeys() if pattern.match(key)]
  
  def Walk(self, unused_path, topdown=True):
    """Returns a pre-cooked os.walk like list, no matter what path is given.

    To call this mock, user has to prepare the expected return value first and
    saves it at self.walk_list, since the return will be self.walk_list no
    matter what the input path is. It is an empty list as default.
    If you have many pathes to walk, you will have to extend this method
    and return different values for different paths.
    
    Args:
      unused_path: a path to walk, not actually used.
      topdown: it will return the pre-cooked walk list in order or reverse
        based on the boolean value. Default is True means in order.

    Returns:
      the pre-cooked list self.walk_list.
    """
    if topdown:
      return self.walk_list
    else:
      return self.walk_list.reverse()

  def GetHostName(self):
    """Mock socket.gethostname()."""
    return self.fake_env_vars['HOSTNAME']

  def FindAbsPath(self, relative_path):
    """Not a really mock, just a wrapper.

    I might mock it later. Currently just moved this out of the mock code, sine
    I don't have dependency on os module in my main code.

    Args:
      relative_path: a string of path to map.

    Returns:
      an abs path as returned by os.path.abspath.
    """
    return os.path.abspath(relative_path)
