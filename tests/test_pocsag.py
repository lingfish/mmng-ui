import importlib
import sys

import pytest
from rich.text import Text
from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import (
    DataTable,
    Digits,
    Footer,
    Header,
    Input,
    Markdown,
    RadioButton,
    RadioSet,
    TabbedContent,
    TabPane,
)

from mmng_ui.capcode_db import CapcodeDB
from mmng_ui.pocsag import (
    AboutScreen,
    Executable,
    FeedTabbedContent,
    FeedWidget,
    HelpScreen,
    MainScreen,
    MsgsPerSecond,
    OutputMessage,
    PortConfig,
    RenameTabScreen,
    SaveScreen,
    Status,
    StatusWidget,
    _extract_table_rows,
    _format_as_csv,
    _format_as_json,
    _format_as_markdown,
    _serve_mode,
    parse_ports,
)


class StatusApp(App):
    def compose(self) -> ComposeResult:
        yield StatusWidget(id='test-status')


def test_output_message():
    """Test OutputMessage dataclass."""
    msg = OutputMessage('test output')
    assert isinstance(msg, Message)
    assert msg.output == 'test output'


def test_status_dataclass():
    """Test Status dataclass."""
    status = Status(receiver='test_receiver', ip_address='192.168.1.1', json_mode=True, charset='US')
    assert status.receiver == 'test_receiver'
    assert status.ip_address == '192.168.1.1'
    assert status.json_mode is True
    assert status.charset == 'US'

    # Test __repr__
    repr_str = repr(status)
    assert 'Receiver: test_receiver' in repr_str
    assert 'IP address: 192.168.1.1' in repr_str


def test_executable_dataclass():
    """Test Executable dataclass."""
    # Test with resolved_path
    exec_with_path = Executable(command='test_cmd', resolved_path='/usr/bin/test_cmd', version='1.0.0')
    assert exec_with_path.command == 'test_cmd'
    assert exec_with_path.resolved_path == '/usr/bin/test_cmd'
    assert exec_with_path.version == '1.0.0'

    # Test with None resolved_path
    exec_none_path = Executable(command='test_cmd', resolved_path=None, version=None)
    assert exec_none_path.command == 'test_cmd'
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
    def __init__(self, ports=None, port_configs=None, capcode_db=None):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        if port_configs is not None:
            self.port_configs = port_configs
        else:
            self.port_configs = [PortConfig(p) for p in (ports or [8888])]
        self.message_count = []
        self.json_capable = True
        self.mmng.version = '1.4.0'
        self._streaming_disabled = True
        self.capcode_db = capcode_db

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


@pytest.mark.asyncio
async def test_main_screen_compose():
    """Test MainScreen composes Header, Footer, and TabbedContent with FeedWidgets."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        header = pilot.app.screen.query_one(Header)
        footer = pilot.app.screen.query_one(Footer)
        tab_content = pilot.app.screen.query_one(TabbedContent)
        assert header is not None
        assert footer is not None
        assert tab_content is not None

        messages_table = pilot.app.screen.query_one('#messages-8888')
        log_widget = pilot.app.screen.query_one('#log-8888')
        status_widget = pilot.app.screen.query_one('#status-8888')
        sparkline = pilot.app.screen.query_one('#spark-8888')
        mps = pilot.app.screen.query_one('#msgs-per-second-8888')
        assert messages_table is not None
        assert log_widget is not None
        assert status_widget is not None
        assert sparkline is not None
        assert mps is not None


@pytest.mark.asyncio
async def test_main_screen_on_mount_sets_columns():
    """Test MainScreen.on_mount sets up DataTable columns correctly."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert 'time' in table.columns
        assert 'address' in table.columns
        assert 'message' in table.columns
        assert str(table.columns['time'].label) == 'Time'
        assert str(table.columns['address'].label) == 'Address'
        assert str(table.columns['message'].label) == 'Message'


