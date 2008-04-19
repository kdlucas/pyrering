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

"""Provides common non-specific to PyreRing util methods."""

__author__ = 'mwu@google.com (Mingyu Wu)'


import logging

logger = logging.getLogger('PyreRing')


def DebugLog(f, name=None):
  """A decorator for logging debug info of method."""
  if name is None:
    name = f.func_name

  def Debug(*args, **kwargs):
    """Wrap a logger around the method to log method enter and exit."""
    logger.debug('enter %s method...' % name)
    logger.debug('arguments: %s %s' % (str(args), str(kwargs)))
    result = f(*args, **kwargs)
    logger.debug('exit %s method...' % name)
    logger.debug('results are: %s' % str(result))
    return result
  return Debug
