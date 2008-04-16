#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""The unit test class for scanscripts."""

__author__ = 'mwu@google.com (Mingyu Wu)'

import os
import unittest


from lib import mock_filesystemhandlerextend
from lib import scanscripts

ScanScriptsError = scanscripts.ScanScriptsError
TestNotFoundError = scanscripts.TestNotFoundError
TestNotSupportedError = scanscripts.TestNotSupportedError


class ScanScriptsTest(unittest.TestCase):
  """Unit test cases for ScanScripts."""

  def setUp(self):
    """Setup a virutal filesystem for testing and populate it with test data."""
    self.script_dir = '/tmp/source'
    self.mock_filesystem = (
        mock_filesystemhandlerextend.MockFileSystemHandlerExtend())
    self._PopulateFileSystem({'/tmp/source/anyfile.sh': ''})
    self.one = scanscripts.ScanScripts(self.script_dir,
                                       filesystem=self.mock_filesystem)

  def _PopulateFileSystem(self, temp_file_system):
    """Polulate the virutal filesystem self.mock_filesystem.fake_files.
    
    The data are prepared for test purpose.

    Args:
      temp_file_system: a dictionary for the mock file system.
    """
    for key, value in temp_file_system.iteritems():
      self.mock_filesystem.WriteToFile(key, value)
    
  def testDefaultFileSystem(self):
    """The default real filesystem should be inited as default."""
    one = scanscripts.ScanScripts('/tmp')
    self.assertTrue(one.filesystem, msg='Default file system init failed')
      
  def testNormalSuite(self):
    """The normal case for passing in a suite file."""
    temp_file_system = {
        '/tmp/source/test1.sh': '',
        '/tmp/source/test2.py': '',
        '/tmp/source/normal.suite': ['# this is a comment\n',
                                     'test1.sh\n',
                                     'test2.py\n'],
        }
    self._PopulateFileSystem(temp_file_system)

    script_list = self.one.BaseScan('normal.suite')
    self.assertEqual(len(script_list), 2, msg='failed to parse suite file.')
    for one in script_list:
      self.assertTrue(one['TEST_SCRIPT'] in ['/tmp/source/test1.sh',
                                             '/tmp/source/test2.py'],
                      msg='wrong script returned: %s.' % one['TEST_SCRIPT'])

  def testOneScript(self):
    """Pass in one script as the argument, one script should be returned."""
    temp_file_system = {'/tmp/source/test1.sh': '',
                        '/tmp/source/test2.sh': '',
                       }
    self._PopulateFileSystem(temp_file_system)

    script_list = self.one.BaseScan('test1.sh')
    self.assertEqual(len(script_list), 1, msg='one script should be returned')
    self.assertEqual(script_list[0]['TEST_SCRIPT'],
                     os.path.join(self.script_dir, 'test1.sh'),
                     msg=('wrong script is returned %s' %
                          script_list[0]['TEST_SCRIPT']))
    
  def testOnePerlScript(self):
    """Pass in one script as the argument, one script should be returned."""
    temp_file_system = {'/tmp/source/test1.pl': '',
                        '/tmp/source/test2.sh': '',
                       }
    self._PopulateFileSystem(temp_file_system)

    script_list = self.one.BaseScan('test1.pl')
    self.assertEqual(len(script_list), 1, msg='one script should be returned')
    self.assertEqual(script_list[0]['TEST_SCRIPT'],
                     os.path.join(self.script_dir, 'test1.pl'),
                     msg=('wrong script is returned %s' %
                          script_list[0]['TEST_SCRIPT']))

  def testNoneExistName(self):
    """Test a nonexist name, a ValueError should be raised."""
    temp_file_system = {'/tmp/source/test1.sh': ''}
    self._PopulateFileSystem(temp_file_system)
    self.assertRaises(TestNotFoundError, self.one.BaseScan, 'nonexist.sh')
  
  def testOneDir(self):
    """Pass in a dir name, the scripts under that dir should be returned."""
    temp_file_system = {'/tmp/source/one_dir/test1.py': ''}
    self._PopulateFileSystem(temp_file_system)

    # Prepare a return for the os.walk call, this will be needed when BaseScan
    # walks on that directory.
    tuple1 = ('/tmp/source/one_dir', [], ['test1.py'])
    self.mock_filesystem.walk_list = [tuple1]

    script_list = self.one.BaseScan('one_dir')
    self.assertEqual(len(script_list), 1, msg='one script should return')
    self.assertEqual(os.path.basename(script_list[0]['TEST_SCRIPT']),
                     'test1.py',
                     msg='test1.py should return')

  def testScanPerlScript(self):
    """Pass in a dir name, the perl script under that dir should bereturned."""
    temp_file_system = {'/tmp/source/one_dir/test1.pl': ''}
    self._PopulateFileSystem(temp_file_system)

    # Prepare a return for the os.walk call, this will be needed when BaseScan
    # walks on that directory.
    tuple1 = ('/tmp/source/one_dir', [], ['test1.pl'])
    self.mock_filesystem.walk_list = [tuple1]
    script_list = self.one.BaseScan('one_dir')
    self.assertEqual(len(script_list), 1, msg='one script should return')
    self.assertEqual(os.path.basename(script_list[0]['TEST_SCRIPT']),
                     'test1.pl',
                     msg='test1.pl should return')
    
  def testLoopCondition(self):
    """Test if a loop happens, a ValueError should be raised."""
    temp_file_system = {'/tmp/source/loop/loop1.suite': ['loop2.suite\n'],
                        '/tmp/source/loop/loop2.suite': ['loop1.suite\n']}
    self._PopulateFileSystem(temp_file_system)
    self.assertRaises(ScanScriptsError, self.one.BaseScan, 'loop/loop1.suite')

  def testWildcardsSuite(self):
    """Test suite file contains wildcard charactors.
    
    If the suite file has wildcards file names, glob should be used to match the
    real scripts and return the list of real scripts.
    """
    temp_file_system = {'/tmp/source/wildcard/test1.py': '',
                        '/tmp/source/wildcard/wildcard.suite': '*.py\n'}
    self._PopulateFileSystem(temp_file_system)
    script_list = self.one.BaseScan('wildcard/wildcard.suite')
    self.assertEqual(len(script_list), 1, msg='only one script should return')
    
    for one_script in script_list:
      self.assertTrue(os.path.basename(one_script['TEST_SCRIPT']) in
                      ['test1.py'])
      
  def testParFileScan(self):
    """Test scan and pick up par files."""
    temp_file_system = {'/tmp/source/onedir/test1.par': '',
                        '/tmp/source/onedir/test1.sh': '',
                       }
    self._PopulateFileSystem(temp_file_system)
    script_list = self.one.BaseScan('onedir/test1.par')
    self.assertEqual(len(script_list), 1, msg='test1.par should be returned.')
    self.assertEqual(script_list[0]['TEST_SCRIPT'],
                     os.path.join(self.script_dir, 'onedir/test1.par'),
                     msg=('wrong script is returned %s' %
                          script_list[0]['TEST_SCRIPT']))

  def testWildcardSuite(self):
    """Test suite file contains wildcard picks up par files."""
    temp_file_system = {'/tmp/source/wildcard/test1.par': '',
                        '/tmp/source/wildcard/wildcard.suite': '*.par\n'}
    self._PopulateFileSystem(temp_file_system)
    script_list = self.one.BaseScan('wildcard/wildcard.suite')
    self.assertEqual(len(script_list), 1, msg='Only one script shoudl return')
    for one_script in script_list:
      self.assertTrue(os.path.basename(one_script['TEST_SCRIPT']) in
                      ['test1.par'])
    

if __name__ == '__main__':
  unittest.main()
