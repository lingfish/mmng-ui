from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from subprocess import PIPE

import click
from rich.emoji import EMOJI
from rich.text import Text
from textual import events, work
from textual.actions import SkipAction
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import (
    ContentSwitcher,
    DataTable,
    Digits,
    Footer,
    Header,
    Label,
    Markdown,
    RichLog,
    Rule,
    Sparkline,
    TabbedContent,
    TabPane,
)

from mmng_ui._version import __version__
from mmng_ui.capcode_db import CapcodeDB
from mmng_ui.reader import ParseLine


def parse_ports(port_str: str) -> list[int]:
    """Parse a comma-separated port string into a list of integers."""
    if not port_str:
        raise ValueError('Port string cannot be empty')
    ports = []
    for part in port_str.split(','):
        stripped = part.strip()
        if not stripped:
            raise ValueError(f'Invalid port string: {port_str!r}')
        try:
            ports.append(int(stripped))
        except ValueError:
            raise ValueError(f'Invalid port value: {stripped!r}')
    return ports


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

    def __init__(self, app, loop, port):
        self.app = app
        self.loop = loop
        self.port = port
        self.status = self.app.query_one(f'#status-{port}')
        self.last_activity_time = 0

    def connection_made(self, transport):
        self.transport = transport
        self.status.receiver = 'ready'

    def connection_lost(self, exc):
        self.status.receiver = 'Closed'

    def datagram_received(self, data, addr):
        self.last_activity_time = self.loop.time()
        self.status.ip_address = addr[0]
        if self.app.app.sox_rate:
            stdin = self.app.sox_process.stdin
        else:
            stdin = self.app.process.stdin
        stdin.write(data)
        stdin.drain()

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

    BINDINGS = [('escape,space,q,question_mark', 'app.pop_screen', 'Close')]

    def compose(self) -> ComposeResult:
        text = """
# mmng-ui

## Introduction

This is a TUI utility to decode and see POCSAG messages.

mmng-ui will listen on chosen UDP ports for raw streams from software like SDR++, use
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


class AboutScreen(ModalScreen):
    """About/info screen modal."""

    BINDINGS = [('escape,space,q', 'app.pop_screen', 'Close')]

    def compose(self) -> ComposeResult:
        mmng_info = f'''
## multimon-ng

```
Path: {self.app.mmng.resolved_path}
Version: {self.app.mmng.version}
```
        '''
        if self.app.sox_rate:
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
                yield Label('Version', classes='version')
            with Center():
                yield Digits(__version__, classes='version')
            yield Rule(line_style='double')
            with Container(id='app-versions'):
                yield Markdown(mmng_info)
                if self.app.sox_rate:
                    yield Markdown(sox_info)




class MsgsPerSecond(Sparkline):
    """Calculate/update the messages per second sparkline."""

    def __init__(self, samples=None, message_count_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.samples = samples if samples is not None else [0] * 60
        self.message_count_ref = message_count_ref

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1, self.update_graph)
        self.data = self.samples
        self.styles.height = '1'

    def update_graph(self) -> None:
        count = len(self.message_count_ref)
        self.data = self.data[-59:] + [count]
        self.message_count_ref.clear()


class FeedTabbedContent(TabbedContent):
    """TabbedContent with height: 1fr to override TabbedContent's DEFAULT_CSS height: auto."""

    DEFAULT_CSS = """
    FeedTabbedContent {
        height: 1fr;
    }
    """

    def on_mount(self) -> None:
        switcher = self.get_child_by_type(ContentSwitcher)
        switcher.styles.height = '1fr'


class FeedTabPane(TabPane):
    """TabPane with height: 100% to override TabPane's DEFAULT_CSS height: auto."""

    DEFAULT_CSS = """
    FeedTabPane {
        height: 100%;
    }
    """


