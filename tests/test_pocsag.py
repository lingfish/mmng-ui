# ruff: noqa: N802
import pytest
from textual.app import App, ComposeResult
from textual.message import Message

from mmng_ui.pocsag import (
    OutputMessage,
    Status,
    Executable,
    StatusWidget,
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