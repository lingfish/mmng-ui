import moment
import pytest

from mmng_ui.reader import parse_line


@pytest.fixture
def sample_data():
    return '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   @@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM<NUL>'

def test_parse_line(sample_data):
    current_time, timestamp, address, trim_message = parse_line(sample_data)
    assert address == '1622020'
    assert timestamp == moment.date(2024, 9, 23, 12, 38, 00)
    assert trim_message == '@@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM'