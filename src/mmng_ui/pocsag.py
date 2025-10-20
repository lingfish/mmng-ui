from __future__ import annotations

import shlex
import shutil
import sys
import asyncio
# from codecs import ignore_errors
# from itertools import zip_longest
# from operator import itemgetter
# from re import search
from subprocess import PIPE
from dataclasses import dataclass

import click
# from rich import inspect
from rich.text import Text
# from textual._two_way_dict import TwoWayDict
from textual.app import App, ComposeResult
from textual.containers import Container, Center
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import (
    Header,
    RichLog,
    DataTable,
    Footer,
    Markdown,
    Sparkline,
    Label,
    Digits,
    Rule,
)
from textual import work, events
from textual.message import Message
from textual.binding import Binding
from textual.actions import SkipAction
# from textual.widgets._data_table import ColumnKey, CellType, RowKey, CellDoesNotExist, Row

from mmng_ui.reader import ParseLine
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
    charset: str

    def __repr__(self):
        return f'Receiver: {self.receiver}\nIP address: {self.ip_address}'

@dataclass
class Executable:
    """An info class for the executables to run."""

    command: str
    resolved_path: str
    version: str | None


class UDPHandler(asyncio.DatagramProtocol):
    """Handle UDP traffic"""

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
        """This updates the things in the status pane."""
        while True:
            if self.loop.time() - self.last_activity_time > 5:
                self.status.receiver = '[wheat4]idle[/]'
            await asyncio.sleep(1)


class StatusWidget(Widget):
    """The status pane."""

    receiver = reactive('[dark_red]Not connected[/]')
    ip_address = reactive('[wheat4]None[/]')
    json_mode = reactive('[wheat4]Unknown[/]')
    charset = reactive('[wheat4]Unknown[/]')

    def render(self) -> str:
        return f'Receiver: {self.receiver}\nIP address: {self.ip_address}\nJSON mode: {self.json_mode}\nCharset: {self.charset}'


