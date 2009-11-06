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

"""A library for indirecting common filesystem operations and process calls.

This library's main purpose is to help isolate policy from procedure in I/O
heavy code to make it more easily testable.  It also has some basic support
for cleaning up external processes cleanly.  We also provide a companion mock
object (mock_filesystem_handler.py) to facilitate testing.
"""

__author__ = 'springer@google.com (Matthew Springer)'

import os
import select
import shutil
import signal
import StringIO
import subprocess
import sys
import time
import traceback
import types


def CommonStartingTokens(*token_lists):
  """Returns a list of common starting tokens.

  Args:
    token_lists: any number of lists of tokens

  Returns:
    the longest list of tokens that are the same in all lists
  """
  if token_lists:
    min_length = min([len(t) for t in token_lists])
    last_matching_token = -1
    mismatched = False
    for pos in xrange(min_length):
      reference_token = token_lists[0][pos]
      for tokenlist in token_lists[1:]:
        if reference_token != tokenlist[pos]:
          mismatched = True
          break
      if mismatched:
        break
      else:
        last_matching_token = pos

    results = token_lists[0][0:last_matching_token + 1]
  else:
    results = []
  return results


class FileSystemHandler(object):
  """An indirection class around underlying os services to make testing easier.

  This also insulates the upper levels of the build from knowing too much about
  the underlying operating system environment.
  """

  SEP = os.sep  # a stand-in for os.sep
  SIGTERM_TIMEOUT = 30  # time to wait for a process to die gracefully.

  class ScriptError(Exception):
    """Thrown when something goes wrong while running an external script."""

  def __init__(self):
    os.umask(022)

  ###### Some General Utilities (mostly so we can mock for testing) ######

  def RunCommandFG(self, command, combine_stdout_stderr = True):
    """Run a shell command in the foreground (ie. wait for completion).

    Args: command: a string containing the shell command.
          combine_stdout_stderr: When true, combine stdout and stderr
    Returns: a tuple of (exit_code, stdout, stderr), where stdout & stderr are
    file handles.
    """
    return self.RunCommandFGWithTimeout(command, -1, combine_stdout_stderr)

  def RunCommandFGToPipe(self, command, pipe_out, pipe_err = subprocess.STDOUT):
    """Run a shell command in the foreground (ie. wait for completion).

    Args: command: a string containing the shell command.
          pipe_out/err: an open file handler to redirect stdout/stderr.
                        When pipe_err = subprocess.STDOUT, stderr is redirected
                        to stdout.
    Returns: an exit code.
    """
    timeout_code, _, _ = self._RunCmdInFGAndWait(command, pipe_out, pipe_err,
                                                 -1)
    return timeout_code

  def RunCommandFGWithTimeout(self, command, timeout = 60,
                              combine_stdout_stderr = True):
    """Run a shell command in the forground (ie. wait for completion), but
    with a timeout specified in secs.

    Args:
      command: a string containing the shell command.
      timeout: an integer timeout value in seconds.
      combine_stdout_stderr: When true, combine stdout and stderr.
    Returns: a tuple of (timeout_code, stdout, stderr) where stdout/stderr are
             file handles.
             timeout_code is an integer equal to the return code or None if
             the process had to be killed by timeout.
    """
    if combine_stdout_stderr:
      stderr = subprocess.STDOUT
    else:
      stderr = subprocess.PIPE
    return self._RunCmdInFGAndWait(command, subprocess.PIPE, stderr, timeout)

  def RunCommandFGToPipeWithTimeout(self, command, pipe_out,
                                    pipe_err = subprocess.STDOUT, timeout = 60,
                                    env = None):
    """Run a shell command in the forground (ie. wait for completion), but
    with a timeout specified in secs.  Sends all the stdout and stderr to a
    caller supplied file handle.

    Args:
      command: a string containing the shell command.
      pipe_out/err: an open file handler to redirect stdout/stderr.
                    When pipe_err = subprocess.STDOUT, stderr is redirected
                    to stdout.
      timeout: an integer timeout value in seconds.
      env: a dictionary of exported values
    Returns: an integer exit code, None if the process timed out.
    """
    timeout_code, _, _ = self._RunCmdInFGAndWait(command, pipe_out,
                                                 pipe_err, timeout, env)
    return timeout_code

  def RunCommandBGToPipe(self, command, pipe_out, pipe_err = subprocess.STDOUT,
                         env = None):
    """Run a shell command in the background (ie. do not wait for completion),
    instead returns the process object of the command.

    Note that we do not support a timeout, we let the caller do that.

    Args:
      command: a string containing the shell command.
      pipe_out/err: an open file handler to redirect stdout/stderr.
                    When either is set to subprocess.PIPE and new pipe is made
                    in pipe.stdout/err.
                    When pipe_err = subprocess.STDOUT, stderr is redirected
                    to stdout.
      env: a dictionary of exported values
    Returns: a subprocess.Popen object which can be poll()ed or wait()ed on,
             os.waitpgid()ed, etc...
    """
    # Use external values when no environment dictionary is provided.
    if env is None:
      env = os.environ

    # Flush our various pipes since subprocess output will NOT cause previous
    # stuff in the buffer to flush.  This makes sure our output stays ordered in
    # the file.
    for pipe in [pipe_out, pipe_err]:
      if isinstance(pipe, types.FileType):
       pipe.flush()

    proc = subprocess.Popen(command, shell = True, close_fds = True,
                            preexec_fn = os.setpgrp,
                            stdout = pipe_out, stderr = pipe_err,
                            env = env)
    return proc

  def _RunCmdInFGAndWait(self, command, pipe_out, pipe_err, timeout,
                         env = None):
    """Helper function to handle command running and error handling.
    Use one of the other entry points above and not this function.
    """
    proc = self.RunCommandBGToPipe(command, pipe_out, pipe_err, env)
    should_read_output = (pipe_out == subprocess.PIPE or
                          pipe_err == subprocess.PIPE)
    try:
      return self._WaitOnProcessTimeout(proc, timeout, should_read_output)
    except OSError:
      err_msg = ('Exception [%s] on command [%s].\n\tSTACK TRACE:\n%s'
                 % (sys.exc_type, command, traceback.format_exc()))
      raise self.ScriptError(err_msg)

  def _WaitOnProcessTimeout(self, proc, timeout, should_read_output):
    """Takes a popen subprocess object and does the right thing for its
    timeout.  Kills a process that has hit timeout.  If the process responds,
    and if successfully killed, we return None.  If the process will not respond
    to SIGTERM, we send a SIGKILL.

    The only requirement is that any process object's children have to be in the
    same process group.  This is true for all run command functions defined
    above.

    Args:
      proc: a subprocess module Popen object
      timeout: an integer with any negative or zero value indicating do not
               timeout.
      should_read_output: When True, while waiting, also read the output to a
                          new buffer.
    Returns:
      A tuple of the (exit_code, stdout, stderr) where exit_code is the exit
      code of the process, with None indicating a timeout, and
      stdout/err are the output pipes of the object.  If should_read_output is
      True, then stdout/err are copied to a pre-loaded StringIO object.
    """
    if should_read_output:
      # Only create StringIO objects for those outputs we want to save.
      if proc.stdout:
        stdout_buffer = StringIO.StringIO()
      else:
        stdout_buffer = None
      if proc.stderr:
        stderr_buffer = StringIO.StringIO()
      else:
        stderr_buffer = None
      # Note that if we selected to combine stdout and stderr when we launched
      # the process, proc.stderr would be None.
      outputs_to_probe = [pipe for pipe in [proc.stdout, proc.stderr] if pipe]
    else:
      stdout_buffer = proc.stdout
      stderr_buffer = proc.stderr
      outputs_to_probe = []


    start_time = time.time()
    try:
      while ((proc.poll() is None) and
             (time.time() - start_time < timeout or timeout <= 0)):
        if should_read_output:
          # Probe for up to half a second to see if there is any new output
          results, _, _ = select.select(outputs_to_probe, [], [], 0.5)
          # Read out from any available pipe.  results is [] if timed out.
          for out_stream in results:
            if out_stream == proc.stdout:
              stdout_buffer.write(out_stream.readline())
            elif out_stream == proc.stderr:
              stderr_buffer.write(out_stream.readline())
        else:
          time.sleep(0.5)

      # Normal return case, we terminated OK.
      if proc.poll() is not None:
        return proc.wait(), stdout_buffer, stderr_buffer

      # If we're here, we timed out. Try asking the process to stop nicely.
      os.killpg(proc.pid, signal.SIGTERM)
      deadline = time.time() + self.SIGTERM_TIMEOUT
      while time.time() < deadline and proc.poll() is not None:
        time.sleep(1)

      if proc.poll() is None:
        # SIGTERM failed! Pull out the heavy guns.
        os.killpg(proc.pid, signal.SIGKILL)

      return None, stdout_buffer, stderr_buffer 

    finally:
      # In case we get an exception (typically a KeyboardException) while
      # waiting, just clean up.
      if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGKILL)
        time.sleep(0.1)
      elif should_read_output:
        # We know the process terminated, so it is safe to read all output.
        if proc.stdout:
          stdout_buffer.write(proc.stdout.read())
        if proc.stderr:
          stderr_buffer.write(proc.stderr.read())

      # So that the StringIO looks like a normal pipe, seek to the begining.
      if should_read_output:
        if stdout_buffer:
          stdout_buffer.seek(0)
        if stderr_buffer:
          stderr_buffer.seek(0)

  def ChDir(self, path):
    """Equivalent to os.chdir.  Only really provided so we can test. """
    return os.chdir(path)

  def MkDir(self, path, permission_mode = 0775):
    """By default directories should be global read/exec, largely because the
    contents of the logs need to be read by our .php scripts.  Unlike os.mkdir,
    this does not fail if the directory already exists.
    """
    if not os.access(path, os.F_OK):
      os.makedirs(path, permission_mode)

  def ListDir(self, path):
    """Equivalent to os.listdir."""
    return os.listdir(path)

  def RmFile(self, path):
    """Equivalent to rm."""
    return os.remove(path)

  def RmTree(self, path):
    """Recursively and forcible remove path."""
    # See http://docs.python.org/lib/module-shutil.html#l2h-2356
    return shutil.rmtree(path)

  def ChMod(self, path, permission_mode = 0444):
    """Equivalent to os.chmod."""
    return os.chmod(path, permission_mode )

  def CheckFile(self, path):
    """Checks for file existence."""
    return os.path.lexists(path)

  def CheckDir(self, path):
    """Checks if the given path is a directory."""
    return os.path.isdir(path)

  def PathJoin(self, *args):
    """Joins paths in a system appropriate way."""
    return os.path.join(*args)

  def SymLink(self, path, link_name):
    """Creates a symlink to the given path called link_name.  Note that python's
    os.symlink function is perhaps not entirely clear on what the arguments
    actually mean.  Path is where the symlink points, link_name is what the
    filename actually is.
    """
    assert not self.CheckFile(os.path.join(path, link_name))
    os.symlink(path, link_name)

  def ReadLink(self, path):
    """Returns the path linked to by path."""
    return os.readlink(path)

  def AbsPath(self, path):
    """Returns an absolute path name."""
    return os.path.abspath(path)

  def Basename(self, path):
    """Returns the basename part of a path name."""
    return os.path.basename(path)

  def GetCwd(self):
    """Returns the current working directory."""
    return os.getcwd()

  def IsAbs(self, path):
    """Returns True when the path is an absolute path name."""
    return os.path.isabs(path)

  def MakeOrMoveSymlink(self, source, target, link_name):
    """Creates a symbolic link from one directory to another.

    This will remove an old symlink from our base log directory (if it exists)
    and then (re)create it.  It also has logic to correctly figure out a minimum
    symlink distance for child, sibling and absolute directories.

    Caveats:
      - source and target must be existing directories

    Args:
      source: name of a source directory, will contain the link
      target: name of a destination directory
      link_name: the name used to link from source to target

    Raises:
      ScriptError: on invalid inputs
    """
    # Use absolute names to simplify the logic.
    absolute_source = self.AbsPath(source)
    absolute_target = self.AbsPath(target)

    # Check that the source and target are not the same.
    if absolute_source == absolute_target:
      raise self.ScriptError('cannot link a directory to itself: [%s]' %
                             absolute_source)

    # Determine if a relative path can be used.
    tokenized_source = absolute_source.split(self.SEP)
    tokenized_target = absolute_target.split(self.SEP)
    prefix_dirs = CommonStartingTokens(tokenized_source, tokenized_target)

    if prefix_dirs == tokenized_source:
      # The target is below us, use a relative path.
      symlink_target = self.SEP.join(tokenized_target[len(tokenized_source):])
    else:
      # Symlink is to something not below us, use an absolute path
      symlink_target = absolute_target

    # Changing the current working directory makes this a critical section
    # because we must restore the current working directory even when an error
    # is raised.
    save_cwd = self.GetCwd()
    try:
      self.ChDir(absolute_source)
      if self.CheckFile(link_name):
        self.RmFile(link_name)
      self.SymLink(symlink_target, link_name)
    finally:
      self.ChDir(save_cwd)

  def WriteToFile(self, path, output):
    """Writes to a file with writelines().  Will truncate any existing file.
    Args:
      path: a filename in a string
      output: an iterable object (like a list of strings or a file handle)
    Returns: None
    """
    self._FileWrite(path, output, 'w')

  def AppendToFile(self, path, output):
    """Write to a file, but appends.
    Args:
      path: a filename in a string
      output: an iterable object (like a list of strings or a file handle)
    Returns: None
    """
    self._FileWrite(path, output, 'a')

  def _FileWrite(self, path, output, mode = 'w'):
    file_h = self.FileOpen(path, mode)
    file_h.writelines(output)
    self.FileClose(file_h)

  def FileOpenForRead(self, path):
    """Returns an open file handle."""
    return open(path, 'r')

  def FileTouch(self, path):
    """Equivalent to the unix command "touch"."""
    self.FileClose(self.FileOpen(path, 'a'))

  def FileOpen(self, path, mode = 'w'):
    return open(path, mode)

  def FileClose(self, file_h):
    file_h.close()

  def LookupEnvVariable(self, variable):
    """Indirects the os env variable lookup so we can mock out the env lookups
    for testing purposes.
    """
    value = os.environ[variable]
    return value

  def SetEnvVariable(self, variable, value):
    """Indirects setting env variables.  This only affects our subshell, so all
    these settings will be lost once we exit.
    """
    os.environ[variable] = value

  def StdErrFileHandler(self):
    """Grabs a file handler that outputs to stderr."""
    return sys.stderr
