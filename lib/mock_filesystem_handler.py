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
#
# Author: mwu@google.com (Mingyu Wu)

__author__ = 'springer@google.com (Matthew Springer)'

import os
import shutil
import subprocess
import StringIO
import re

from lib import filesystem_handler


class MockFileSystemHandler(filesystem_handler.FileSystemHandler):
  """A mock file system abstraction class with built-in misbehavior."""

  SEP = os.sep  # a stand-in for os.sep

  def __init__(self):
    self.anticipated_shell_commands = {}
    self.fake_shell_command_log = []
    self.fake_env_vars = {'USER': 'prebuild',
                          'HOSTNAME' :'fake_workstation.corp.google.com',
                          'PWD' : '/fake/working/dir'}
    self.fake_files = {}
    # In full misbehave mode, we throw an exception of some sort.
    self.full_misbehave_mode = False
    # In partial misbehave mode, we just return a failure code.
    self.partial_misbehave_mode = False
    # In timeout_misbehave_mode, return None (indicating timeout) and no stdout.
    self.timeout_misbehave_mode = False
    self.expected_stdout_output = ['fake_stdout_line1\n', 'fake_stdout_line2\n']
    self.expected_stderr_output = None

  def __del__(self):
    """Makes sure all out StringIO buffers are closed."""
    for buff in self.fake_files.values():
      if not buff.closed:
        buff.close()

  def SetExpectedCommandOutput(self, command, retcode, stdout, stderr = None,
                               misbehave = False):
    """If we have a command we expect, we can set a "triggered response" to
    just that one command.
    """
    self.anticipated_shell_commands[command] = (retcode, stdout, stderr,
                                                misbehave)

  def SetShellStdout(self, shell_lines):
    self.expected_stdout_output = shell_lines

  def SetShellStderr(self, shell_lines):
    self.expected_stderr_output = shell_lines

  def RunCommandFG(self, command, combine_stdout_stderr = True):
    self.fake_shell_command_log.append(command)
    if self.full_misbehave_mode:
      raise self.ScriptError('Fake error message')

    retcode, stdout, stderr, misbehave = self.anticipated_shell_commands.get(
        command, (0, self.expected_stdout_output, self.expected_stderr_output,
                  self.partial_misbehave_mode))
    if misbehave:
      retcode = 1

    if stdout is not None:
      fake_stdout_stream = StringIO.StringIO()
      fake_stdout_stream.writelines(stdout)
      fake_stdout_stream.seek(0)
    else:
      fake_stdout_stream = None

    if combine_stdout_stderr:
      fake_stderr_stream = None
      if stderr is not None:
        fake_stdout_stream.seek(0, 2)  # Go to the end of the output
        fake_stdout_stream.writelines(stderr)
        fake_stdout_stream.seek(0)
    else:
      fake_stderr_stream = StringIO.StringIO()
      if stderr is not None:
        fake_stderr_stream.writelines(stderr)
      fake_stderr_stream.seek(0)

    return retcode, fake_stdout_stream, fake_stderr_stream

  def RunCommandFGWithTimeout(self, command, timeout = 60,
                              combine_stdout_stderr = True):
    """We implement timeout as a return code of None in filesystem_handler.
    To simulate a timeout, we return None and an empty "file".
    """
    if self.timeout_misbehave_mode:
      if combine_stdout_stderr:
        return None, self.FileOpen('/dev/null', 'r'), None
      else:
        return (None, self.FileOpen('/dev/null', 'r'),
                self.FileOpen('/dev/null', 'r'))

    return self.RunCommandFG(command, combine_stdout_stderr)

  def RunCommandFGToPipe(self, command, pipe_out, pipe_err = subprocess.STDOUT):
    """In this case if the external command already has an open file, we
    can just let them write to it, so in this case we write our pre-expected
    stdout to their file handle.
    """
    ret_code, out, err = self.RunCommandFG(command,
                                           pipe_err == subprocess.STDOUT)
    pipe_out.writelines(out.readlines())
    if err:
      if pipe_err == subprocess.STDOUT:
        pipe_out.writelines(err.readlines())
      else:
        pipe_err.writelines(err.readlines())
    return ret_code

  def RunCommandFGToPipeWithTimeout(self, command, pipe_out,
                                    pipe_err = subprocess.STDOUT, timeout = 60,
                                    env = None):
    if self.timeout_misbehave_mode:
      return None
    return self.RunCommandFGToPipe(command, pipe_out, pipe_err)

  def LookupEnvVariable(self, variable):
    self.fake_shell_command_log.append('Lookup [%s]' % variable)
    return self.fake_env_vars[variable]

  def SetEnvVariable(self, variable, value):
    self.fake_shell_command_log.append(
                                   'Set var [%s] to [%s]' % (variable, value))
    self.fake_env_vars[variable] = value

  def ChDir(self, path):
    """Equivalent to os.chdir."""
    self.fake_shell_command_log.append('Chdir to [%s]' % path)
    return None

  def MkDir(self, path, permission_mode = 0775):
    """Equivalent to os.mkdirs.

    The mock version will make an empty file with the name "the/path/", but it
    won't automatically make parent directories like "the/".
    """
    if path in ['.', '']:
      return None
    self.fake_shell_command_log.append('mkdir %s' % path)
    if not path.endswith(self.SEP):
      path += self.SEP
    # Touch the "file" to mark the directory.
    self.fake_files[path] = self.FileOpen(path)
    self.FileClose(self.fake_files[path])
    return None

  def ListDir(self, path):
    """Equivalent to os.listdir.  In the mock case, this is fairly limited."""
    self.fake_shell_command_log.append('ls %s' % path)
    # Be semi-intelligent about leading "."
    for pattern in r'^.' + self.SEP, r'^.$':
      path, number = re.subn(pattern, '', path)
    if path != "" and not path.endswith(self.SEP):
      path += self.SEP
    files = []
    for file_name in self.fake_files:
      # Show files like path/a_file and path/a_sub_dir/ but don't show files
      # like path/a_sub_dir/a_sub_sub_dir.
      if (file_name.startswith(path) and file_name != path and
          not re.search(r'%s[^%s]' % (self.SEP, self.SEP),
                        file_name[len(path):])):
        # Take off the trailing slash if it is a directory
        if file_name.endswith(self.SEP):
          file_name = file_name[0:-len(self.SEP)]
        # Remove directory prefix and emit file.
        files.append(file_name[len(path):])
    return files

  def RmFile(self, path):
    """TODO(springer): Figure out if this should really throw an OSError if the
    file is not present in our fake filesystem by default.
    """
    if self.full_misbehave_mode:
      raise OSError('Fake error trying to delete file [%s]' % path)

    self.fake_shell_command_log.append('rm %s' % path)
    if path in self.fake_files:
      if not self.fake_files[path].closed:
        self.fake_files[path].close()
      del self.fake_files[path]

  def RmTree(self, path):
    """Recursively and forcible remove path."""
    for file_name in self.fake_files.keys():
      if file_name.startswith(path):
        if not self.fake_files[file_name].closed:
          self.fake_files[file_name].close()
        del self.fake_files[file_name]

  def CheckFile(self, path):
    """Checks for file existence."""
    return self.fake_files.has_key(path)

  def CheckDir(self, path):
    """Checks if the given path is a directory."""
    if path in ['.', '']:
      return True
    if not path.endswith(self.SEP):
      path += self.SEP
    return self.fake_files.has_key(path)

  def SymLink(self, path, link_name):
    """Checks for file existence.  We currently handle symlinks by making a fake
    file and putting the token "symlink" in it.
    """
    self.fake_shell_command_log.append('ln -s %s->%s' % (link_name, path))
    self.WriteToFile(link_name, 'symlink -> %s\n' % path)
    return True

  def ReadLink(self, path):
    """Returns the path linked to by path."""
    output = self.FileOpen(path, 'r').readline().strip()
    if not output.startswith('symlink -> '):
      raise OSError('Invalid argument: \'%s\'' % path)
    return output[len('symlink -> '):]

  def _FileWrite(self, path, output, mode = 'w'):
    if (mode == 'a') and (path in self.fake_files):
      file_h = self.fake_files[path]
      file_h.seek(0, 2) # To actually append, find the end of the file.
    else:
      self.fake_files[path] = self.FileOpen(path, mode)
    self.fake_files[path].writelines(output)
    # In the real fielsystem handler, we'd actually close the file here, but
    # with a StringIO object, we loose the data if we close the last ref. So
    # instead, we just seek back to the beginning.
    self.fake_files[path].seek(0)

  def FileOpenForRead(self, path):
    """Returns an open file handle."""
    return self.FileOpen(path, 'r')

  def FileOpen(self, path, mode = 'w'):
    if self.full_misbehave_mode:
      raise OSError('Fake error trying to open file [%s]' % path)

    if (mode == 'r') and (path in self.fake_files):
      file_h = self.fake_files[path]
      file_h.seek(0)
      return file_h

    if (mode == 'a') and (path in self.fake_files):
      file_h = self.fake_files[path]
      file_h.seek(0, 2)
      return file_h

    # Case where we've never seen this file before or we're writing.
    # Give 'em a blank file.
    file_h = StringIO.StringIO()
    self.fake_files[path] = file_h
    file_h.name = path
    return file_h

  def FileClose(self, file_h):
    # We don't actually close files since we're using StringIO bufs and we want
    # to read from them later.
    assert isinstance(file_h, StringIO.StringIO)
    file_h.seek(0)

  def PrintLogs(self):
    """Debug print command to dump the logs."""
    print self.fake_shell_command_log
    for path in self.fake_files.keys():
      if not self.fake_files[path].closed:
        self.fake_files[path].seek(0)
      print 'File[%s]' % path
      print '-----------------------'
      for line in self.fake_files[path].readlines():
        print line,
      print 'EOF'
