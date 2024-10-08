import moment
import pytest

from mmng_ui.reader import ParseLine, PocsagMessage


@pytest.fixture
def sample_data():
    return '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   @@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM<NUL>'

@pytest.fixture
def sample_json_data():
    return '{"demod_name":"POCSAG1200","address":1920312,"function":3,"alpha":"Time Critical Incident - Clear ASAP - or advise Comms of Time to Clear (Via Radio)"}'

def test_POCSAG_parse_line(sample_data):
    parse_line = ParseLine()
    result, json_detected = parse_line.parse(sample_data)
    assert result.address == '1622020'
    assert result.timestamp == moment.date(2024, 9, 23, 12, 38, 00)
    assert result.trim_message == '@@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM'
    assert json_detected is False

def test_parse_line_json(sample_json_data):
    parse_line = ParseLine()
    result, json_detected = parse_line.parse(sample_json_data)
    assert result.address == '1920312'
    assert result.trim_message == 'Time Critical Incident - Clear ASAP - or advise Comms of Time to Clear (Via Radio)'
    assert json_detected is True

def test_parse_line_invalid_not_json():
    parse_line = ParseLine(json_detected=True)
    result, json_detected = parse_line.parse('Jibberish that is not JSON')
    assert result.address == ''
    assert result.trim_message == 'ERROR: multimon-ng returned non-JSON: Jibberish that is not JSON'
    assert json_detected is True


@pytest.mark.skip(reason='Untestable for now')
def test_POCSAG_handling_numeric_message():
    line = 'Numeric Message 1234'
    parse_line = ParseLine()
    timestamp, address, message, trim_message, json_detected = parse_line.parse(line)
    assert timestamp is None
    assert address == ''
    assert message == '1234'
    assert trim_message == '1234'

@pytest.mark.skip(reason='Untestable for now')
def test_FLEX_handling_fragmented_message():
    line1 = 'FLEX [123] Fragmented Message 01/2022 F/ ALN ...[ |]'
    line2 = 'FLEX [123] Continued Message 02/2022 C/'
    parse_line = ParseLine()
    fragment_address = None
    for line in [line1, line2]:
        timestamp, address, message, trim_message = parse_line.parse(line)
        if not fragment_address:
            fragment_address = address
            assert address == '123'
            assert message is None  # First message should be empty
            continue

        assert timestamp is None
        assert address == ''
        assert message == frag[fragment_address]
        del frag[fragment_address]

@pytest.mark.skip(reason='Untestable for now')
def test_FLEX_handling_complete_message():
    line = 'FLEX [123] Complete Message 2022-09-01 12:34:56'
    parse_line = ParseLine()
    timestamp, address, message, trim_message = parse_line.parse(line)
    assert timestamp == Moment.date('2022-09-01 12:34:56', 'YYYY-MM-DD HH:mm:ss')
    assert address == ''
    assert message == ''
    assert trim_message is None

def test_default_case():
    line = 'Invalid Message'
    parse_line = ParseLine()
    result = PocsagMessage()
    result, json_detected = parse_line.parse(line)
    # assert timestamp is None
    assert result.address == ''
    assert result.trim_message == ''