# MainScreen on_output_message tests
@pytest.mark.asyncio
async def test_main_screen_on_output_message_adds_row():
    """Test FeedWidget adds row to DataTable for valid message."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        test_line = '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   test message'
        feed = pilot.app.screen.query_one(FeedWidget)
        feed.post_message(OutputMessage(test_line))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert len(list(table.rows)) == 1
        row_key = list(table.rows.keys())[0]
        cells = table.get_row(row_key)
        assert cells[2] == Text('test message', overflow='fold')


@pytest.mark.asyncio
async def test_main_screen_on_output_message_no_message():
    """Test FeedWidget logs warning for invalid message."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        feed.post_message(OutputMessage('garbage input'))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert len(list(table.rows)) == 0


@pytest.mark.asyncio
async def test_on_output_message_shows_capcode_alias(tmp_path):
    """Test FeedWidget shows alias for known capcode address."""
    json_file = tmp_path / 'test_capcodes.json'
    json_file.write_text(
        '{"data": [{"address": "1622020", "alias": "Test Alias", "agency": "TA", "color": "purple", "icon": "fire"}]}'
    )
    capcode_db = CapcodeDB.load(json_file)
    async with MainScreenTestApp(capcode_db=capcode_db).run_test() as pilot:
        await pilot.pause()
        test_line = '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   test message'
        feed = pilot.app.screen.query_one(FeedWidget)
        feed.post_message(OutputMessage(test_line))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert len(list(table.rows)) == 1
        row_key = list(table.rows.keys())[0]
        cells = table.get_row(row_key)
        assert 'Test Alias' in str(cells[1])
        assert '1622020' in str(cells[1])
        assert '🔥' in str(cells[1])


@pytest.mark.asyncio
async def test_on_output_message_unknown_capcode_shows_raw(tmp_path):
    """Test FeedWidget shows raw address for unknown capcode."""
    json_file = tmp_path / 'test_capcodes.json'
    json_file.write_text('{"data": [{"address": "9999999", "alias": "Other", "agency": "XX"}]}')
    capcode_db = CapcodeDB.load(json_file)
    async with MainScreenTestApp(capcode_db=capcode_db).run_test() as pilot:
        await pilot.pause()
        test_line = '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   test message'
        feed = pilot.app.screen.query_one(FeedWidget)
        feed.post_message(OutputMessage(test_line))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert len(list(table.rows)) == 1
        row_key = list(table.rows.keys())[0]
        cells = table.get_row(row_key)
        assert '1622020' in str(cells[1])
        assert 'Other' not in str(cells[1])


# Pocsag action and key binding tests
class ActionTestApp(App):
    """A minimal App with Pocsag bindings/actions and a MainScreen."""

    CSS_PATH = None
    BINDINGS = [
        ('c', 'clear_screen', 'Clear'),
        ('question_mark', "app.push_screen('help')", 'Help'),
        ('a', 'about', 'About'),
        ('q', 'quit', 'Quit'),
        ('r', 'rename_tab', 'Rename tab'),
    ]
    SCREENS = {'help': HelpScreen, 'about': AboutScreen}

    def __init__(self, ports=None, port_configs=None):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        if port_configs is not None:
            self.port_configs = port_configs
        else:
            self.port_configs = [PortConfig(p) for p in (ports or [8888])]
        self.message_count = []
        self.json_capable = True
        self.mmng.version = '1.4.0'
        self._streaming_disabled = True
        self.capcode_db = None

    def action_clear_screen(self):
        tabs = self.screen.query_one(FeedTabbedContent)
        if (pane := tabs.active_pane) is not None:
            pane.query_one(FeedWidget).clear()

    def action_about(self):
        self.push_screen('about')

    def action_rename_tab(self):
        tabs = self.screen.query_one(FeedTabbedContent)
        if (pane := tabs.active_pane) is not None:
            self._rename_pane = pane
            title = str(pane._title) if pane._title else ''
            self.push_screen(RenameTabScreen(current_title=title))

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


