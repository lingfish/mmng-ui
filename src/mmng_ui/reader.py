from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any

import moment
from moment import Moment

frag = {}


@dataclass
class PocsagMessage:
    current_time: Moment = field(default_factory=moment.now)
    timestamp: Moment = None
    address: str = None
    trim_message: str = None


@dataclass
class ParseLine:
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

    send_function_code: bool = True
    use_timestamp: bool = True
    json_detected: bool | None = None

    def _parse_json(self, json_line: Any, result: PocsagMessage) -> PocsagMessage:
        """Parse a multimon-ng unified JSON schema object (schema v2+).

        The envelope is stable across schema versions: `kind` classifies the
        frame (message / event / diagnostic), `capcode` is the unified address
        (null for non-addressed frames), and `message` is the best-decode
        shortcut. Only `kind == "message"` carries a subscriber payload;
        events and diagnostics produce no table row, avoiding the field-
        presence crashes of the pre-schema era (mmng-ui#3).
        """
        kind = json_line.get('kind', '')

        capcode = json_line.get('capcode')
        result.address = '' if capcode is None else str(capcode)

        if kind != 'message':
            # Event (tone_only, biw_*, flextime, eas_*) or diagnostic
            # (bch_stats): no displayable message. Leave trim_message unset.
            result.trim_message = None
            return result

        message = json_line.get('message') or ''
        # Strip <XXX> control-char markers and apply the same umlaut cleanup
        # the legacy path uses, so display is consistent across schemas.
        result.trim_message = (
            re.sub(r'<[A-Za-z]{3}>', '', message).replace('Ä', '[').replace('Ü', ']').strip() or None
        )

        # timestamp is Unix epoch seconds (int). Convert to a Moment when
        # requested so the UI can show it; fall back silently if absent.
        if self.use_timestamp:
            ts = json_line.get('timestamp')
            if isinstance(ts, (int, float)):
                try:
                    result.timestamp = moment.unix(ts, utc=True)
                except (ValueError, TypeError):
                    pass

        return result

    def parse(self, line: str) -> tuple[PocsagMessage, bool]:
        result = PocsagMessage()
        message: str | None = None
        trim_message: str | None = None
        time_string: str | None = None
        json_line: Any | None = None
        timestamp: Moment = None

        if self.json_detected is None:
            try:
                json_line = json.loads(line)
                self.json_detected = True
            except json.JSONDecodeError:
                self.json_detected = False

        if self.json_detected:
            if not json_line:
                try:
                    json_line = json.loads(line)
                except JSONDecodeError:
                    result.trim_message = f'ERROR: multimon-ng returned non-JSON: {line}'
                    result.address = ''
                    return result, self.json_detected

            # --- multimon-ng JSON schema v2 (schema/json/v2.json) ---
            # Unified JSON envelope (schema v2): kind, capcode, message.
            # Only kind == "message" has a subscriber payload; events and
            # diagnostics are skipped cleanly (cf. mmng-ui#3).
            if json_line.get('schema_version') == 2:
                return self._parse_json(json_line, result), self.json_detected

            demod_name = json_line.get('demod_name', '')
            msg_type = json_line.get('msg_type', '')

            if 'pocsag' in demod_name.lower():
                result.trim_message = (
                    re.sub(r'<[A-Za-z]{3}>', '', json_line.get('alpha', '')).replace('Ä', '[').replace('Ü', ']').strip()
                    or ''
                )
                result.address = str(json_line.get('address', ''))
            elif 'flex' in demod_name.lower() or msg_type in (
                'alphanumeric', 'numeric', 'tone_only', 'special_numeric',
                'secure', 'instruction', 'short_msg', 'binary', 'numbered_numeric',
            ):
                result.trim_message = json_line.get('message', '')
                result.address = str(json_line.get('capcode', ''))

            return result, self.json_detected

        # POCSAG handling
        if re.search(r'POCSAG\d+: Address:', line):
            address_match = re.search(r'POCSAG\d+: Address:(.*?)Function', line)
            if address_match:
                address = address_match.group(1).strip()
                if self.send_function_code:
                    function_code_match = re.search(r'Function: (\d)', line)
                    if function_code_match:
                        address += function_code_match.group(1)

            # Handling Alpha messages
            if 'Alpha:' in line:
                message_match = re.search(r'Alpha:(.*?)$', line)
                if message_match:
                    message = message_match.group(1).strip()

                    if self.use_timestamp:
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
                                    # pass

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
                                    # pass

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
                address = address_match.group(1).strip()

            # Handle timestamps within FLEX
            if self.use_timestamp:
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
                        try:
                            trim_message = frag[address] + message
                            del frag[address]
                        except KeyError:
                            # We've seen a fragment without the starting frag, treat as final
                            trim_message = message
                    else:
                        trim_message = message

        # Default case
        else:
            address = ''
            message = None
            trim_message = ''

        result.timestamp = timestamp or None
        result.address = str(address)
        result.trim_message = trim_message or None
        return result, self.json_detected
