import importlib
import sys

import pytest
from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import Digits, Footer, Header, Markdown

from mmng_ui.pocsag import (
    AboutScreen,
    Executable,
    HelpScreen,
    MainScreen,
    MsgsPerSecond,
    OutputMessage,
    Status,
    StatusWidget,
    _serve_mode,
)


class StatusApp(App):
    def compose(self) -> ComposeResult:
        yield StatusWidget(id='test-status')


def test_output_message():
    """Test OutputMessage dataclass."""
    msg = OutputMessage("test output")
    assert isinstance(msg, Message)
    assert msg.output == "test output"


def test_status_dataclass():
    """Test Status dataclass."""
    status = Status(
        receiver="test_receiver",
        ip_address="192.168.1.1",
        json_mode=True,
        charset="US"
    )
    assert status.receiver == "test_receiver"
    assert status.ip_address == "192.168.1.1"
    assert status.json_mode is True
    assert status.charset == "US"

    # Test __repr__
    repr_str = repr(status)
    assert "Receiver: test_receiver" in repr_str
    assert "IP address: 192.168.1.1" in repr_str


def test_executable_dataclass():
    """Test Executable dataclass."""
    # Test with resolved_path
    exec_with_path = Executable(
        command="test_cmd",
        resolved_path="/usr/bin/test_cmd",
        version="1.0.0"
    )
    assert exec_with_path.command == "test_cmd"
    assert exec_with_path.resolved_path == "/usr/bin/test_cmd"
    assert exec_with_path.version == "1.0.0"

    # Test with None resolved_path
    exec_none_path = Executable(
        command="test_cmd",
        resolved_path=None,
        version=None
    )
    assert exec_none_path.command == "test_cmd"
    assert exec_none_path.resolved_path is None
    assert exec_none_path.version is None


@pytest.mark.asyncio
async def test_status_widget_render():
    """Test StatusWidget render method."""
    async with StatusApp().run_test() as pilot:
        status = pilot.app.query_one('#test-status')

        # Check default render output
        rendered = status.render()
        assert 'Receiver: [dark_red]Not connected[/]' in rendered
        assert 'IP address: [wheat4]None[/]' in rendered
        assert 'JSON mode: [wheat4]Unknown[/]' in rendered
        assert 'Charset: [wheat4]Unknown[/]' in rendered

        # Change reactive attributes and check render updates
        status.receiver = '[green]receiving[/]'
        status.ip_address = '[blue]192.168.1.100[/]'
        status.json_mode = '[yellow]Yes[/]'
        status.charset = '[cyan]FR[/]'

        rendered = status.render()
        assert 'Receiver: [green]receiving[/]' in rendered
        assert 'IP address: [blue]192.168.1.100[/]' in rendered
        assert 'JSON mode: [yellow]Yes[/]' in rendered
        assert 'Charset: [cyan]FR[/]' in rendered


# HelpScreen tests
@pytest.mark.asyncio
async def test_help_screen_compose():
    """Test HelpScreen composes correctly."""
    async with App().run_test() as pilot:
        pilot.app.push_screen(HelpScreen())
        await pilot.pause()
        help_widget = pilot.app.screen.query_one('#help')
        assert isinstance(help_widget, Markdown)


@pytest.mark.asyncio
async def test_help_screen_dismiss_escape():
    """Test HelpScreen dismisses with escape key."""
    async with App().run_test() as pilot:
        pilot.app.push_screen(HelpScreen())
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        await pilot.press('escape')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_help_screen_dismiss_q():
    """Test HelpScreen dismisses with q key."""
    async with App().run_test() as pilot:
        pilot.app.push_screen(HelpScreen())
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        await pilot.press('q')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_help_screen_dismiss_space():
    """Test HelpScreen dismisses with space key."""
    async with App().run_test() as pilot:
        pilot.app.push_screen(HelpScreen())
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        await pilot.press('space')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, HelpScreen)


# AboutScreen tests
class AboutScreenApp(App):
    def __init__(self, has_sox: bool = False):
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.sox_rate = 48000 if has_sox else None
        if has_sox:
            self.sox = Executable('sox', '/usr/bin/sox', '14.4.2')
        super().__init__()


