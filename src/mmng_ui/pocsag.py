import re
import sys
from collections import deque
from datetime import datetime
import time
import asyncio
from subprocess import PIPE
from dataclasses import dataclass
from time import sleep

import moment
from rich import inspect
from rich.text import Text
from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Header, Static, RichLog, DataTable, Footer, HelpPanel, Markdown, Sparkline
from textual import work, events
from textual.message import Message
from textual.binding import Binding
from textual.actions import SkipAction

from .reader import parse_line


def parse_datetime(time_string: str, format_string: str) -> int:
    """
    Parse a datetime and return, I dunno.

    :param time_string:
    :type time_string:
    :param format_string:
    :type format_string:
    :return:
    :rtype:
    """
    try:
        dt_obj = datetime.strptime(time_string, format_string)
        return int(time.mktime(dt_obj.timetuple()))
    except ValueError:
        return None


@dataclass
class OutputMessage(Message, bubble=False):
    """Custom message class to handle subprocess output."""
    output: str


@dataclass
class Status:
    """The status pane"""

    receiver: str
    ip_address: str

    def __repr__(self):
        return(f'Receiver: {self.receiver}\nIP address: {self.ip_address}')

class UDPHandler(asyncio.DatagramProtocol):
    def __init__(self, app, loop):
        self.app = app
        self.loop = loop
        self.status = self.app.query_one('#status')
        self.last_activity_time = 0

    def connection_made(self, transport):
        self.transport = transport
        self.status.receiver = 'ready'

    def connection_lost(self, exc):
        self.status.receiver = 'Closed'

    def datagram_received(self, data, addr):
        # log = self.pocsag.query_one('#log')
        # message = data.decode()
        # log.write(f"Received data from {addr}")
        self.last_activity_time = self.loop.time()
        # self.status.receiver = 'receiving'
        self.status.ip_address = addr[0]
        self.app.process.stdin.write(data)
        self.app.process.stdin.drain()

    async def idle_task(self):
        while True:
            if self.loop.time() - self.last_activity_time > 5:
                self.status.receiver = '[wheat4]idle[/]'
            await asyncio.sleep(1)

class StatusWidget(Widget):
    """The status pane."""

    receiver = reactive('[dark_red]Not connected[/]')
    ip_address = reactive('[wheat4]None[/]')

    def render(self) -> str:
        return(f'Receiver: {self.receiver}\nIP address: {self.ip_address}')