@pytest.mark.asyncio
async def test_action_clear_screen():
    """Test action_clear_screen clears DataTable and RichLog."""
    async with ActionTestApp().run_test() as pilot:
        await pilot.pause()

        table = pilot.app.screen.query_one('#messages-8888')
        table.add_row('12:00:00', '123456', 'test message')
        await pilot.pause()

        assert len(list(table.rows)) == 1

        await pilot.press('c')
        await pilot.pause()

        assert len(list(table.rows)) == 0

        log = pilot.app.screen.query_one('#log-8888')
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
    def __init__(self):
        super().__init__()
        self.message_count = []

    def compose(self) -> ComposeResult:
        yield MsgsPerSecond(message_count_ref=self.message_count)


@pytest.mark.asyncio
async def test_msgspersecond_update_graph_appends_count():
    """Test MsgsPerSecond.update_graph appends count and resets message_count."""
    async with MsgsPerSecondApp().run_test() as pilot:
        mps = pilot.app.screen.query_one(MsgsPerSecond)
        pilot.app.message_count.extend([10, 20, 30])
        mps.update_graph()
        assert mps.data[-1] == 3
        assert pilot.app.message_count == []


@pytest.mark.asyncio
async def test_msgspersecond_update_graph_keeps_last_60():
    """Test MsgsPerSecond.update_graph keeps only last 60 elements."""
    async with MsgsPerSecondApp().run_test() as pilot:
        mps = pilot.app.screen.query_one(MsgsPerSecond)
        pilot.app.message_count.extend(range(70))
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
    """Test FeedWidget.read_process_output yields decoded lines."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        mock_stream = MockStreamReader([b'hello world\n', b''])
        results = []
        async for line in feed.read_process_output(mock_stream):
            results.append(line)
        assert results == ['hello world']


@pytest.mark.asyncio
async def test_read_process_output_breaks_on_empty():
    """Test FeedWidget.read_process_output breaks on empty line."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        mock_stream = MockStreamReader([b''])
        results = []
        async for line in feed.read_process_output(mock_stream):
            results.append(line)
        assert results == []


@pytest.mark.asyncio
async def test_read_process_output_sets_status_receiver():
    """Test FeedWidget.read_process_output sets status receiver."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        status = feed.query_one('#status-8888')
        mock_stream = MockStreamReader([b'test line\n', b''])
        async for _ in feed.read_process_output(mock_stream):
            pass
        assert status.receiver == '[blink bold bright_green]receiving[/]'


# Tests for MainScreen.on_output_message scroll
@pytest.mark.asyncio
async def test_on_output_message_scrolls_to_bottom():
    """Test FeedWidget scrolls to bottom after adding a row."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        test_line = '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   test message'
        feed = pilot.app.screen.query_one(FeedWidget)
        feed.post_message(OutputMessage(test_line))
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        assert len(list(table.rows)) == 1
        assert table.scroll_y == table.max_scroll_y


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


# --- parse_ports tests ---


def test_parse_ports_single():
    """Test parse_ports with a single port."""
    assert parse_ports('8888') == [PortConfig(8888)]


def test_parse_ports_single_with_equals():
    """Test parse_ports with a single port and equals syntax."""
    assert parse_ports('8888=Cops') == [PortConfig(8888, 'Cops')]


def test_parse_ports_single_with_colon():
    """Test parse_ports with a single port and colon syntax."""
    assert parse_ports('8888:FireDept') == [PortConfig(8888, 'FireDept')]


def test_parse_ports_multiple():
    """Test parse_ports with multiple ports."""
    assert parse_ports('8888,8889,8890') == [
        PortConfig(8888),
        PortConfig(8889),
        PortConfig(8890),
    ]


def test_parse_ports_multiple_mixed():
    """Test parse_ports with multiple ports using mixed syntax."""
    assert parse_ports('8888=Cops,8889:Fire') == [
        PortConfig(8888, 'Cops'),
        PortConfig(8889, 'Fire'),
    ]


def test_parse_ports_with_spaces():
    """Test parse_ports handles spaces."""
    assert parse_ports('8888, 8889') == [PortConfig(8888), PortConfig(8889)]


def test_parse_ports_empty_name_equals():
    """Test parse_ports with empty name after equals raises ValueError."""
    with pytest.raises(ValueError):
        parse_ports('8888=')


def test_parse_ports_empty_name_colon():
    """Test parse_ports with empty name after colon raises ValueError."""
    with pytest.raises(ValueError):
        parse_ports('8888:')