class FeedWidget(Widget):
    """A widget representing a single POCSAG feed on one UDP port."""

    def __init__(self, port: int, capcode_db: CapcodeDB | None = None, **kwargs):
        super().__init__(**kwargs)
        self.port = port
        self.capcode_db = capcode_db
        self.process = None
        self.sox_process = None
        self.message_count = []

    DEFAULT_CSS = """
FeedWidget {
    height: 100%;
    layout: vertical;
}
"""

    def compose(self) -> ComposeResult:
        with Widget(classes='feed-grid'):
            yield DataTable(id=f'messages-{self.port}', classes='feed-messages')
            yield RichLog(id=f'log-{self.port}', highlight=True, markup=True, classes='feed-log')
            with Widget(classes='feed-status-container'):
                yield StatusWidget(id=f'status-{self.port}', classes='feed-status')
                yield Sparkline([], id=f'spark-{self.port}')
        yield MsgsPerSecond(id=f'msgs-per-second-{self.port}', message_count_ref=self.message_count, classes='feed-mps')

    async def on_mount(self) -> None:
        """Setup the initial UI components."""
        table = self.query_one(f'#messages-{self.port}')
        log = self.query_one(f'#log-{self.port}')
        status = self.query_one(f'#status-{self.port}')
        spark = self.query_one(f'#spark-{self.port}')

        # Inline styles override DEFAULT_CSS for proper grid stretching
        table.styles.height = '100%'
        spark.styles.height = '100%'

        table.add_column('Time', key='time')
        table.add_column('Address', key='address')
        table.add_column('Message', key='message')
        table.cursor_type = 'none'
        table.columns['message'].auto_width = False
        table.border_title = 'Messages'
        log.border_title = 'Log window'
        status.border_title = 'Status'

        self.parse_line = ParseLine()

        status.charset = self.app.charset

    def on_resize(self, event: events.Resize) -> None:
        table = self.query_one(f'#messages-{self.port}')
        if not table.columns or not table.visible:
            return
        time_w = table.columns['time'].get_render_width(table)
        addr_w = table.columns['address'].get_render_width(table)
        scroll_pad = table.styles.scrollbar_size_vertical if table.show_vertical_scrollbar else 0
        available = (table.size.width - time_w - addr_w
                     - (2 * table.cell_padding) - scroll_pad)
        table.columns['message'].width = max(available, 20)

    def start_streaming(self):
        """Build multimon-ng args and start the subprocess/UDP pipeline."""
        if getattr(self.app, '_streaming_disabled', False):
            return
        log = self.query_one(f'#log-{self.port}')
        log.write(f'multimon-ng version: {self.app.mmng.version}')
        log.write(f'JSON capable: {self.app.json_capable}')
        mmng_args = f'-a POCSAG512 -a POCSAG1200 -a POCSAG2400 -a FLEX -a FLEX_NEXT -f alpha -t raw -u -q --timestamp -p {"--json" if self.app.json_capable else ""} -C {self.app.charset} -'
        self.stream_subprocess(self.app.mmng_binary, mmng_args)

    @work(exclusive=True)
    async def stream_subprocess(self, command, args):
        """Stream output from a subprocess and post it using post_message."""
        if self.app.sox_rate:
            sox_args = f'-t raw -esigned-integer -b16 -r{self.app.sox_rate} - -t raw -esigned-integer -b16 -r22050 -'
            sox_read, sox_write = os.pipe()
            self.sox_process = await asyncio.create_subprocess_exec(
                self.app.sox_binary, *shlex.split(sox_args), stdin=PIPE, stdout=sox_write, stderr=PIPE
            )
            os.close(sox_write)

            self.process = await asyncio.create_subprocess_exec(
                command, *shlex.split(args), stdin=sox_read, stdout=PIPE, stderr=PIPE
            )
            os.close(sox_read)
        else:
            self.process = await asyncio.create_subprocess_exec(
                command, *shlex.split(args), stdin=PIPE, stdout=PIPE, stderr=PIPE
            )

        network_loop = asyncio.get_running_loop()
        transport, protocol = await network_loop.create_datagram_endpoint(
            lambda: UDPHandler(self, network_loop, self.port), local_addr=('::', self.port)
        )
        network_loop.create_task(protocol.idle_task())

        # Stream stdout asynchronously
        async for line in self.read_process_output(self.process.stdout):
            self.post_message(OutputMessage(line))
            self.set_timer(1, lambda: setattr(self.query_one(f'#status-{self.port}'), 'receiver', '[dark_green]waiting[/]'))
            self.query_one(f'#spark-{self.port}').data = self.query_one(f'#spark-{self.port}').data[-9:] + [len(line)]
            self.message_count.append(1)

        # Handle any stderr errors
        async for error in self.read_process_output(self.process.stderr):
            self.post_message(OutputMessage(f'[red]Error: {error}'))
        async for error in self.read_process_output(self.sox_process.stderr):
            self.post_message(OutputMessage(f'[red]Error: {error}'))

    async def read_process_output(self, output):
        """Read the output of a subprocess line by line."""
        status = self.query_one(f'#status-{self.port}')
        while True:
            status.receiver = '[blink bold bright_green]receiving[/]'
            line = await output.readline()
            if not line:
                break
            yield line.decode().strip()

    async def on_output_message(self, message: OutputMessage):
        """Handle OutputMessage to update UI components."""
        log = self.query_one(f'#log-{self.port}')
        table = self.query_one(f'#messages-{self.port}')
        status = self.query_one(f'#status-{self.port}')

        # Process the output as it becomes available
        log.write(f'[bold magenta]multimon-ng: {message.output}')

        result, json_detected = self.parse_line.parse(message.output)

        status.json_mode = json_detected

        if result.trim_message:
            raw_address = str(result.address)
            entry = self.capcode_db.lookup(raw_address) if self.capcode_db else None
            if entry:
                emoji = EMOJI.get(entry.icon, '') if entry.icon else ''
                prefix = f'{emoji} ' if emoji else ''
                addr_renderable = Text(f'{prefix}{entry.alias}', style=entry.color or '', justify='right')
                addr_renderable.append(f' ({raw_address})', style='dim')
            else:
                addr_renderable = Text(raw_address, justify='right')
            table.add_row(
                str(result.current_time.strftime('%H:%M:%S')),
                addr_renderable,
                Text(result.trim_message, overflow='fold'),
                height=None,
            )
        else:
            log.write('WARNING: No valid message decoded from multimon-ng')

        try:
            table.action_scroll_bottom()
        except SkipAction:
            pass

    def clear(self):
        self.query_one(f'#messages-{self.port}').clear()
        self.query_one(f'#log-{self.port}').clear()


