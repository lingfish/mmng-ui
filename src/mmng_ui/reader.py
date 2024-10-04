from __future__ import annotations

import re
import time
import moment
from moment import Moment

frag = {}


def parse_line(line: str, send_function_code: bool = True, use_timestamp: bool = True) -> tuple[
    Moment, Moment | None, str, str]:
    """
    Parse a line from multimon-ng, converted from https://github.com/pagermon/pagermon/blob/master/client/reader.js

    :param line: The multimon-ng line to parse
    :type line: str
    :param send_function_code: Not entirely sure!
    :type send_function_code: bool
    :param use_timestamp: Attempt to decode and return timestamps
    :type use_timestamp: Moment
    :return: tuple of current time, timestamp, pager address and message
    :rtype: tuple
    """
    current_time: Moment = moment.now()
    timestamp: None = None
    address: str = None
    message: str | None = None
    trim_message: str = None
    time_string: str = None

    # POCSAG handling
    if re.search(r'POCSAG\d+: Address:', line):
        address_match = re.search(r'POCSAG\d+: Address:(.*?)Function', line)
        if address_match:
            address = address_match.group(1).strip()
            if send_function_code:
                function_code_match = re.search(r'Function: (\d)', line)
                if function_code_match:
                    address += function_code_match.group(1)

        # Handling Alpha messages
        if 'Alpha:' in line:
            message_match = re.search(r'Alpha:(.*?)$', line)
            if message_match:
                message = message_match.group(1).strip()

                if use_timestamp:
                    # Handle date formats like 'DD MMM YYYY HH:mm:ss'
                    if re.search(r'\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', line):
                        time_string_match = re.search(r'\d+ \w+ \d+ \d{2}:\d{2}:\d{2}', line)
                        if time_string_match:
                            time_string = time_string_match.group()
                            try:
                                timestamp = moment.date(time_string, '%d %B %Y %H:%M:%S')
                                message = message.replace(time_string, '').strip()
                            except ValueError:
                                raise
                                pass

                    # Handle date formats like 'YYYY-MM-DD HH:mm:ss'
                    elif re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line):
                        time_string_match = re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line)
                        if time_string_match:
                            time_string = time_string_match.group()
                            try:
                                timestamp = moment.date(time_string, 'YYYY-MM-DD HH:mm:ss')
                                message = message.replace(time_string, '').strip()
                            except ValueError:
                                raise
                                pass

                # Clean the message
                trim_message = re.sub(r'<[A-Za-z]{3}>', '', message).replace('Ä', '[').replace('Ü', ']').strip()

        # Handling Numeric messages
        elif 'Numeric:' in line:
            message_match = re.search(r'Numeric:(.*?)$', line)
            if message_match:
                message = message_match.group(1).strip()
                trim_message = re.sub(r'<[A-Za-z]{3}>', '', message).replace('Ä', '[').replace('Ü', ']').strip()

    # FLEX handling
    elif re.search(r'FLEX[:|]', line):
        address_match = re.search(r'FLEX[:|] ?.*?[\[|](\d*?)[\]| ]', line)
        if address_match:
            address = address_match.group(1).trim()

        # Handle timestamps within FLEX
        if use_timestamp:
            if re.search(r'FLEX[:|] ?\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', line):
                time_string_match = re.search(r'\d+ \w+ \d+ \d{2}:\d{2}:\d{2}', line)
                if time_string_match:
                    time_string = time_string_match.group()
                    try:
                        timestamp = moment.date(time_string, '%d %B %Y %H:%M:%S')
                    except ValueError:
                        pass

            elif re.search(r'FLEX[:|] ?\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line):
                time_string_match = re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line)
                if time_string_match:
                    time_string = time_string_match.group()
                    try:
                        timestamp = moment.date(time_string, 'YYYY-MM-DD HH:mm:ss')
                    except ValueError:
                        pass

        # Handle fragmented and complete messages
        if re.search(r'([ |]ALN[ |]|[ |]GPN[ |]|[ |]NUM[ |])', line):
            message_match = re.search(r'FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |](.+)', line)
            if message_match:
                message = message_match.group(1).strip()

                # Message fragmentation handling
                if re.search(r'[ |][0-9]{4}\/[0-9]\/F\/.[ |]', line):
                    frag[address] = message
                    trim_message = ''
                elif re.search(r'[ |][0-9]{4}\/[0-9]\/C\/.[ |]', line):
                    trim_message = frag[address] + message
                    del frag[address]
                else:
                    trim_message = message

    # Default case
    else:
        address = ''
        message = None
        trim_message = ''

    return current_time, timestamp, address, trim_message
