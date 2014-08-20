#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the Google Chrome cookie database plugin."""

import unittest

# pylint: disable=unused-import
from plaso.formatters import chrome_cookies as chrome_cookies_formatter
from plaso.lib import eventdata
from plaso.lib import timelib_test
from plaso.parsers.sqlite_plugins import chrome_cookies
from plaso.parsers.sqlite_plugins import test_lib


class ChromeCookiesPluginTest(test_lib.SQLitePluginTestCase):
  """Tests for the Google Chrome cookie database plugin."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._plugin = chrome_cookies.ChromeCookiePlugin()

  def testProcess(self):
    """Tests the Process function on a Chrome cookie database file."""
    test_file = self._GetTestFilePath(['cookies.db'])
    event_generator = self._ParseDatabaseFileWithPlugin(self._plugin, test_file)
    event_objects = []
    extra_objects = []

    # Since we've got both events generated by cookie plugins and the Chrome
    # cookie plugin we need to separate them.
    for event_object in self._GetEventObjects(event_generator):
      # The plugin attribute is not set by the plugin itself unless the plugin
      # is a specific cookie plugin.
      if not hasattr(event_object, 'plugin'):
        event_objects.append(event_object)
      else:
        extra_objects.append(event_object)

    # The cookie database contains 560 entries:
    #     560 creation timestamps.
    #     560 last access timestamps.
    #     560 expired timestamps.
    # Then there are extra events created by plugins:
    #      75 events created by Google Analytics cookies.
    # In total: 1755 events.
    self.assertEquals(len(event_objects), 3 * 560)

    # Double check that we've got at least the 75 Google Analytics sessions.
    self.assertGreaterEqual(len(extra_objects), 75)

    # Check few "random" events to verify.

    # Check one linkedin cookie.
    event_object = event_objects[124]
    self.assertEquals(
        event_object.timestamp_desc, eventdata.EventTimestamp.ACCESS_TIME)
    self.assertEquals(event_object.host, u'www.linkedin.com')
    self.assertEquals(event_object.cookie_name, u'leo_auth_token')
    self.assertFalse(event_object.httponly)
    self.assertEquals(event_object.url, u'http://www.linkedin.com/')

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '2011-08-25 21:50:27.292367')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    expected_msg = (
        u'http://www.linkedin.com/ (leo_auth_token) Flags: [HTTP only] = False '
        u'[Persistent] = True')
    expected_short = u'www.linkedin.com (leo_auth_token)'
    self._TestGetMessageStrings(event_object, expected_msg, expected_short)

    # Check one of the visits to rubiconproject.com.
    event_object = event_objects[379]
    self.assertEquals(
        event_object.timestamp_desc, eventdata.EventTimestamp.ACCESS_TIME)

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '2012-04-01 13:54:34.949210')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    self.assertEquals(event_object.url, u'http://rubiconproject.com/')
    self.assertEquals(event_object.path, u'/')
    self.assertFalse(event_object.secure)
    self.assertTrue(event_object.persistent)

    expected_msg = (
        u'http://rubiconproject.com/ (put_2249) Flags: [HTTP only] = False '
        u'[Persistent] = True')
    self._TestGetMessageStrings(
        event_object, expected_msg, u'rubiconproject.com (put_2249)')

    # Examine an event for a visit to a political blog site.
    event_object = event_objects[444]
    self.assertEquals(
        event_object.path,
        u'/2012/03/21/romney-tries-to-clean-up-etch-a-sketch-mess/')
    self.assertEquals(event_object.host, u'politicalticker.blogs.cnn.com')

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '2012-03-22 01:47:21.012022')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    # Examine a cookie that has an autologin entry.
    event_object = event_objects[1425]

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '2012-04-01 13:52:56.189444')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    self.assertEquals(event_object.host, u'marvel.com')
    self.assertEquals(event_object.cookie_name, u'autologin[timeout]')
    self.assertEquals(
        event_object.timestamp_desc, eventdata.EventTimestamp.CREATION_TIME)
    # This particular cookie value represents a timeout value that corresponds
    # to the expiration date of the cookie.
    self.assertEquals(event_object.data, u'1364824322')


if __name__ == '__main__':
  unittest.main()