def test_parse_ports_whitespace_only_name():
    """Test parse_ports with whitespace-only name raises ValueError."""
    with pytest.raises(ValueError):
        parse_ports('8888=   ')


def test_parse_ports_invalid():
    """Test parse_ports raises ValueError for invalid input."""
    with pytest.raises(ValueError):
        parse_ports('abc')


def test_parse_ports_empty():
    """Test parse_ports raises ValueError for empty string."""
    with pytest.raises(ValueError):
        parse_ports('')


# --- FeedWidget compose tests ---


class FeedWidgetTestApp(App):
    def __init__(self):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        self.port_configs = [PortConfig(8888)]
        self.message_count = []
        self.json_capable = True
        self.mmng.version = '1.4.0'
        self._streaming_disabled = True


@pytest.mark.asyncio
async def test_feed_widget_compose():
    """Test FeedWidget composes all expected widgets with port-specific IDs."""
    async with FeedWidgetTestApp().run_test() as pilot:
        screen = pilot.app.screen
        feed = FeedWidget(port=8888)
        screen.mount(feed)
        await pilot.pause()

        messages_table = feed.query_one('#messages-8888')
        log_widget = feed.query_one('#log-8888')
        status_widget = feed.query_one('#status-8888')
        sparkline = feed.query_one('#spark-8888')
        mps = feed.query_one('#msgs-per-second-8888')

        assert messages_table is not None
        assert log_widget is not None
        assert status_widget is not None
        assert sparkline is not None
        assert mps is not None

        assert str(messages_table.columns['time'].label) == 'Time'
        assert str(messages_table.columns['address'].label) == 'Address'
        assert str(messages_table.columns['message'].label) == 'Message'


@pytest.mark.asyncio
async def test_feed_widget_clear():
    """Test FeedWidget.clear clears table and log."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        table = feed.query_one('#messages-8888')
        table.add_row('12:00:00', '123456', 'test message')
        log = feed.query_one('#log-8888')
        log.write('test log entry')
        await pilot.pause()

        assert len(list(table.rows)) == 1
        assert len(log.lines) == 1

        feed.clear()
        await pilot.pause()

        assert len(list(table.rows)) == 0
        assert len(log.lines) == 0


@pytest.mark.asyncio
async def test_data_table_no_blank_rows():
    """DataTable should auto-size to row count (no inline height: 100%)."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        # No inline height override — table uses default height: auto
        assert table.styles.height is None or table.styles.height.value == 1.0
        # With zero rows, no blank filler
        assert len(list(table.rows)) == 0
        # Add one row
        table.add_row('12:00:00', '123456', 'test')
        await pilot.pause()
        # Only real rows present
        assert len(list(table.rows)) == 1


@pytest.mark.asyncio
async def test_messages_container_fills_grid():
    """.feed-messages is the DataTable itself (no wrapper)."""
    async with MainScreenTestApp().run_test() as pilot:
        await pilot.pause()
        feed = pilot.app.screen.query_one(FeedWidget)
        elem = feed.query_one('.feed-messages')
        assert isinstance(elem, DataTable)
        assert elem.id == 'messages-8888'


# --- Multi-port tab tests ---


class MultiPortTestApp(App):
    BINDINGS = [
        ('c', 'clear_screen', 'Clear'),
    ]

    def __init__(self, ports=None):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        self.port_configs = [PortConfig(p) for p in (ports or [8888, 8889])]
        self.message_count = []
        self.json_capable = True
        self.mmng.version = '1.4.0'
        self._streaming_disabled = True
        self.capcode_db = None

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def action_clear_screen(self):
        tabs = self.screen.query_one(FeedTabbedContent)
        if (pane := tabs.active_pane) is not None:
            pane.query_one(FeedWidget).clear()