@pytest.mark.asyncio
async def test_about_screen_without_sox():
    """Test AboutScreen without sox shows mmng info but not sox info."""
    async with AboutScreenApp(has_sox=False).run_test() as pilot:
        pilot.app.push_screen(AboutScreen())
        await pilot.pause()
        about_screen = pilot.app.screen
        digits = about_screen.query_one(Digits)
        assert digits is not None
        versions = about_screen.query_one('#app-versions')
        assert len(versions.children) == 1
        mmng_md = versions.children[0]
        assert isinstance(mmng_md, Markdown)
        assert '/usr/bin/multimon-ng' in str(mmng_md._markdown)
        assert '1.4.0' in str(mmng_md._markdown)


@pytest.mark.asyncio
async def test_about_screen_with_sox():
    """Test AboutScreen with sox shows both mmng and sox info."""
    async with AboutScreenApp(has_sox=True).run_test() as pilot:
        pilot.app.push_screen(AboutScreen())
        await pilot.pause()
        about_screen = pilot.app.screen
        digits = about_screen.query_one(Digits)
        assert digits is not None
        versions = about_screen.query_one('#app-versions')
        assert len(versions.children) == 2
        mmng_md = versions.children[0]
        sox_md = versions.children[1]
        assert isinstance(mmng_md, Markdown)
        assert isinstance(sox_md, Markdown)
        assert '/usr/bin/multimon-ng' in str(mmng_md._markdown)
        assert '1.4.0' in str(mmng_md._markdown)
        assert '/usr/bin/sox' in str(sox_md._markdown)
        assert '14.4.2' in str(sox_md._markdown)


@pytest.mark.asyncio
async def test_about_screen_dismiss_escape():
    """Test AboutScreen dismisses with escape key."""
    async with AboutScreenApp().run_test() as pilot:
        pilot.app.push_screen(AboutScreen())
        await pilot.pause()
        assert isinstance(pilot.app.screen, AboutScreen)
        await pilot.press('escape')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, AboutScreen)


@pytest.mark.asyncio
async def test_about_screen_dismiss_q():
    """Test AboutScreen dismisses with q key."""
    async with AboutScreenApp().run_test() as pilot:
        pilot.app.push_screen(AboutScreen())
        await pilot.pause()
        assert isinstance(pilot.app.screen, AboutScreen)
        await pilot.press('q')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, AboutScreen)


# MainScreen compose and on_mount tests
class MainScreenTestApp(App):
    def __init__(self):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        self.port = 8888
        self.message_count = []

    def on_mount(self) -> None:
        screen = MainScreen()
        async def mock_detect():
            return '1.4.0', True
        screen._detect_mmng_version = mock_detect
        def mock_stream(*args, **kwargs):
            pass
        screen.stream_subprocess = mock_stream
        self.push_screen(screen)


@pytest.mark.asyncio
async def test_main_screen_compose():
    """Test MainScreen composes all expected widgets."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        header = pilot.app.screen.query_one(Header)
        footer = pilot.app.screen.query_one(Footer)
        messages_table = pilot.app.screen.query_one('#messages')
        log_widget = pilot.app.screen.query_one('#log')
        status_widget = pilot.app.screen.query_one('#status')
        sparkline = pilot.app.screen.query_one('#spark')
        assert header is not None
        assert footer is not None
        assert messages_table is not None
        assert log_widget is not None
        assert status_widget is not None
        assert sparkline is not None


@pytest.mark.asyncio
async def test_main_screen_on_mount_sets_columns():
    """Test MainScreen.on_mount sets up DataTable columns correctly."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages')
        assert 'time' in table.columns
        assert 'address' in table.columns
        assert 'message' in table.columns
        assert str(table.columns['time'].label) == 'Time'
        assert str(table.columns['address'].label) == 'Address'
        assert str(table.columns['message'].label) == 'Message'


