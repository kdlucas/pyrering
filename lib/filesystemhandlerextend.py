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

"""This is an extended filesystemhandler from Matt's FileSystemHandler.

I need some more functions which doesn't included in Matt's original code, so I
added them here.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import errno
import fcntl
import glob
import logging
import os
import signal
import socket
import subprocess
import time

from lib import common_util
from lib import filesystem_handler

logger = logging.getLogger('PyreRing')
DEBUG = common_util.DebugLog


class FileSystemHandlerExtend(filesystem_handler.FileSystemHandler):
  """Extends original FileSystemHandler."""

  def __init__(self):
    """Just to overwrite the original init from FileSystemHandler.
    
    In the original FileSystemHandler, the init method will set os.umask. But
    for this usage in the PyreRing, we would like to keep umask as whatever it
    is. So I overwrite it here it just skip the changing of umask on the
    system.
    """
    pass

  def LookupEnvVariableWithDefault(self, var, value):
    """Calls os.environ.get to get env variable."""
    return os.environ.get(var, value)

  def Glob(self, pattern):
    """Calls glob.glob directly."""
    return glob.glob(pattern)
    
  def Walk(self, path, topdown=True):
    """Calls os.walk directly."""
    return os.walk(path, topdown)

  def GetHostName(self):
    """Return the host name by socket.gethostname."""
    return socket.gethostname()

  def FindAbsPath(self, relative_path):
    """calls os.path.abspath directly."""
    return os.path.abspath(relative_path)
    
  def RunCommandFGToPipeWithTimeoutGetOutput(self, command, timeout=60):
    """Run command with a timeout."""
    return self._RunCmdInFGAndWait(command, subprocess.PIPE, subprocess.PIPE,
                                   timeout)

  def _ReadPipe(self, fd):
    """Read and clean the content of the given file handler.

    Because of the 4k Bytes limitation of the buffer size. The file handler
    needs to be read out as soon as possible. If the file handler is set to
    none blocking mode, the read operation will return as soon as the content
    is clean. As default file handler is set to blocking mode, so the read
    operation will block and wait till the file handler is closed.

    Args:
      fd: an opened file handler.

    Returns:
      The string message in the file handler. If nothing to read, an empty
      string will be returned.
    """
    message = ''
    bytes = ''
    # Loop reading, break when reach the end.
    while 1:
      try:
        bytes = fd.read(4096)
      except IOError, e:
        # When reaching the end of the fd, IOError with errno EAGAIN is raised,
        # which is expected, re-raise the exception if not EAGAIN.
        if e[0] != errno.EAGAIN:
          raise
        break
      if not bytes:
        break
      message += bytes
    return message

  @DEBUG
  def RunCommandToLoggerWithTimeout(self, command, timeout=600):
    """Open a subshell to run a command with a timeout and log the output.

    Same as RunCommandToPipeWithTimeout except the command output will be
    logged in logger, no pipe needed.

    Args:
      command: a shell command or script to run
      timeout: an integer for the timeout in seconds.

    Returns:
      a tuple with 2 values will be returned. The first one is the return code
      of the shell command run, None if it times out. The second one will be
      the shell command output pipe with both stdout and stderr.
    """
    output = ''
    mesg = ''
    start_time = 0
    proc = subprocess.Popen(command, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # It is very important to set the stdout to nonblocking mode. Otherwise
    # the code will block when it tries to read from the stdout pipe. fd.read()
    fcntl.fcntl(proc.stdout,
                fcntl.F_SETFL,
                fcntl.fcntl(proc.stdout, fcntl.F_GETFL)|os.O_NONBLOCK)
    p = proc.stdout
    # Wait for the timeout while need to clean up the proc.stdout buffer, so it
    # will not fill up for the 4k bytes limit.
    while start_time < timeout and proc.poll() is None:
      time.sleep(1)
      start_time += 1
      mesg = self._ReadPipe(p)
      if mesg:
        logger.info(mesg)
        output += mesg

    if proc.poll() is not None:
      # It is a normal exit
      mesg = self._ReadPipe(p)
      if mesg:
        logger.info(mesg)
        output += mesg
      return proc.wait(), output
    else:
      os.kill(proc.pid, signal.SIGKILL)
      logger.debug('exit %s.RunCommandToLoggerWithTimeout as kill' %
                   self.__class__)
      return None, output

  @DEBUG
  def RunCommandToPipeWithTimeout(self, log_pipe, command, timeout=600):
    """Open a subshell to run a command with a timeout option.

    This method is used to get run a script in a subshell without preexec_fn
    option set in subprocess. I have some problem with that option set. So I
    have to write a new one without that option. It will run shell script in a
    subshell and return the return code and a pipe with the output.

    Args:
      log_pipe: a file descriptor to write the output of the command to.
      command: a shell command or script to run
      timeout: an integer for the timeout in seconds.

    Returns:
      a tuple with 2 values will be returned. The first one is the return code
      of the shell command run, None if it times out. The second one will be
      the shell command output pipe with both stdout and stderr.
    
    Caveats:
      The pipe can only hold 4k byte chars in buffer as default. So the bugger
      must be cleaned up frequently. fcntl will set the buffer to none block
      mode, so reading the buffer will not block the process.
    """
    output = ''
    mesg = ''
    start_time = 0
    proc = subprocess.Popen(command, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # It is very important to set the stdout to nonblocking mode. Otherwise
    # the code will block when it tries to read from the stdout pipe. fd.read()
    fcntl.fcntl(proc.stdout,
                fcntl.F_SETFL,
                fcntl.fcntl(proc.stdout, fcntl.F_GETFL)|os.O_NONBLOCK)
    p = proc.stdout
    # Wait for the timeout while need to clean up the proc.stdout buffer, so it
    # will not fill up for the 4k bytes limit.
    while start_time < timeout and proc.poll() is None:
      time.sleep(1)
      start_time += 1
      mesg = self._ReadPipe(p)
      if mesg:
        log_pipe.write(mesg)
        log_pipe.flush()
        output += mesg

    if proc.poll() is not None:
      # it is a normal exit
      mesg = self._ReadPipe(p)
      log_pipe.write(mesg)
      log_pipe.flush()
      output += mesg
      return proc.wait(), output
    else:
      os.kill(proc.pid, signal.SIGKILL)
      return None, output