@pytest.mark.asyncio
async def test_main_screen_multi_port_two_tabs():
    """Test MainScreen with 2 ports creates 2 tab panes."""
    async with MultiPortTestApp(ports=[8888, 8889]).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(TabbedContent)
        panes = list(tabs.query(TabPane))
        assert len(panes) == 2
        assert panes[0].id == 'tab-8888'
        assert panes[1].id == 'tab-8889'

        feed1 = panes[0].query_one(FeedWidget)
        feed2 = panes[1].query_one(FeedWidget)
        assert feed1.port == 8888
        assert feed2.port == 8889

        assert panes[0].query_one('#messages-8888') is not None
        assert panes[1].query_one('#messages-8889') is not None


@pytest.mark.asyncio
async def test_main_screen_single_port_one_tab():
    """Test MainScreen with 1 port creates 1 tab pane."""
    async with MultiPortTestApp(ports=[8888]).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(TabbedContent)
        panes = list(tabs.query(TabPane))
        assert len(panes) == 1
        assert panes[0].id == 'tab-8888'


@pytest.mark.asyncio
async def test_clear_only_active_tab():
    """Test action_clear_screen only clears the active tab's feed."""
    async with MultiPortTestApp(ports=[8888, 8889]).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(FeedTabbedContent)
        panes = list(tabs.query(TabPane))
        feed1 = panes[0].query_one(FeedWidget)
        feed2 = panes[1].query_one(FeedWidget)
        t1 = panes[0].query_one('#messages-8888')
        t2 = panes[1].query_one('#messages-8889')

        t1.add_row('12:00:00', '123456', 'tab1 msg')
        t2.add_row('12:00:01', '789012', 'tab2 msg')
        await pilot.pause()

        assert len(list(t1.rows)) == 1
        assert len(list(t2.rows)) == 1

        # Switch to second tab by clicking it
        await pilot.click('#--content-tab-tab-8889')
        await pilot.pause()

        await pilot.press('c')
        await pilot.pause()

        assert len(list(t2.rows)) == 0, 'active tab should be cleared'
        assert len(list(t1.rows)) == 1, 'inactive tab should not be cleared'


# --- Tab naming tests ---


@pytest.mark.asyncio
async def test_main_screen_tab_title_with_named_port():
    """Test MainScreen shows custom name for named port."""
    async with MainScreenTestApp(
        port_configs=[PortConfig(8888, 'Cops')],
    ).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(TabbedContent)
        panes = list(tabs.query(TabPane))
        assert len(panes) == 1
        assert 'Cops' in str(panes[0]._title)


@pytest.mark.asyncio
async def test_main_screen_tab_title_with_unnamed_port():
    """Test MainScreen shows default 'Port X' for unnamed port."""
    async with MainScreenTestApp(
        port_configs=[PortConfig(8888)],
    ).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(TabbedContent)
        panes = list(tabs.query(TabPane))
        assert len(panes) == 1
        assert 'Port 8888' in str(panes[0]._title)


@pytest.mark.asyncio
async def test_main_screen_mixed_named_unnamed_ports():
    """Test MainScreen with mix of named and unnamed ports."""
    async with MainScreenTestApp(
        port_configs=[
            PortConfig(8888, 'Cops'),
            PortConfig(8889),
            PortConfig(8890, 'Fire'),
        ],
    ).run_test() as pilot:
        await pilot.pause()
        tabs = pilot.app.screen.query_one(TabbedContent)
        panes = list(tabs.query(TabPane))
        assert len(panes) == 3
        assert 'Cops' in str(panes[0]._title)
        assert 'Port 8889' in str(panes[1]._title)
        assert 'Fire' in str(panes[2]._title)


# --- Runtime rename tests ---


@pytest.mark.asyncio
async def test_rename_tab_keybinding_opens_modal():
    """Test that pressing 'r' opens the rename tab modal."""
    async with ActionTestApp(port_configs=[PortConfig(8888, 'OldName')]).run_test() as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, RenameTabScreen)

        await pilot.press('r')
        await pilot.pause()

        assert isinstance(pilot.app.screen, RenameTabScreen)


