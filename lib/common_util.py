#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.

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