class HelpScreen(ModalScreen):
    """Help screen modal."""

    BINDINGS = [("escape,space,q,question_mark", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        text = """
# mmng-ui

## Introduction

This is a TUI utility to decode and see POCSAG messages.

mmng-ui will listen on a chosen UDP port for raw streams from software like SDR++, use
[multimon-ng](https://github.com/EliasOenal/multimon-ng) to decode it, and show you POCSAG messages in a wonderful
text interface.

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

JSON output was merged into `multimon-ng` [version 1.4.0](https://github.com/EliasOenal/multimon-ng/releases/tag/1.4.0).

[//]: # (README.md ends here)"""
        yield Markdown(text, id='help')


# class FilterScreen(ModalScreen[str]):
#     """Screen with a dialog to quit."""
#
#     BORDER_TITLE = 'Filter messages'
#
#     def compose(self) -> ComposeResult:
#         yield Input(placeholder='Enter a filter here', id='filter')
#
#     @on(Input.Submitted)
#     def handle_filter(self, event: Input.Submitted) -> None:
#         self.dismiss(event.value)

class AboutScreen(ModalScreen):
    """About/info screen modal."""

    BINDINGS = [("escape,space,q", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        mmng_info = f'''
## multimon-ng

```
Path: {self.app.mmng.resolved_path}
Version: {self.app.mmng.version}
```
        '''
        if self.app.sox_binary:
            sox_info = f'''
## sox

```
Path: {self.app.sox.resolved_path}
Version: {self.app.sox.version}
```
        '''
        with Container(id='about'):
            yield Markdown('# This is mmng-ui!')
            with Center():
                yield Label("Version", classes='version')
            with Center():
                yield Digits(__version__, classes='version')
            yield Rule(line_style="double")
            yield Markdown(mmng_info)
            if self.app.sox_binary:
                yield Markdown(sox_info)


class MsgsPerSecond(Sparkline):
    """Calculate/update the messages per second sparkline."""

    def __init__(self, samples=[0] * 60, **kwargs):
        super().__init__(**kwargs)
        self.samples = samples

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1, self.update_graph)
        self.data = self.samples

    def update_graph(self) -> None:
        self.data = self.data[-59:] + [len(self.app.message_count)]
        self.app.message_count = []


# class DataTableFilter(DataTable):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self._unfiltered_data = None
#         self._unfiltered_rows = None
#         self._search_term = None
#         self._search_column = None
#
#     async def filter(self, column: str, search: str) -> Self:
#         self._search_term = search
#         self._search_column = column
#         if search == '':
#             if self._unfiltered_data is not None:
#                 self._data = self._unfiltered_data
#                 self._unfiltered_data = None
#
#                 self.rows = self._unfiltered_rows
#                 self._unfiltered_rows = None
#                 self.border_title = 'POCSAG messages'
#         else:
#             if self._unfiltered_data is None:
#                 self._unfiltered_data = self._data
#                 self._unfiltered_rows = self.rows
#
#             self._data = dict(
#                 filter(
#                     lambda x: True if search.lower() in str(x[1][column]).lower() else False,
#                     self._unfiltered_data.items(),
#                 )
#             )
#             self.rows = {row_key: self._unfiltered_rows[row_key] for row_key in self._data.keys()}
#             self.border_title = 'POCSAG messages (filter applied)'
#
#         self._row_locations = TwoWayDict({key: new_index for new_index, (key, _) in enumerate(self._data.items())})
#         self._update_count += 1
#         self._require_update_dimensions = True
#         self.refresh()
#         return self
#
#     @property
#     def filter_active(self) -> bool:
#         return self._search_term != ''
#
#     async def filter_refresh(self) -> None:
#         if self.filter_active:
#             await self.filter(self._search_column, '')
#             await self.filter(self._search_column, self._search_term)
#
#     def update_cell(
#         self, row_key: RowKey | str, column_key: ColumnKey | str, value: CellType, *, update_width: bool = False
#     ) -> None:
#         if self._unfiltered_data is not None:
#             try:
#                 self._unfiltered_data[row_key][column_key] = value
#             except KeyError:
#                 raise CellDoesNotExist(f'No cell exists for row_key={row_key!r}, column_key={column_key!r}.') from None
#
#         return super().update_cell(row_key, column_key, value, update_width=update_width)
#
#     def clear(self, columns: bool = False) -> Self:
#         self._unfiltered_data = None
#         self._unfiltered_rows = None
#         return super().clear(columns)
#
#     def add_column(
#         self, label: TextType, *, width: int | None = None, key: str | None = None, default: CellType | None = None
#     ) -> ColumnKey:
#         column_key = super().add_column(label, width=width, key=key, default=default)
#
#         if self._unfiltered_data is not None:
#             for row_key in self._unfiltered_rows.keys():
#                 self._unfiltered_data[row_key][column_key] = default
#
#         return column_key
#
#     def add_row(
#         self, *cells: CellType, height: int = 1, key: str | None = None, label: TextType | None = None
#     ) -> RowKey:
#         row_key = super().add_row(*cells, height=height, key=key, label=label)
#
#         if self._unfiltered_data is not None:
#             self._unfiltered_data[row_key] = {
#                 column.key: cell for column, cell in zip_longest(self.ordered_columns, cells)
#             }
#             label = Text.from_markup(label) if isinstance(label, str) else label
#             self._unfiltered_rows[row_key] = Row(row_key, height, label)
#
#         return row_key
#
#     def remove_row(self, row_key: RowKey | str) -> None:
#         super().remove_row(row_key)
#         if self._unfiltered_data is not None:
#             del self._unfiltered_rows[row_key]
#             del self._unfiltered_data[row_key]
#
#     def remove_column(self, column_key: ColumnKey | str) -> None:
#         super().remove_column(column_key)
#
#         if self._unfiltered_data is not None:
#             for row in self._unfiltered_data:
#                 del self._unfiltered_data[row][column_key]


class MainScreen(Screen):
    def compose(self):
        yield Header()
        with Container(id='app-grid'):
            yield DataTable(id='messages')
            yield RichLog(id='log', highlight=True, markup=True)
            with Container(id='status-container'):
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
        table.border_title = 'Messages'
        log.border_title = 'Log window'
        status.border_title = 'Status'

        self.parse_line = ParseLine()

        # Run multimon-ng, grab version and JSON support
        mmng_help_process = await asyncio.create_subprocess_exec(self.app.mmng_binary, '-h', stderr=PIPE)
        mmng_help = await mmng_help_process.stderr.read()
        await mmng_help_process.wait()
        mmng_text = mmng_help.decode()
        json_capable = '--json' in mmng_text
        self.app.mmng.version = mmng_text.splitlines()[0].split()[1]
        log.write(f'multimon-ng version: {self.app.mmng.version}')
        log.write(f'JSON capable: {json_capable}')

        if self.app.sox_binary:
            sox_help_process = await asyncio.create_subprocess_exec(self.app.sox_binary, '--version', stdout=PIPE)
            sox_help = await sox_help_process.stdout.read()
            await sox_help_process.wait()
            sox_text = sox_help.decode()
            self.app.sox.version = sox_text.splitlines()[0].split()[2].lstrip('v')
            log.write(f'sox version: {self.app.sox.version}')
        status.charset = self.app.charset
        mmng_args = f'-a POCSAG512 -a POCSAG1200 -a POCSAG2400 -a FLEX -a FLEX_NEXT -f alpha -t raw -u -q --timestamp -p {"--json" if json_capable else ""} -C {self.app.charset} -'
        self.log('About to start multimon')
        self.stream_subprocess(self.app.mmng_binary, mmng_args)
        self.log('AFTER: About to start multimon')

    @work(exclusive=True)
    async def stream_subprocess(self, command, args):
        """Stream output from a subprocess and post it using post_message."""
        self.log('   in stream_subprocess')
        self.process = await asyncio.create_subprocess_exec(
            command, *shlex.split(args), stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        self.log('*** process is assigned')

        network_loop = asyncio.get_running_loop()
        transport, protocol = await network_loop.create_datagram_endpoint(
            lambda: UDPHandler(self, network_loop), local_addr=('::', self.app.port)
        )
        network_loop.create_task(protocol.idle_task())

        # Stream stdout asynchronously
        async for line in self.read_process_output(self.process.stdout):
            self.log(f'Raw output from multimon: {line}')
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
        table = self.screen.query_one('#messages')
        self.recalc_width(table)

    async def watch_show_vertical_scrollbar(self) -> None:
        table = self.screen.query_one('#messages')
        self.recalc_width(table)

    async def on_output_message(self, message: OutputMessage):
        """Handle OutputMessage to update UI components."""
        log = self.screen.query_one('#log')
        table = self.screen.query_one('#messages')
        status = self.screen.query_one('#status')

        self.log(f'RECEIVED EVENT: {message}')
        # Process the output as it becomes available
        log.write(f'[bold magenta]multimon-ng: {message.output}')

        result, json_detected = self.parse_line.parse(message.output)
        self.log(f'result: {result}')

        status.json_mode = json_detected

        if message and result.trim_message:
            self.log('Adding a row')
            table.add_row(
                str(result.current_time.strftime('%H:%M:%S')),
                Text(str(result.address), justify='right'),
                result.trim_message,
                height=None,
            )
            # await table.filter_refresh()
        else:
            log.write('WARNING: No valid message decoded from multimon-ng')

        self.recalc_width(table)

    def recalc_width(self, table) -> None:
        message_col_width = table.columns['time'].get_render_width(table) + table.columns['address'].get_render_width(
            table
        )
        if table.show_vertical_scrollbar:
            scroll_padding = table.styles.scrollbar_size_vertical
        else:
            scroll_padding = 0
        table.columns['message'].width = (
            (table.size.width - message_col_width) - (2 * table.cell_padding) - scroll_padding
        )
        table.columns['message'].auto_width = False
        try:
            table.action_scroll_bottom()
        except SkipAction:
            pass


class Pocsag(App):
    def __init__(self, mmng_binary: str, port: int, charset: str, sox_binary: str | None) -> None:
        self.mmng_binary = mmng_binary
        self.sox_binary = sox_binary
        self.port = port
        self.charset = charset
        self.mmng = Executable(command=mmng_binary, resolved_path=shutil.which(mmng_binary), version=None)
        if sox_binary:
            self.sox = Executable(command=sox_binary, resolved_path=shutil.which(sox_binary) or None, version=None)
        # self.filter: str = None
        super().__init__()

    CSS_PATH = 'pocsag.tcss'

    # SCREENS = {'help': HelpScreen, 'filter': FilterScreen}
    SCREENS = {'help': HelpScreen}

    BINDINGS = [
        Binding(key='q', action='quit', description='Quit the app'),
        Binding(
            key='question_mark',
            action="app.push_screen('help')",
            description='Show help screen',
            key_display='?',
        ),
        Binding(key='c', action='clear_screen', description='Clear all panes'),
        Binding(
            key='a',
            action="about",
            description='About/info',
            key_display='a',
        ),
        # Binding(key='/', action='filter', description='Filter the messages'),
    ]

    message_count = []

    def on_mount(self):
        self.push_screen(MainScreen())

    def action_clear_screen(self) -> None:
        self.screen.query_one('#messages').clear()
        self.screen.query_one('#log').clear()
    #
    # async def action_filter(self) -> None:
    #     async def check_filter(filter: str | None) -> None:
    #         """Called when FilterScreen is dismissed."""
    #         table = self.screen.query_one('#messages')
    #         self.log(filter)
    #         self.filter = filter
    #         await table.filter('message', search=self.filter)
    #
    #     await self.push_screen(FilterScreen(), check_filter)

    def action_about(self) -> None:
        self.push_screen(AboutScreen())

@click.command(context_settings={'show_default': True})
@click.option('--mmng-binary', '-m', required=False, default='multimon-ng', help='Path to multimon-ng binary')
@click.option('--sox-binary', '-s', required=False, help='Path to sox binary')
@click.option('--port', '-p', required=False, type=int, default=8888, help='Port to listen on')
@click.option(
    '--charset',
    '-c',
    type=click.Choice(['US', 'FR', 'DE', 'SE', 'SI'], case_sensitive=False),
    required=False,
    default='US',
    help='Charset encoding (case sensitive!)',
)
@click.option('--serve', required=False, is_flag=True, default=False, help='Serve the app via the web')
@click.option('--serve-host', required=False, type=str, help='Host/IP to serve the app on (when using --serve)')
@click.option('--serve-port', required=False, type=int, help='Port to serve the app on (when using --serve)')
@click.version_option(version=__version__)
def main(mmng_binary, sox_binary, port, charset, serve, serve_host, serve_port):
    if serve or serve_host or serve_port:
        if not serve:
            serve = True
        if not serve_host:
            serve_host = None
        if not serve_port:
            serve_port = 8000

        try:
            from textual_serve.server import Server
            import socket
            if serve_host == 'localhost':
                public_url = f'http://localhost:{serve_port}'
            else:
                public_url = f'http://{socket.getfqdn()}:{serve_port}'
            server = Server(command='mmng-ui', host=serve_host, port=serve_port, public_url=public_url)
            server.serve()
        except ImportError:
            click.echo('Error: textual-serve is not installed.  Please install mmng-ui via "pipx install mmng-ui[web]"', err=True)
            sys.exit(1)

    else:
        if not shutil.which(mmng_binary):
            click.echo(f'multimon-ng binary not found!  I searched for "{mmng_binary}"', err=True)
            sys.exit(1)

        Pocsag(mmng_binary=mmng_binary, sox_binary=sox_binary, port=port, charset=charset).run()


if __name__ == '__main__':
    main()
