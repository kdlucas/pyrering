#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.
# Author: mwu@google.com (Mingyu Wu)

"""A dummy program to output a lot of text on screen."""

count = 1
# 1000 times of the string will give a size about 23k.
while count < 1000:
  print 'this is a test message.'
  count += 1