class MainScreen(Screen):
    def compose(self):
        yield Header()
        with FeedTabbedContent():
            for port in self.app.ports:
                with FeedTabPane(f'Port {port}', id=f'tab-{port}'):
                    yield FeedWidget(port=port, capcode_db=self.app.capcode_db)
        yield Footer()

    async def on_mount(self) -> None:
        """Setup the initial components."""
        self.title = 'multimon-ng decoder'
        version, json_capable = await self._detect_mmng_version()
        self.app.mmng.version = version
        self.app.json_capable = json_capable
        for feed in self.query(FeedWidget):
            feed.start_streaming()

    async def _detect_mmng_version(self) -> tuple[str, bool]:
        """Returns (version_string, json_capable)."""
        try:
            mmng_help_process = await asyncio.create_subprocess_exec(self.app.mmng_binary, '-h', stderr=PIPE)
            mmng_help = await mmng_help_process.stderr.read()
            await mmng_help_process.wait()
            mmng_text = mmng_help.decode()
            json_capable = '--json' in mmng_text
            version = mmng_text.splitlines()[0].split()[1]
            return version, json_capable
        except OSError:
            return '0.0.0', False


class Pocsag(App):
    def __init__(self, mmng_binary: str, ports: list[int], charset: str, sox_binary: str | None, sox_rate: int | None, capcode_db: CapcodeDB | None = None) -> None:
        self.mmng_binary = mmng_binary
        self.sox_binary = sox_binary
        self.ports = ports
        self.charset = charset
        self.sox_rate = sox_rate
        self.capcode_db = capcode_db
        self.mmng = Executable(command=mmng_binary, resolved_path=shutil.which(mmng_binary), version=None)
        if self.sox_binary and self.sox_rate:
            self.sox = Executable(command=sox_binary, resolved_path=shutil.which(sox_binary) or None, version=None)
        self.json_capable = False
        super().__init__()

    CSS_PATH = 'pocsag.tcss'

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
            action='about',
            description='About/info',
            key_display='a',
        ),
    ]

    def on_mount(self):
        self.push_screen(MainScreen())

    def action_clear_screen(self) -> None:
        tabs = self.screen.query_one(FeedTabbedContent)
        if (pane := tabs.active_pane) is not None:
            pane.query_one(FeedWidget).clear()

    def action_about(self) -> None:
        self.push_screen(AboutScreen())


