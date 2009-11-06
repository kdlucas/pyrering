#!/usr/bin/python
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""mocks EmailMessage class for testing.

This mock overwrites Send method in EmailMessage to raise an EmaiCalledError
instead of sending out emails for testing purpose. It is not a really error.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

from lib import emailmessage


class MockEmailMessage(emailmessage.EmailMessage):
  """Mock EmailMessage class to testing purpose.
  
  It overwrites the original Send method to raise an exception instead of
  sending real email messages.
  """

  class EmailCalledError(Exception):
    """Thrown when email is about to send out. Not an acutal error."""
    pass
    
  def Send(self,
           unused_server_name='localhost',
           unused_user=None,
           unused_password=None):
    """Mock the real EmailMessage.Send method."""
    raise self.EmailCalledError