class HelpScreen(ModalScreen):
    """Help screen modal."""

    BINDINGS = [("escape,space,q,question_mark", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        text = """
# mmng-ui

## Introduction

This is a TUI utility to decode and see POCSAG messages.

## Objective

blah.

[//]: # (README.md ends here)"""
        yield Markdown(text, id='help')



class MsgsPerSecond(Sparkline):
    def __init__(self, samples=[0]*60, **kwargs):
        super().__init__(**kwargs)
        self.samples = samples

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1, self.update_graph)
        self.data = self.samples

    def update_graph(self) -> None:
        self.log(self.app)
        self.data = self.data[-59:] + [len(self.app.message_count)]
        self.app.message_count = []


# class Pocsag(App):
class MainScreen(Screen):
    def compose(self):
        yield Header()
        with Container(id="app-grid"):
            yield DataTable(id='messages')
            yield RichLog(id='log', highlight=True, markup=True)
            # yield StatusWidget(id='status')
            with Container(id="status-container"):
                yield StatusWidget(id='status')
                yield Sparkline([], id='spark')
        yield MsgsPerSecond(id='msgs-per-second')
        yield Footer()

    async def on_mount(self) -> None:
        """Setup the initial components."""
        self.current_width = '0'
        self.title = 'multimon-ng decoder'
        table = self.screen.query_one('#messages')
        log = self.screen.query_one('#log')
        status = self.screen.query_one('#status')

        table.add_column('Time', key='time')
        table.add_column('Address', key='address')
        table.add_column('Message', key='message')
        table.cursor_type = 'none'
        table.border_title ='POCSAG messages'
        log.border_title='Log window'
        status.border_title='Status'

        shell_command = (
            '/home/jason/PycharmProjects/multimon-ng/build/multimon-ng '
            '-a POCSAG512 -a POCSAG1200 -a POCSAG2400 -f alpha '
            '-t raw -u -q -b1 --timestamp -p -'
        )
        self.log('About to start multimon')
        self.stream_subprocess(shell_command)
        self.log('AFTER: About to start multimon')

        network_loop = asyncio.get_running_loop()
        transport, protocol = await network_loop.create_datagram_endpoint(
            lambda: UDPHandler(self, network_loop),
            local_addr=('::', 8888)
        )
        network_loop.create_task(protocol.idle_task())

    @work(exclusive=True)
    async def stream_subprocess(self, command):
        """Stream output from a subprocess and post it using post_message."""
        self.log('   in stream_subprocess')
        self.process = await asyncio.create_subprocess_shell(
            command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE
        )

        # Stream stdout asynchronously
        async for line in self.read_process_output(self.process.stdout):
            self.post_message(OutputMessage(line))
            self.set_timer(1, lambda: setattr(self.query_one('#status'), 'receiver', '[dark_green]waiting[/]'))
            self.query_one('#spark').data = self.query_one('#spark').data[-9:] + [len(line)]
            self.app.message_count.append(1)

        # Handle any stderr errors
        async for error in self.read_process_output(self.process.stderr):
            self.post_message(OutputMessage(f'[red]Error: {error}'))

    async def read_process_output(self, output):
        """Read the output of a subprocess line by line."""
        self.log('   in read_process_output')
        status = self.query_one('#status')
        while True:
            status.receiver = '[blink bold bright_green]receiving[/]'
            line = await output.readline()
            self.log('   read a line')
            if not line:
                break
            yield line.decode().strip()

    async def on_resize(self, event: events.Resize) -> None:
        self.current_width = event.size.width
        log = self.screen.query_one('#log')
        table = self.screen.query_one('#messages')

    async def watch_show_vertical_scrollbar(self) -> None:
        log = self.screen.query_one('#log')
        log.write('scrollbar appeared!')

    async def on_output_message(self, message: OutputMessage):
        """Handle OutputMessage to update UI components."""
        log = self.screen.query_one('#log')
        table = self.screen.query_one('#messages')

        # Process the output as it becomes available
        log.write(f'[bold magenta]multimon-ng: {message.output}')
        sendFunctionCode = True  # Change as needed
        useTimestamp = True       # Change as needed
        EASOpts = None            # Modify based on options needed for EAS decoding
        frag = {}
        current_time, timestamp, address, message = parse_line(message.output)
        self.log('Adding a row')
        if message:
            table.add_row(str(timestamp.strftime('%H:%M:%S')), Text(address, justify='right'), message, height=None)
        else:
            log.write('WARNING: No valid message decoded from multimon-ng')
        try:
            table.action_scroll_bottom()
        except SkipAction:
            pass

        message_col_width = table.columns['time'].get_render_width(table) + table.columns['address'].get_render_width(table)
        if table.show_vertical_scrollbar:
            scroll_padding = table.styles.scrollbar_size_vertical
        else:
            scroll_padding = 0
        table.columns["message"].width = (table.size.width - message_col_width) - (2 * table.cell_padding) - scroll_padding
        table.columns["message"].auto_width = False


class Pocsag(App):
    CSS_PATH = "pocsag.tcss"

    SCREENS = {"help": HelpScreen}

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(
            key="question_mark",
            action="app.push_screen('help')",
            description="Show help screen",
            key_display="?",
        ),
        Binding(key='c', action='clear_screen', description='Clear all panes'),
    ]

    message_count = []

    def on_mount(self):
        self.push_screen(MainScreen())

    def action_clear_screen(self) -> None:
        self.screen.query_one(DataTable).clear()
        self.screen.query_one('#log').clear()