# MainScreen on_output_message tests
@pytest.mark.asyncio
async def test_main_screen_on_output_message_adds_row():
    """Test MainScreen.on_output_message adds row to DataTable for valid message."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        test_line = (
            '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   test message'
        )
        screen = pilot.app.screen
        screen.post_message(OutputMessage(test_line))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages')
        assert len(list(table.rows)) == 1
        row_key = list(table.rows.keys())[0]
        cells = table.get_row(row_key)
        assert cells[2] == 'test message'


@pytest.mark.asyncio
async def test_main_screen_on_output_message_no_message():
    """Test MainScreen.on_output_message logs warning for invalid message."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        screen.post_message(OutputMessage('garbage input'))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages')
        assert len(list(table.rows)) == 0


# Pocsag action and key binding tests
class ActionTestApp(App):
    """A minimal App with Pocsag bindings/actions and a MainScreen."""
    CSS_PATH = None
    BINDINGS = [
        ('c', 'clear_screen', 'Clear'),
        ('question_mark', "app.push_screen('help')", 'Help'),
        ('a', 'about', 'About'),
        ('q', 'quit', 'Quit'),
    ]
    SCREENS = {'help': HelpScreen, 'about': AboutScreen}

    def __init__(self):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        self.port = 8888
        self.message_count = []

    def action_clear_screen(self):
        self.screen.query_one('#messages').clear()
        self.screen.query_one('#log').clear()

    def action_about(self):
        self.push_screen('about')

    def on_mount(self) -> None:
        screen = MainScreen()
        async def mock_detect():
            return '1.4.0', True
        screen._detect_mmng_version = mock_detect
        def mock_stream(*args, **kwargs):
            pass
        screen.stream_subprocess = mock_stream
        self.push_screen(screen)


@pytest.mark.asyncio
async def test_action_clear_screen():
    """Test action_clear_screen clears DataTable and RichLog."""
    async with ActionTestApp().run_test() as pilot:
        await pilot.pause()

        table = pilot.app.screen.query_one('#messages')
        table.add_row('12:00:00', '123456', 'test message')
        await pilot.pause()

        assert len(list(table.rows)) == 1

        await pilot.press('c')
        await pilot.pause()

        assert len(list(table.rows)) == 0

        log = pilot.app.screen.query_one('#log')
        assert len(log.lines) == 0


@pytest.mark.asyncio
async def test_key_binding_help():
    """Test ? key binding opens HelpScreen."""
    async with ActionTestApp().run_test() as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, HelpScreen)
        await pilot.press('?')
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_key_binding_about():
    """Test a key binding opens AboutScreen."""
    async with ActionTestApp().run_test() as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, AboutScreen)
        await pilot.press('a')
        await pilot.pause()
        assert isinstance(pilot.app.screen, AboutScreen)


@pytest.mark.asyncio
async def test_key_binding_quit():
    """Test q key binding quits the app."""
    async with ActionTestApp().run_test() as pilot:
        await pilot.pause()
        await pilot.press('q')
        await pilot.pause()
        assert not pilot.app.is_running


# Tests for MsgsPerSecond.update_graph
class MsgsPerSecondApp(App):
    def compose(self) -> ComposeResult:
        yield MsgsPerSecond()


@pytest.mark.asyncio
async def test_msgspersecond_update_graph_appends_count():
    """Test MsgsPerSecond.update_graph appends count and resets message_count."""
    async with MsgsPerSecondApp().run_test() as pilot:
        mps = pilot.app.screen.query_one(MsgsPerSecond)
        pilot.app.message_count = [10, 20, 30]
        mps.update_graph()
        assert mps.data[-1] == 3
        assert pilot.app.message_count == []


@pytest.mark.asyncio
async def test_msgspersecond_update_graph_keeps_last_60():
    """Test MsgsPerSecond.update_graph keeps only last 60 elements."""
    async with MsgsPerSecondApp().run_test() as pilot:
        mps = pilot.app.screen.query_one(MsgsPerSecond)
        pilot.app.message_count = list(range(70))
        mps.update_graph()
        assert len(mps.data) <= 60
        assert mps.data[-1] == 70


