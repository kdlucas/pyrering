#!/usr/bin/python2.4
# Copyright 2007 Google Inc. All Rights Reserved
#

__author__ = 'springer@google.com (Matthew Springer)'

import shutil
import tempfile
import time
import unittest

from lib import filesystem_handler


class FileSystemHandlerTests(unittest.TestCase):
  """Tests our operating system abstraction layer.  Most of these functions are
  actually mocked in other unittests, we test enough here to make sure we are
  doing the interaction correctly when we need to for real.
  """

  def setUp(self):
    self.filesys = filesystem_handler.FileSystemHandler()
    self.filesys.SIGTERM_TIMEOUT = 1
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_tmpdir)

  def testRunCommandFGNoTimeout(self):
    """Test that we can actually run shell commands. Use mostly shell built-ins
    so we're not so dependent on what's actually installed.
    """
    ret_code, out, err = self.filesys.RunCommandFG('echo 1234')
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), ['1234\n'])

    ret_code, out, err = self.filesys.RunCommandFG('echo 1234 1>&2', True)
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), ['1234\n'])

    ret_code, out, err = self.filesys.RunCommandFG('echo 1234 1>&2', False)
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), [])
    self.assertEqual(err.readlines(), ['1234\n'])

    ret_code, out, err = self.filesys.RunCommandFG('/bin/false')
    self.assertEqual(ret_code, 1)
    self.assertEqual(out.readlines(), [])

  def testRunCommandFGWithTimeout(self):
    """Test that we can run shell commands with a timeout. Try cases that
    actually timeout as well as those that don't.
    """
    ret_code, out, err = self.filesys.RunCommandFGWithTimeout(
        'echo 1234', 1, False)
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), ['1234\n'])
    self.assertEqual(err.readlines(), [])

    ret_code, out, err = self.filesys.RunCommandFGWithTimeout(
        'echo 1234 1>&2', 1, False)
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), [])
    self.assertEqual(err.readlines(), ['1234\n'])

    ret_code, out, err,  = self.filesys.RunCommandFGWithTimeout('/bin/false', 1)
    self.assertEqual(ret_code, 1)
    self.assertEqual(out.readlines(), [])

    # Now try things that actually take time.
    ret_code, out, err = self.filesys.RunCommandFGWithTimeout('sleep 2', 3)
    self.assertEqual(ret_code, 0)
    self.assertEqual(out.readlines(), [])

    ret_code, out, err = self.filesys.RunCommandFGWithTimeout(
                                                      'sleep 1; /bin/false', 2)
    self.assertEqual(ret_code, 1)
    self.assertEqual(out.readlines(), [])

    ret_code, out, err = self.filesys.RunCommandFGWithTimeout('sleep 3', 1)
    self.assertEqual(ret_code, None)
    self.assertEqual(out.readlines(), [])

    ret_code, out, err = self.filesys.RunCommandFGWithTimeout('sleep 4', 2)
    self.assertEqual(ret_code, None)
    self.assertEqual(out.readlines(), [])

    # Make sure we can get partial output even after a timeout.
    ret_code, out, err = self.filesys.RunCommandFGWithTimeout(
        'echo 1234 1>&2 && sleep 2', 1, False)
    self.assertEqual(ret_code, None)
    self.assertEqual(out.readlines(), [])
    self.assertEqual(err.readlines(), ['1234\n'])

  def testRunCommandFGToPipe(self):
    """Test that we can run shell commands in the foreground and that they
    correctly spool output to a file handle.
    """
    output_path = self.filesys.PathJoin(self.test_tmpdir, 'fake_log')
    output_path_err = self.filesys.PathJoin(self.test_tmpdir, 'fake_log_err')
    log_file = open(output_path, 'w')

    ret_code = self.filesys.RunCommandFGToPipe('echo 1234', log_file)
    self.assertEqual(ret_code, 0)
    log_file.seek(0)
    log_file.close()
    self.assertEqual(open(output_path, 'r').readlines(), ['1234\n'])
    self.filesys.RmFile(output_path)

    # Try one that has a known fail return code.
    log_file = open(output_path, 'w')
    ret_code = self.filesys.RunCommandFGToPipe('echo 5467; /bin/false',
                                               log_file)
    self.assertEqual(ret_code, 1)
    log_file.seek(0)
    log_file.close()
    self.assertEqual(open(output_path, 'r').readlines(), ['5467\n'])
    self.filesys.RmFile(output_path)

    # Try one that writes to stderr
    log_file = open(output_path, 'w')
    ret_code = self.filesys.RunCommandFGToPipe('/bin/ls /dev/null/not_a_file',
                                               log_file)
    self.assertNotEqual(ret_code, 0)
    log_file.seek(0)
    log_file.close()
    self.assertTrue(open(output_path, 'r').readlines())
    self.filesys.RmFile(output_path)

    # Try one that writes to stdout and stderr
    log_file = open(output_path, 'w')
    ret_code = self.filesys.RunCommandFGToPipe(
        '/bin/ls /dev/null/not_a_file; /bin/ls /dev/null',
        log_file)
    self.assertEqual(ret_code, 0)
    log_file.seek(0)
    log_file.close()
    self.assertTrue('/dev/null\n' in open(output_path, 'r'))
    self.filesys.RmFile(output_path)

    # Try one that writes to stdout and stderr separately
    log_file = open(output_path, 'w')
    log_file_err = open(output_path_err, 'w')
    ret_code = self.filesys.RunCommandFGToPipe(
        '/bin/ls /dev/null/not_a_file; /bin/ls /dev/null',
        log_file, log_file_err)
    self.assertEqual(ret_code, 0)
    log_file.seek(0)
    log_file.close()
    log_file_err.seek(0)
    log_file_err.close()
    self.assertEqual(open(output_path, 'r').readlines(), ['/dev/null\n'])
    self.filesys.RmFile(output_path)
    self.filesys.RmFile(output_path_err)

  def testRunCommandBGToPipe(self):
    """Test that we can indeed run shell commands in the background. """
    output_path = self.filesys.PathJoin(self.test_tmpdir, 'bogus_log')
    log_file = open(output_path, 'w')
    proc = self.filesys.RunCommandBGToPipe('echo 1234', log_file)

    ret_code = proc.wait()
    self.assertEqual(ret_code, 0)
    log_file.seek(0)
    log_file.close()
    self.assertEqual(open(output_path, 'r').readlines(), ['1234\n'])
    self.filesys.RmFile(output_path)

    log_file = open(output_path, 'w')
    proc = self.filesys.RunCommandBGToPipe('echo 5467; /bin/false', log_file)

    ret_code = proc.wait()
    self.assertEqual(ret_code, 1)
    log_file.seek(0)
    log_file.close()
    self.assertEqual(open(output_path, 'r').readlines(), ['5467\n'])
    self.filesys.RmFile(output_path)

  def testProcessCleanupWithoutPipe(self):
    """Tests that the various timeout methods also clean up what they spawned.
    We specifically validate that we also clean up the process group.
    """
    ret_code, out, err = self.filesys.RunCommandFGWithTimeout('sleep 12345', 2)
    time.sleep(1)
    self.assertEqual(None , ret_code)
    self.assertEqual(out.readlines() , [])
    # Now run a grep job that should find nothing with that tag.
    ret_code, out, err = self.filesys.RunCommandFG(
                                   'ps -fC sleep | grep "sleep 12345" | wc -l')
    # Hopefully by now, the processes are toast.
    self.assertEqual('0', out.readline().strip())

  def testProcessCleanupWithPipe(self):
    """Tests that the various timeout methods also clean up what the spawned
    when we use a file for capturing output.
    """
    output_buffer = self.filesys.PathJoin(self.test_tmpdir, 'fake_stream')
    output_file = open(output_buffer, 'w')
    timeout_code = self.filesys.RunCommandFGToPipeWithTimeout(
                                   '/usr/bin/yes', output_file, timeout = 1)
    time.sleep(1)
    self.assertEqual(timeout_code, None)
    output_file.close()
    ret_code, out, err = self.filesys.RunCommandFG(
                                   'ps -fC yes | grep "/bin/yes" | wc -l')
    self.assertEqual('0', out.readline().strip())
    output_file = open(output_buffer, 'r')
    self.assertEqual('y\n', output_file.readline())
    output_file.close()

  def testRunCommandExceptionExpectation(self):
    """This validates that the subprocess module does NOT raise an OSError when
    executing a non-existent command. 0xFF is the return code for bash
    trying to execute a non-existent file.
    """
    ret_code, out, err = self.filesys.RunCommandFG('bad_command_name')
    self.assertEqual(ret_code, 127)

  def testRunCommandThatHangsAndKillIt(self):
    """This validates that we can successfully kill a process ignoring SIGTERM.
    Signal 15 is SIGTERM.
    """
    ret_code, out, err = self.filesys.RunCommandFGWithTimeout(
        'trap "" 15; sleep 5', 1)
    self.assertEqual(ret_code, None)

  def testPathJoiningWithVariableNumberOfArguments(self):
    self.assertEqual('usr/bin/path',
                     self.filesys.PathJoin('usr', 'bin', 'path'))
    self.assertEqual('./fake/path/to/someplace',
                 self.filesys.PathJoin('.', 'fake/', 'path/to/', 'someplace'))

  def testAbs(self):
    self.assert_(self.filesys.IsAbs('/dev/null'))
    self.failIf(self.filesys.IsAbs('dev/null'))
    self.failIf(self.filesys.IsAbs('./dev/null'))
    self.assertEqual('/dev/null', self.filesys.AbsPath('/dev/../../dev/./null'))
    self.assertEqual('null', self.filesys.Basename('/dev/null'))

  def testCommonStartingTokens(self):
    a = ['apple', 'bee', 'cat', 'dog']
    b = ['apple', 'bee', 'cat', 'dog', 'eagle']
    c = ['apple', 'bee', 'cop', 'dog', 'eagle']
    d = ['apple', 'bat', 'cat']
    e = ['axiom', 'bat', 'cat', 'dog']
    f = ['axiom', 'bat']
    g = ['axiom']
    h = []
    CST = filesystem_handler.CommonStartingTokens
    self.assertEqual(a, CST(a))
    self.assertEqual(a, CST(a, a))
    self.assertEqual(a, CST(a, b))
    self.assertEqual(['apple', 'bee'], CST(a, c))
    self.assertEqual(['apple', 'bee'], CST(a, b, c))
    self.assertEqual(['apple'], CST(a, b, c, d))
    self.assertEqual(['apple'], CST(d, a))
    self.assertEqual(['axiom'], CST(e, f, g))
    self.assertEqual([], CST(a, f))
    self.assertEqual([], CST(g, h))
    self.assertEqual([], CST(h, g))
    self.assertEqual([], CST())

  def testMakeOrMoveSymLink(self):
    # Raise error on linking to oneself.
    self.assertRaises(self.filesys.ScriptError, self.filesys.MakeOrMoveSymlink,
                      '/dev/null', '/dev/null', 'dummy_link')


if __name__ == '__main__':
  unittest.main()
