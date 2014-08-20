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
"""This file contains the wifi.log (Mac OS X) parser."""

import datetime
import logging
import re

import pyparsing

from plaso.events import time_events
from plaso.lib import eventdata
from plaso.lib import timelib
from plaso.parsers import text_parser


__author__ = 'Joaquin Moreno Garijo (bastionado@gmail.com)'


class MacWifiLogEvent(time_events.TimestampEvent):
  """Convenience class for a Mac Wifi log line event."""

  DATA_TYPE = 'mac:wifilog:line'

  def __init__(self, timestamp, agent, function, text, action):
    """Initializes the event object.

    Args:
      timestamp: The timestamp time value, epoch.
      source_code: Details of the source code file generating the event.
      log_level: The log level used for the event.
      text: The log message
      action: A string containing known WiFI actions, eg: connected to
              an AP, configured, etc. If the action is not known,
              the value is the message of the log (text variable).
    """
    super(MacWifiLogEvent, self).__init__(timestamp,
        eventdata.EventTimestamp.ADDED_TIME)
    self.agent = agent
    self.function = function
    self.text = text
    self.action = action


class MacWifiLogParser(text_parser.PyparsingSingleLineTextParser):
  """Parse text based on wifi.log file."""

  NAME = 'macwifi'

  ENCODING = u'utf-8'

  # Regular expressions for known actions.
  RE_CONNECTED = re.compile(r'Already\sassociated\sto\s(.*)\.\sBailing')
  RE_WIFI_PARAMETERS = re.compile(
      r'\[ssid=(.*?), bssid=(.*?), security=(.*?), rssi=')

  # Define how a log line should look like.
  WIFI_LINE = (
      text_parser.PyparsingConstants.MONTH.setResultsName('day_of_week') +
      text_parser.PyparsingConstants.MONTH.setResultsName('month') +
      text_parser.PyparsingConstants.ONE_OR_TWO_DIGITS.setResultsName('day') +
      text_parser.PyparsingConstants.TIME_MSEC.setResultsName('time') +
      pyparsing.Literal(u'<') +
      pyparsing.CharsNotIn(u'>').setResultsName('agent') +
      pyparsing.Literal(u'>') +
      pyparsing.CharsNotIn(u':').setResultsName('function') +
      pyparsing.Literal(u':') +
      pyparsing.SkipTo(pyparsing.lineEnd).setResultsName('text'))

  WIFI_HEADER = (
      text_parser.PyparsingConstants.MONTH.setResultsName('day_of_week') +
      text_parser.PyparsingConstants.MONTH.setResultsName('month') +
      text_parser.PyparsingConstants.ONE_OR_TWO_DIGITS.setResultsName('day') +
      text_parser.PyparsingConstants.TIME_MSEC.setResultsName('time') +
      pyparsing.Literal(u'***Starting Up***'))

  # Define the available log line structures.
  LINE_STRUCTURES = [
      ('logline', WIFI_LINE),
      ('header', WIFI_HEADER)]

  def __init__(self):
    """Initializes a parser object."""
    super(MacWifiLogParser, self).__init__()
    self._year_use = 0
    self._last_month = None

  def _GetAction(self, agent, function, text):
    """Parse the well know actions for easy reading.

    Args:
      agent: The device that generate the entry.
      function: The function or action called by the agent.
      text: Mac Wifi log text.

    Returns:
      know_action: A formatted string representing the known (or common) action.
    """
    if not agent.startswith('airportd'):
      return text

    if 'airportdProcessDLILEvent' in function:
      interface = text.split()[0]
      return u'Interface {0:s} turn up.'.format(interface)

    if 'doAutoJoin' in function:
      match = re.match(self.RE_CONNECTED, text)
      if match:
        ssid = match.group(1)[1:-1]
      else:
        ssid = 'Unknown'
      return u'Wifi connected to SSID {0:s}'.format(ssid)

    if 'processSystemPSKAssoc' in function:
      wifi_parameters = self.RE_WIFI_PARAMETERS.search(text)
      if wifi_parameters:
        ssid = wifi_parameters.group(1)
        bssid = wifi_parameters.group(2)
        security = wifi_parameters.group(3)
        if not ssid:
          ssid = 'Unknown'
        if not bssid:
          bssid = 'Unknown'
        if not security:
          security = 'Unknown'
        return (
             u'New wifi configured. BSSID: {0:s}, SSID: {1:s}, '
             u'Security: {2:s}.').format(bssid, ssid, security)
    return text

  def _GetTimestamp(self, day, month, year, time):
    """Gets a timestamp from a pyparsing ParseResults timestamp.

    This is a timestamp_string as returned by using
    text_parser.PyparsingConstants structures:
    08, Nov, [20, 36, 37], 222]

    Args:
      timestamp_string: The pyparsing ParseResults object

    Returns:
      day: An integer representing the day.
      month: An integer representing the month.
      year: An integer representing the year.
      timestamp: A plaso timelib timestamp event or 0.
    """
    try:
      time_part, millisecond = time
      hour, minute, second = time_part
      timestamp = timelib.Timestamp.FromTimeParts(
          year, month, day, hour, minute, second,
          microseconds=(millisecond * 1000))
    except ValueError:
      timestamp = 0
    return timestamp

  def _GetYear(self, stat, zone):
    """Retrieves the year either from the input file or from the settings."""
    time = getattr(stat, 'crtime', 0)
    if not time:
      time = getattr(stat, 'ctime', 0)

    if not time:
      logging.error(
          ('Unable to determine correct year of syslog file, using current '
           'year'))
      return timelib.GetCurrentYear()

    try:
      timestamp = datetime.datetime.fromtimestamp(time, zone)
    except ValueError as exception:
      logging.error((
          u'Unable to determine correct year of syslog file, using current '
          u'one, with error: {0:s}').format(exception))
      return timelib.GetCurrentYear()
    return timestamp.year

  def _ParseLogLine(self, parser_context, structure):
    """Parse a logline and store appropriate attributes.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      structure: A pyparsing.ParseResults object from a line in the
                 log file.

    Returns:
      An event object (instance of EventObject) or None.
    """
    # TODO: improving this to get a valid year.
    if not self._year_use:
      self._year_use = parser_context.year

    if not self._year_use:
      # Get from the creation time of the file.
      self._year_use = self._GetYear(
          self.file_entry.GetStat(), parser_context.timezone)
      # If fail, get from the current time.
      if not self._year_use:
        self._year_use = timelib.GetCurrentYear()

    # Gap detected between years.
    month = timelib.MONTH_DICT.get(structure.month.lower())
    if not self._last_month:
      self._last_month = month
    if month < self._last_month:
      self._year_use += 1
    timestamp = self._GetTimestamp(
        structure.day,
        month,
        self._year_use,
        structure.time)
    if not timestamp:
      logging.debug(u'Invalid timestamp {0:s}'.format(structure.timestamp))
      return
    self._last_month = month

    text = structure.text

    # Due to the use of CharsNotIn pyparsing structure contains whitespaces
    # that need to be removed.
    function = structure.function.strip()
    action = self._GetAction(structure.agent, function, text)
    return MacWifiLogEvent(
        timestamp, structure.agent, function, text, action)

  def ParseRecord(self, parser_context, key, structure):
    """Parse each record structure and return an EventObject if applicable.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      key: An identification string indicating the name of the parsed
           structure.
      structure: A pyparsing.ParseResults object from a line in the
                 log file.

    Returns:
      An event object (instance of EventObject) or None.
    """
    if key == 'logline':
      return self._ParseLogLine(parser_context, structure)
    elif key != 'header':
      logging.warning(
          u'Unable to parse record, unknown structure: {0:s}'.format(key))

  def VerifyStructure(self, parser_context, line):
    """Verify that this file is a Mac Wifi log file.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      line: A single line from the text file.

    Returns:
      True if this is the correct parser, False otherwise.
    """
    try:
      _ = self.WIFI_HEADER.parseString(line)
    except pyparsing.ParseException:
      logging.debug(u'Not a Mac Wifi log file')
      return False
    return True
