#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.

"""This is a wrapper around email.MIMEText module.

This is used to generate email message with less typing. Since I am expecting
email test report will be used frequently.
"""

__author__ = 'mwu@google.com (Mingyu Wu)'

import email.MIMEText
import logging
import smtplib
import sys
import traceback

from lib import common_util

DEBUG = common_util.DebugLog

logger = logging.getLogger('PyreRing')


class EmailMessage(object):
  """This class is a wrapper around email.MIMEText and smtplib to send emails.
  
  It will send out user specified emails. If failed, it should catch all
  exceptions and log them, it will not raise exceptions to upper levels.
  So it will be a nice handy tool to use without worrying about exceptions.
  """

  def __init__(self):
    self.message = ''

  @DEBUG
  def SetMessage(self,
                 from_address,
                 to_address,
                 subject,
                 body='',
                 content_file=''):
    """Prepare an MIMEtext object for an email message.
    
    It will populate the email message with from/to/subject/body.

    Args:
      from_address: an email address or a google id. '@google.com' will be
          assumed if not given.
      to_address: <string> a comma seperated email addresses or google ids or
          mix. '@google.com' is assumed if not given.
      subject: <string> the email subject.
      body: <string> the email body.
      content_file: this should be a flat text file append at the bottom of
        the email body.

    Returns:
      None. a MIME type message will be created with the given arguments as
      the class variable.
    """
    if not content_file:
      content = body
    else:
      reader = open(content_file)
      content = reader.read()
      reader.close()
    if not to_address:
      logger.warning('no email receipient defined')
      return
    self.message = email.MIMEText.MIMEText(content)
    self.message['From'] = from_address
    self.message['To'] = to_address
    self.message['Subject'] = subject

    self.from_address = from_address
    self.to_address = to_address

  @DEBUG
  def Send(self, server_name='localhost', user=None, password=None):
    """Send out the email message using the given mail server.

    User will have the option to set server name and account info. The default
    is localhost and no authentication needed. If authentication is required,
    both 'user' and 'password' has to be provided. use '' if password is empty.

    Args:
      server_name: the mail server's name, default is localhost.
      user: userid to login the smtp server.
      password: password to login the smtp server.

    Returns:
      A String: message about why it failed; None, otherwise.
    """
    server = smtplib.SMTP(server_name)
    try:
      try:
        if user is not None and password is not None:
          server.login(user, password)
        # the toaddress has to be a list.
        server.sendmail(self.from_address,
                        self.to_address.split(','),
                        self.message.as_string())
      except (smtplib.SMTPHeloError,
              smtplib.SMTPAuthenticationError,
              smtplib.SMTPRecipientsRefused,
              smtplib.SMTPSenderRefused,
              smtplib.SMTPDataError,
              smtplib.SMTPException):
        err_msg = ('Exception[%s] sending mail. \n\t STACK TRACE: \n%s'
                   % (sys.exc_type, traceback.format_exc()))
        logger.error('Sending email failed, error message: %s' % err_msg)
        return err_msg
    finally:
      server.quit()
    return None