@pytest.mark.asyncio
async def test_rename_tab_enter_confirms_change():
    """Test that entering a name and pressing Enter renames the tab."""
    async with ActionTestApp(port_configs=[PortConfig(8888, 'OldName')]).run_test() as pilot:
        await pilot.pause()

        await pilot.press('r')
        await pilot.pause()
        assert isinstance(pilot.app.screen, RenameTabScreen)

        # Type new name
        await pilot.press(*'NewName')
        await pilot.pause()

        await pilot.press('enter')
        await pilot.pause()

        assert not isinstance(pilot.app.screen, RenameTabScreen)

        tabs = pilot.app.screen.query_one(TabbedContent)
        tab = tabs.get_tab('tab-8888')
        assert 'NewName' in str(tab.label)


@pytest.mark.asyncio
async def test_rename_tab_escape_cancels():
    """Test that pressing Escape cancels the rename without changing the tab."""
    async with ActionTestApp(port_configs=[PortConfig(8888, 'OriginalName')]).run_test() as pilot:
        await pilot.pause()

        await pilot.press('r')
        await pilot.pause()
        assert isinstance(pilot.app.screen, RenameTabScreen)

        await pilot.press(*'Changed')
        await pilot.pause()

        await pilot.press('escape')
        await pilot.pause()

        assert not isinstance(pilot.app.screen, RenameTabScreen)

        tabs = pilot.app.screen.query_one(TabbedContent)
        tab = tabs.get_tab('tab-8888')
        assert 'OriginalName' in str(tab.label)


# --- SaveScreen and format tests ---

SAMPLE_ROWS = [
    {'time': '14:30:25', 'address': '1622020', 'message': 'Test message 1'},
    {'time': '14:30:26', 'address': '1234567', 'message': 'Another message with, comma'},
]

EXPECTED_CSV = (
    'Time,Address,Message\r\n'
    '14:30:25,1622020,Test message 1\r\n'
    '14:30:26,1234567,"Another message with, comma"\r\n'
)

EXPECTED_CSV_NO_CR = (
    'Time,Address,Message\n'
    '14:30:25,1622020,Test message 1\n'
    '14:30:26,1234567,"Another message with, comma"\n'
)

EXPECTED_MD = (
    '| Time | Address | Message |\n'
    '| --- | --- | --- |\n'
    '| 14:30:25 | 1622020 | Test message 1 |\n'
    '| 14:30:26 | 1234567 | Another message with, comma |\n'
)

EXPECTED_JSON = (
    '[\n'
    '  {\n'
    '    "Time": "14:30:25",\n'
    '    "Address": "1622020",\n'
    '    "Message": "Test message 1"\n'
    '  },\n'
    '  {\n'
    '    "Time": "14:30:26",\n'
    '    "Address": "1234567",\n'
    '    "Message": "Another message with, comma"\n'
    '  }\n'
    ']'
)

EXPECTED_JSON_EMPTY = '[]'

EXPECTED_CSV_HEADER_ONLY = 'Time,Address,Message\r\n'


def test_format_as_csv():
    """Test CSV formatting with multiple rows."""
    result = _format_as_csv(SAMPLE_ROWS)
    assert result == EXPECTED_CSV or result == EXPECTED_CSV_NO_CR


def test_format_as_csv_empty():
    """Test CSV formatting with empty rows."""
    result = _format_as_csv([])
    assert result == EXPECTED_CSV_HEADER_ONLY or result == 'Time,Address,Message\n'


def test_format_as_markdown():
    """Test Markdown table formatting."""
    result = _format_as_markdown(SAMPLE_ROWS)
    assert result == EXPECTED_MD


def test_format_as_markdown_empty():
    """Test Markdown formatting with empty rows returns header + separator."""
    result = _format_as_markdown([])
    assert result == EXPECTED_MD.splitlines()[0] + '\n' + EXPECTED_MD.splitlines()[1] + '\n'


def test_format_as_json():
    """Test JSON formatting with multiple rows."""
    result = _format_as_json(SAMPLE_ROWS)
    assert result == EXPECTED_JSON


def test_format_as_json_empty():
    """Test JSON formatting with empty rows."""
    result = _format_as_json([])
    assert result == EXPECTED_JSON_EMPTY