# Tests for MainScreen.read_process_output
class MockStreamReader:
    def __init__(self, lines: list[bytes]):
        self._lines = lines
        self._idx = 0

    async def readline(self):
        if self._idx < len(self._lines):
            line = self._lines[self._idx]
            self._idx += 1
            return line
        return b''


@pytest.mark.asyncio
async def test_read_process_output_yields_decoded_lines():
    """Test MainScreen.read_process_output yields decoded lines."""
    async with MainScreenTestApp().run_test() as pilot:
        screen = pilot.app.screen
        mock_stream = MockStreamReader([b'hello world\n', b''])
        results = []
        async for line in screen.read_process_output(mock_stream):
            results.append(line)
        assert results == ['hello world']


@pytest.mark.asyncio
async def test_read_process_output_breaks_on_empty():
    """Test MainScreen.read_process_output breaks on empty line."""
    async with MainScreenTestApp().run_test() as pilot:
        screen = pilot.app.screen
        mock_stream = MockStreamReader([b''])
        results = []
        async for line in screen.read_process_output(mock_stream):
            results.append(line)
        assert results == []


@pytest.mark.asyncio
async def test_read_process_output_sets_status_receiver():
    """Test MainScreen.read_process_output sets status receiver."""
    async with MainScreenTestApp().run_test() as pilot:
        screen = pilot.app.screen
        status = screen.query_one('#status')
        mock_stream = MockStreamReader([b'test line\n', b''])
        async for _ in screen.read_process_output(mock_stream):
            pass
        assert status.receiver == '[blink bold bright_green]receiving[/]'


# Tests for MainScreen.recalc_width
@pytest.mark.asyncio
async def test_recalc_width_sets_message_column_width():
    """Test MainScreen.recalc_width sets message column width correctly."""
    async with MainScreenTestApp().run_test() as pilot:
        screen = pilot.app.screen
        table = screen.query_one('#messages')
        table.add_row('12:00:00', '123456', 'test message')
        screen.recalc_width(table)
        assert table.columns['message'].auto_width is False
        assert isinstance(table.columns['message'].width, int)
        assert table.columns['message'].width > 0


# Tests for _serve_mode
def test_serve_mode_starts_server(monkeypatch):
    """Test _serve_mode starts server with correct parameters."""
    server_args = {}

    class MockServer:
        def __init__(self, command, host, port, public_url):
            server_args.update(command=command, host=host, port=port, public_url=public_url)
        def serve(self):
            server_args['served'] = True

    mock_module = type(sys)('textual_serve')
    mock_module.server = type(sys)('server')
    mock_module.server.Server = MockServer
    monkeypatch.setitem(sys.modules, 'textual_serve', mock_module)
    monkeypatch.setitem(sys.modules, 'textual_serve.server', mock_module.server)
    monkeypatch.setattr('socket.getfqdn', lambda: 'myhost')

    _serve_mode('0.0.0.0', 8000)
    assert server_args['command'] == 'mmng-ui'
    assert server_args['host'] == '0.0.0.0'
    assert server_args['port'] == 8000
    assert server_args['public_url'] == 'http://myhost:8000'
    assert server_args['served'] is True

    # Test with localhost
    server_args.clear()
    _serve_mode('localhost', 8000)
    assert server_args['public_url'] == 'http://localhost:8000'


def test_serve_mode_missing_dependency_exits(monkeypatch):
    """Test _serve_mode exits when textual-serve is missing."""
    def mock_import(name, *args, **kwargs):
        if name == 'textual_serve':
            raise ImportError("No module named 'textual_serve'")
        return importlib.__import__(name, *args, **kwargs)

    echo_messages = []
    def mock_echo(message, err=False):
        echo_messages.append(message)

    exit_code = []
    def mock_exit(code):
        exit_code.append(code)

    monkeypatch.setattr('builtins.__import__', mock_import)
    monkeypatch.setattr('click.echo', mock_echo)
    monkeypatch.setattr('sys.exit', mock_exit)

    _serve_mode(None, 8000)

    assert len(echo_messages) == 1
    assert 'textual-serve is not installed' in echo_messages[0]
    assert exit_code == [1]