def _serve_mode(host: str | None, port: int) -> None:
    """Handle serve mode logic."""
    try:
        import socket

        from textual_serve.server import Server
        if host == 'localhost':
            public_url = f'http://localhost:{port}'
        else:
            public_url = f'http://{socket.getfqdn()}:{port}'
        server = Server(command='mmng-ui', host=host, port=port, public_url=public_url)
        server.serve()
    except ImportError:
        click.echo('Error: textual-serve is not installed.  Please install mmng-ui via "pipx install mmng-ui[web]"', err=True)
        sys.exit(1)


@click.command(context_settings={'show_default': True})
@click.option('--mmng-binary', '-m', required=False, default='multimon-ng', help='Path to multimon-ng binary')
@click.option('--sox-binary', '-s', required=False, default='sox', help='Path to sox binary (this does not imply that sox will run')
@click.option('--sox-rate', '-r', required=False, type=str, help='Input samplerate for sox to convert from')
@click.option('--port', '-p', required=False, default='8888', help='Port(s) to listen on (comma-separated)')
@click.option(
    '--charset',
    '-c',
    type=click.Choice(['US', 'FR', 'DE', 'SE', 'SI'], case_sensitive=False),
    required=False,
    default='US',
    help='Charset encoding (case sensitive!)',
)
@click.option('--capcodes', '-k', required=False, type=str, help='Path to capcode database (JSON or CSV)')
@click.option('--serve', required=False, is_flag=True, default=False, help='Serve the app via the web')
@click.option('--serve-host', required=False, type=str, help='Host/IP to serve the app on (when using --serve)')
@click.option('--serve-port', required=False, type=int, help='Port to serve the app on (when using --serve)')
@click.version_option(version=__version__)
def main(mmng_binary, sox_binary, sox_rate, port, charset, capcodes, serve, serve_host, serve_port):
    if serve or serve_host or serve_port:
        if not serve:
            serve = True
        if not serve_host:
            serve_host = None
        if not serve_port:
            serve_port = 8000
        _serve_mode(serve_host, serve_port)

    else:
        if not shutil.which(mmng_binary):
            click.echo(f'multimon-ng binary not found!  I searched for "{mmng_binary}"', err=True)
            sys.exit(1)

        if sox_rate:
            if not shutil.which(sox_binary):
                click.echo(f'sox binary not found!  I searched for "{sox_binary}"', err=True)
                sys.exit(1)

        ports = parse_ports(port)
        capcode_db = CapcodeDB.load(capcodes) if capcodes else None
        Pocsag(mmng_binary=mmng_binary, sox_binary=sox_binary, sox_rate=sox_rate, ports=ports, charset=charset, capcode_db=capcode_db).run()


if __name__ == '__main__':
    main()