def test_format_as_json_single_row():
    """Test JSON formatting with a single row."""
    single_row = [{'time': '12:00:00', 'address': '9999999', 'message': 'Single'}]
    result = _format_as_json(single_row)
    assert '"12:00:00"' in result
    assert '"9999999"' in result
    assert '"Single"' in result


# DataTable extraction tests
class ExtractionTestApp(App):
    def compose(self) -> ComposeResult:
        table = DataTable(id='test-table')
        table.add_column('Time', key='time')
        table.add_column('Address', key='address')
        table.add_column('Message', key='message')
        table.add_row('14:30:25', '1622020', Text('Test message 1', overflow='fold'))
        table.add_row(
            '14:30:26',
            Text('Alias (1234567)', justify='right'),
            'Another message',
        )
        yield table


@pytest.mark.asyncio
async def test_extract_table_rows():
    """Test extracting rows from a DataTable."""
    async with ExtractionTestApp().run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one('#test-table')
        rows = _extract_table_rows(table)
        assert len(rows) == 2
        assert rows[0]['time'] == '14:30:25'
        assert rows[0]['address'] == '1622020'
        assert rows[0]['message'] == 'Test message 1'
        assert rows[1]['time'] == '14:30:26'
        assert rows[1]['address'] == 'Alias (1234567)'
        assert rows[1]['message'] == 'Another message'


@pytest.mark.asyncio
async def test_extract_table_rows_empty():
    """Test extracting rows from an empty DataTable."""
    async with ExtractionTestApp().run_test() as pilot:
        await pilot.pause()
        empty_table = DataTable(id='empty-table')
        empty_table.add_column('Time', key='time')
        empty_table.add_column('Address', key='address')
        empty_table.add_column('Message', key='message')
        pilot.app.screen.mount(empty_table)
        await pilot.pause()
        rows = _extract_table_rows(empty_table)
        assert rows == []


class SaveScreenTestApp(App):
    """Minimal app for testing SaveScreen."""

    def __init__(self):
        super().__init__()
        self.delivered = None
        self.delivered_filename = None

    def deliver_text(self, path_or_file, *, save_filename=None, **_kwargs):
        content = path_or_file.read() if hasattr(path_or_file, 'read') else str(path_or_file)
        self.delivered = content
        self.delivered_filename = save_filename
        return 'test-key'


@pytest.mark.asyncio
async def test_save_screen_compose():
    """Test SaveScreen composes correctly."""
    async with SaveScreenTestApp().run_test() as pilot:
        screen = SaveScreen(rows=SAMPLE_ROWS, port=8888)
        pilot.app.push_screen(screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, SaveScreen)
        assert screen.rows == SAMPLE_ROWS
        assert screen.port == 8888


@pytest.mark.asyncio
async def test_save_screen_escape_cancels():
    """Test Escape dismisses SaveScreen without saving."""
    async with SaveScreenTestApp().run_test() as pilot:
        pilot.app.push_screen(SaveScreen(rows=SAMPLE_ROWS, port=8888))
        await pilot.pause()
        assert isinstance(pilot.app.screen, SaveScreen)
        await pilot.press('escape')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SaveScreen)
        assert pilot.app.delivered is None


@pytest.mark.asyncio
async def test_save_screen_enter_saves_csv():
    """Test Enter submits and calls deliver_text with CSV content."""
    async with SaveScreenTestApp().run_test() as pilot:
        pilot.app.push_screen(SaveScreen(rows=SAMPLE_ROWS, port=8888))
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SaveScreen)
        assert pilot.app.delivered is not None
        assert 'Time,Address,Message' in pilot.app.delivered
        assert '14:30:25' in pilot.app.delivered
        assert pilot.app.delivered_filename is not None
        assert pilot.app.delivered_filename.startswith('mmng_port8888_')