def process_line(line, sendFunctionCode=False, useTimestamp=False, EASOpts=None, frag=None):
    address = ''
    message = False
    trimMessage = ''
    datetime_val = None

    # POCSAG parsing
    if re.search(r'POCSAG(\d+): Address:', line):
        address = re.search(r'POCSAG(\d+): Address:(.*?)Function', line).group(2).strip()

        if sendFunctionCode:
            address += re.search(r'POCSAG(\d+): Address:(.*?)Function: (\d)', line).group(3)

        if 'Alpha:' in line:
            message = re.search(r'Alpha:(.*?)$', line).group(1).strip()

            if useTimestamp:
                if re.search(r'\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', message):
                    timeString = re.search(r'\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', message).group(0)
                    datetime_val = parse_datetime(timeString, '%d %B %Y %H:%M:%S')
                    if datetime_val:
                        message = re.sub(r'\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', '', message)
                elif re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', message):
                    timeString = re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', message).group(0)
                    datetime_val = parse_datetime(timeString, '%Y-%m-%d %H:%M:%S')
                    if datetime_val:
                        message = re.sub(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', '', message)

            trimMessage = re.sub(r'<[A-Za-z]{3}>', '', message).replace('Ä', '[').replace('Ü', ']').strip()

        elif 'Numeric:' in line:
            message = re.search(r'Numeric:(.*?)$', line).group(1).strip()
            trimMessage = re.sub(r'<[A-Za-z]{3}>', '', message).replace('Ä', '[').replace('Ü', ']').strip()

    # FLEX parsing
    elif re.search(r'FLEX[:|]', line):
        address = re.search(r'FLEX[:|] ?.*?[\[|](\d*?)[\]| ]', line).group(1).strip()

        if useTimestamp:
            if re.search(r'FLEX[:|] ?\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', line):
                timeString = re.search(r'\d{2} \w+ \d{4} \d{2}:\d{2}:\d{2}', line).group(0)
                datetime_val = parse_datetime(timeString, '%d %B %Y %H:%M:%S')
            elif re.search(r'FLEX[:|] ?\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line):
                timeString = re.search(r'\d+-\d+-\d+ \d{2}:\d{2}:\d{2}', line).group(0)
                datetime_val = parse_datetime(timeString, '%Y-%m-%d %H:%M:%S')

        if re.search(r'([ |]ALN[ |]|[ |]GPN[ |]|[ |]NUM[ |])', line):
            message = re.search(r'FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |](.+)', line).group(1).strip()

            if re.search(r'[ |][0-9]{4}\/[0-9]\/F\/.[ |]', line):
                frag[address] = message
                message = False
                trimMessage = ''
            elif re.search(r'[ |][0-9]{4}\/[0-9]\/C\/.[ |]', line):
                trimMessage = frag[address] + message
                del frag[address]
            elif re.search(r'[ |][0-9]{4}\/[0-9]\/K\/.[ |]', line):
                trimMessage = message
            else:
                trimMessage = message

    # EAS parsing
    elif re.search(r'(EAS[:|]|ZCZC-)', line):
        decodedMessage = SAME.decode(line, EASOpts.excludeEvents, EASOpts.includeFIPS)
        if decodedMessage:
            if EASOpts.addressAddType:
                address = f"{decodedMessage['LLLL-ORG']}-{decodedMessage['type']}"
            else:
                address = decodedMessage["LLLL-ORG"]
            message = decodedMessage
            trimMessage = decodedMessage["MESSAGE"]
            datetime_val = int(time.time())  # Current time as Unix timestamp

    return address, message, trimMessage, datetime_val

def main():
    Pocsag().run()

if __name__ == "__main__":
    main()

