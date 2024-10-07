import shlex
import shutil
import sys
import asyncio
from subprocess import PIPE
from dataclasses import dataclass
import json

import click
from rich.text import Text
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

from mmng_ui.reader import ParseLine, PocsagMessage
from mmng_ui._version import __version__



@dataclass
class OutputMessage(Message, bubble=False):
    """Custom message class to handle subprocess output."""
    output: str


@dataclass
class Status:
    """The status pane"""

    receiver: str
    ip_address: str
    json_mode: bool

    def __repr__(self):
        return f'Receiver: {self.receiver}\nIP address: {self.ip_address}'

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
        self.last_activity_time = self.loop.time()
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
    json_mode = reactive('[wheat4]Unknown[/]')

    def render(self) -> str:
        return f'Receiver: {self.receiver}\nIP address: {self.ip_address}\nJSON mode: {self.json_mode}'


class HelpScreen(ModalScreen):
    """Help screen modal."""

    BINDINGS = [("escape,space,q,question_mark", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        text = """
# mmng-ui

## Introduction

This is a TUI utility to decode and see POCSAG messages.

mmng-ui will listen on a chosen UDP port for raw streams from software like SDR++, use multimon-ng to decode it, and
show you POCSAG messages in a wonderful text interface.

## Usage

Alpha POCSAG messages will display in the top pane.  The bottom pane will show the raw output from `multimon-ng`,
as well as any errors or issues with decoding.

The status panel shows any incoming connections.  Receiver will transition between the following states:

| Receiver state | Description                                     |
|----------------|-------------------------------------------------|
| idle           | No UDP traffic yet seen, or seen in 5 seconds   |
| receiving      | Actively receiving a decode from `multimon-ng`  |
| waiting        | Traffic is coming in, but nothing to be decoded |

Just below the status panel is a sparkline -- this updates on each decode, and reflects character length of said
decode.

Underneath the log window in another sparkline, and this shows messages per second, for the last minute.

The footer shows available keyboard choices to quit the app, show a help screen, and clear all logging panes.

The mouse will also work!

## JSON mode

`mmng-ui` will attempt to auto-detect the output format from `multimon-ng`, and if it looks like JSON, it'll use it.

JSON output isn't yet in `multimon-ng`, but I have a working
fork [here](https://github.com/lingfish/multimon-ng/tree/add-json).

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
        self.data = self.data[-59:] + [len(self.app.message_count)]
        self.app.message_count = []


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
        log.border_title = 'Log window'
        status.border_title = 'Status'

        self.parse_line = ParseLine()

        # Run multimon-ng, grab version and JSON support
        mmng_help_process = await asyncio.create_subprocess_exec(self.app.mmng_binary, '-h', stderr=PIPE)
        mmng_help = await mmng_help_process.stderr.read()
        await mmng_help_process.wait()
        mmng_text = mmng_help.decode()
        json_capable = '--json' in mmng_text
        log.write(f'multimon-ng version: {mmng_text.splitlines()[0]}')
        log.write(f'JSON capable: {json_capable}')

        mmng_args = f'-a POCSAG512 -a POCSAG1200 -a POCSAG2400 -f alpha -t raw -u -q --timestamp -p {"--json" if json_capable else ""} -'
        self.log('About to start multimon')
        self.stream_subprocess(self.app.mmng_binary, mmng_args)
        self.log('AFTER: About to start multimon')

    @work(exclusive=True)
    async def stream_subprocess(self, command, args):
        """Stream output from a subprocess and post it using post_message."""
        self.log('   in stream_subprocess')
        self.process = await asyncio.create_subprocess_exec(
            command,
            *shlex.split(args),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE
        )
        self.log('*** process is assigned')

        network_loop = asyncio.get_running_loop()
        transport, protocol = await network_loop.create_datagram_endpoint(
            lambda: UDPHandler(self, network_loop),
            local_addr=('::', self.app.port)
        )
        network_loop.create_task(protocol.idle_task())

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

    async def watch_show_vertical_scrollbar(self) -> None:
        log = self.screen.query_one('#log')
        log.write('scrollbar appeared!')

    async def on_output_message(self, message: OutputMessage):
        """Handle OutputMessage to update UI components."""
        log = self.screen.query_one('#log')
        table = self.screen.query_one('#messages')
        status = self.screen.query_one('#status')

        # Process the output as it becomes available
        log.write(f'[bold magenta]multimon-ng: {message.output}')

        # result = PocsagMessage()
        result, json_detected = self.parse_line.parse(message.output)

        status.json_mode = json_detected

        self.log('Adding a row')
        if message:
            table.add_row(str(result.current_time.strftime('%H:%M:%S')), Text(result.address, justify='right'), result.trim_message, height=None)
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
    def __init__(self, mmng_binary: str, port:int) -> None:
        self.mmng_binary = mmng_binary
        self.port = port
        super().__init__()

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



@click.command()
@click.option('--mmng-binary', '-m', required=False, default='multimon-ng', help='Path to multimon-ng binary')
@click.option('--port', '-p', required=False, type=int, default=8888, help='Port to listen on')
@click.version_option(version=__version__)
def main(mmng_binary, port):
    if not shutil.which(mmng_binary):
        click.echo('multimon-ng binary not found!', err=True)
        sys.exit(1)

    Pocsag(mmng_binary, port).run()

if __name__ == "__main__":
    main()