# Integration test with full app pipeline
class SaveActionTestApp(App):
    """Test app with save_as action and binding."""

    CSS_PATH = None
    BINDINGS = [
        ('s', 'save_as', 'Save tab to file'),
    ]

    def __init__(self):
        super().__init__()
        self.mmng = Executable('multimon-ng', '/usr/bin/multimon-ng', '1.4.0')
        self.mmng_binary = 'multimon-ng'
        self.sox_binary = None
        self.sox_rate = None
        self.charset = 'US'
        self.port_configs = [PortConfig(8888)]
        self.message_count = []
        self.json_capable = True
        self.mmng.version = '1.4.0'
        self._streaming_disabled = True
        self.capcode_db = None
        self.delivered = None
        self.delivered_filename = None

    def action_save_as(self):
        tabs = self.screen.query_one(FeedTabbedContent)
        if (pane := tabs.active_pane) is not None:
            table = pane.query_one(DataTable)
            rows = _extract_table_rows(table)
            port = pane.query_one(FeedWidget).port
            self.push_screen(SaveScreen(rows=rows, port=port))

    def deliver_text(self, path_or_file, *, save_filename=None, **_kwargs):
        content = path_or_file.read() if hasattr(path_or_file, 'read') else str(path_or_file)
        self.delivered = content
        self.delivered_filename = save_filename
        return 'test-key'

    def on_mount(self):
        self.push_screen(MainScreen())


@pytest.mark.asyncio
async def test_save_action_opens_save_screen():
    """Test pressing 's' opens the SaveScreen."""
    async with SaveActionTestApp().run_test() as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SaveScreen)
        await pilot.press('s')
        await pilot.pause()
        assert isinstance(pilot.app.screen, SaveScreen)


@pytest.mark.asyncio
async def test_save_action_with_data():
    """Test saving with data in the table delivers formatted CSV."""
    async with SaveActionTestApp().run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one('#messages-8888')
        table.add_row(
            '14:30:25',
            '1622020',
            Text('Test message 1', overflow='fold'),
        )
        await pilot.pause()
        await pilot.press('s')
        await pilot.pause()
        assert isinstance(pilot.app.screen, SaveScreen)
        await pilot.press('enter')
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SaveScreen)
        assert pilot.app.delivered is not None
        assert 'Time,Address,Message' in pilot.app.delivered
        assert '14:30:25' in pilot.app.delivered
        assert '1622020' in pilot.app.delivered
        assert 'Test message 1' in pilot.app.delivered


# --- SaveScreen fix tests: RadioSet default selection, extension update, notification ---


@pytest.mark.asyncio
async def test_save_screen_radio_set_selects_first_on_mount():
    """Test that RadioSet selects first option (CSV) on mount."""
    async with SaveScreenTestApp().run_test() as pilot:
        pilot.app.push_screen(SaveScreen(rows=SAMPLE_ROWS, port=8888))
        await pilot.pause()
        radio_set = pilot.app.screen.query_one('#save-format', RadioSet)
        assert radio_set.pressed_index == 0


@pytest.mark.asyncio
async def test_save_screen_format_change_updates_extension():
    """Test that changing RadioSet updates filename extension."""
    async with SaveScreenTestApp().run_test() as pilot:
        pilot.app.push_screen(SaveScreen(rows=SAMPLE_ROWS, port=8888))
        await pilot.pause()
        filename_input = pilot.app.screen.query_one('#save-filename', Input)
        radio_buttons = pilot.app.screen.query(RadioButton)

        # Default should be .csv
        assert filename_input.value.endswith('.csv')

        # Change to Markdown (index 1)
        await pilot.click(radio_buttons[1])
        await pilot.pause()
        assert filename_input.value.endswith('.md')

        # Change to JSON (index 2)
        await pilot.click(radio_buttons[2])
        await pilot.pause()
        assert filename_input.value.endswith('.json')


@pytest.mark.asyncio
async def test_save_screen_notifies_after_save():
    """Test that _do_save calls app.notify with expected message."""
    notify_messages = []

    class NotifySaveTestApp(SaveScreenTestApp):
        def notify(self, message, title=None, **kwargs):
            notify_messages.append((message, title))

    async with NotifySaveTestApp().run_test() as pilot:
        pilot.app.push_screen(SaveScreen(rows=SAMPLE_ROWS, port=8888))
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        assert len(notify_messages) == 1
        msg, title = notify_messages[0]
        assert title == 'Export'
        assert msg.startswith('Saved as')
        assert 'mmng_port8888_' in msg
