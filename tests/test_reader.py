import warnings
from xml.sax import parse

import moment
import pytest

from mmng_ui.reader import ParseLine, PocsagMessage


FLEX_LINES = """FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [4294947544] UNK 00136080 001794b2 00193e1c 0015db79 0004e703 000136bd 00194da5 001b8f04 001846e3 001e8f83 001d7d3b 000ae060 00026bc2 001ffff3 001421c8
FLEX|2024-12-08 21:18:16|3200/4/F/D|03.096|002064197|ALN|
FLEX|2024-12-08 21:18:16|3200/4/C/D|03.096|4294956915|ALN|A - 16 NORTH 41  [34]
FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [002064209] NUM U75[
FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [4294964846] UNK 00116080 000f8b51 000b60aa 000f86aa 0018a645 001620c1 001c1132 000179e8 0002a489 001e10da 0007e16a 001bb879 0009db37 00000008 001421c3
FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [002064201] NUM 73798 94U
FLEX|2024-12-08 21:18:16|3200/4/C/D|03.096|4294947155|ALN|A - 16 NORTH 41  [39]
FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [002064225] NUM 838[
FLEX: 2024-12-08 21:18:16 3200/4/D 03.096 [4294950812] UNK 000a2080 00182222 00178935 0015f288 0010e2e4 000c4579 00111cb0 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
FLEX|2024-12-08 21:18:35|3200/4/C/A|04.062|4294941051|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [73]C9
FLEX: 2024-12-08 21:18:35 3200/4/A 04.062 [002064200] NUM 0-82
FLEX|2024-12-08 21:18:46|3200/4/C/A|04.063|4294947329|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [18]
FLEX: 2024-12-08 21:18:46 3200/4/A 04.063 [002064196] NUM U159
FLEX: 2024-12-08 21:18:46 3200/4/A 04.063 [4294962628] UNK 00000080 0007b3af 0001f034 00183d0a 001a02fd 001dfcf6 001b64de 00000002 001ca342
FLEX: 2024-12-08 21:18:46 3200/4/A 04.063 [002064198] TON 
FLEX|2024-12-08 21:18:46|3200/4/C/A|04.063|4294944497|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [45]
FLEX: 2024-12-08 21:18:46 3200/4/A 04.063 [002064200] NUM 0-82
FLEX: 2024-12-08 21:18:46 3200/4/B 04.063 [4294964639] UNK 00090080 0005b7fc 001fb6d5 00089a00 00162f2d 00019ed2 0019675d 001fa814 001c614d 001e1603 0013751e 0010e361 00096f78 001d1514 001020f0 0014f05e 0010f246 001f50c9 00116430 0012c654 000811bc 00013496 00181839 0006f87c 000c6a85 00025af3 0007af6b 000f88a8 0000b0b4 00147e3e 00025293 0000024e 00000000
FLEX|2024-12-08 21:18:46|3200/4/C/B|04.063|002064201|ALN|
FLEX|2024-12-08 21:18:46|3200/4/C/C|04.063|4294942723|ALN|nsult LOPEZ PEREZ 31373343 h/o spinal compression fx's MRI 12/7 subacute compression deformities, no evidence of cord compression. Pt neurologically intact. any acute surgical intervention? - Donald Thommes 6314176868 [68]3fL
FLEX|2024-12-08 21:18:46|3200/4/F/C|04.063|002064198|ALN|
FLEX: 2024-12-08 21:19:07 3200/4/A 04.064 [4294951837] UNK 001e0080 001b8c62 0004af2b 0017e3b9 000d7361 000d0cbd 0018afef 000eeadc 0013422d 001aafdb 000154e5 00012a9c 0019da58 00168443 000c8ff0 000ad2b5 0015fbba 000dad9a 000e1a3b 000168ad 00175e11 001ce511 000b7428 0002f90b 0017584e 001ce36c 001be44f 00189429 0001c4d5 001347e9 00000364 000002fc 00074080
FLEX: 2024-12-08 21:19:07 3200/4/A 04.064 [4294947930] UNK 00074080 00010ecb 00017eb4 000b534f 000c83e1 00194902 00086a68 001ffffc 001ca342
FLEX|2024-12-08 21:19:07|3200/4/C/A|04.064|002064199|ALN|
FLEX|2024-12-08 21:19:07|3200/4/C/A|04.064|4294954932|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [81]3f
FLEX: 2024-12-08 21:19:07 3200/4/A 04.064 [002064197] NUM 0208
FLEX|2024-12-08 21:19:07|3200/4/C/C|04.064|4294959999|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [68]EFr
FLEX: 2024-12-08 21:19:07 3200/4/C 04.064 [002064200] NUM 494
FLEX|2024-12-08 21:19:07|3200/4/C/C|04.064|4294954950|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [42]
FLEX: 2024-12-08 21:19:07 3200/4/C 04.064 [002064197] NUM [82
FLEX|2024-12-08 21:19:24|3200/4/C/A|04.065|4294942993|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [63]f
FLEX: 2024-12-08 21:19:24 3200/4/A 04.065 [002064255] NUM 0-82
FLEX|2024-12-08 21:20:10|3200/4/C/A|04.067|4294934942|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [74]n9q
FLEX: 2024-12-08 21:20:10 3200/4/A 04.067 [002064200] NUM 615 
FLEX|2024-12-08 21:20:10|3200/4/F/A|04.067|4294944338|ALN|y880kbOfI5gfYoG5q6BAA<Fr
FLEX|2024-12-08 21:20:10|3200/4/K/A|04.067|002064205|ALN|
FLEX|2024-12-08 21:20:10|3200/4/C/A|04.067|4294954940|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [69]
FLEX: 2024-12-08 21:20:10 3200/4/A 04.067 [002064197] NUM 0-82
FLEX|2024-12-08 21:20:10|3200/4/C/C|04.067|4294960016|ALN|om: meditechalerts@ehr.org Subject: Housekeeping Request - Dirty: 435 02  [34]
FLEX: 2024-12-08 21:20:10 3200/4/C 04.067 [002064200] NUM 1-82
FLEX|2024-12-08 21:20:35|3200/4/F/A|04.068|4294957717|ALN|Io5VcvE4axx96Gao5S27oVGTMCtWrYop7acr6bHwpuSkBVYy6mH1/hoGv90tkB56M31MDsDRYpr3UrZHtIzAagGC7wRUpYesyLcB7J4cjG4oTSN+8XtVaRJCcC//W/VLI9Wyew0wrwNfwU9LoQvqY7WDuToJZ0h1CNtTSCfwMjFgnn3f
FLEX: 2024-12-08 21:20:35 3200/4/A 04.068 [002064208] UNK
FLEX|2024-12-08 21:20:35|3200/4/C/B|04.068|4294949507|ALN|gjHWy4P7KiHaoSjJNDh5FFBLcrZUE6aH1ob2BjUDr9Bwzv9Hj3EFGTCC4e6ReNxVpUqrGjSTIuc2lkPv6wdf0KYcpIgY4JKE2nONeRhokfPl1kWqgR7tlhY0o2uXqkfsve1jyLQuiYCc/HXDuCMka0wrqgUEzdY354tXBSEpfuA8ZI
FLEX|2024-12-08 21:20:35|3200/4/K/C|05.068|4294958624|ALN|O2lH3hZo1Msa3QGxn9A8mh4xIxrhv1CZB2dnl6bZR1PTZLnqn1jhJyFezB+1C9+uWyHk7J4b2PI3FiSFkY8L/fBFEes27TOymNS79T1uqMTFrvWeRp/QL1HqWhYc5WaMBvCSdmGrj7kaY7B4oEu7BvzAkTiFqeV8+fxqyIEiYduRt3fL
FLEX: 2024-12-08 21:20:35 3200/4/C 05.068 [002064209] UNK
FLEX|2024-12-08 21:20:35|3200/4/F/D|05.068|4294948699|ALN|5fIIzRaReOOgQdqS2sCeu/vzt0ip8gQo+gf3oMhdcDDF/Y5H5f0/IlFaQ5G11QUhMemAYPtyUxe/Lahtxbw/QS1DB9SKk5Q971ZQvOsadK3mSbSMmDKCoEVH1MzbXeMRbUx2hP9YIShPEf7TuqlLpvADxWvcwcOaN6Goly2sEO95kP
FLEX: 2024-12-08 21:20:35 3200/4/D 05.068 [002064214] NUM 78-6
FLEX|2024-12-08 21:20:46|3200/4/C/A|04.069|4294957717|ALN|JAL9h6uvKnu86BtKZ3XpCIfW2uncjuItbKwgHTOVtpz33LXWm+LjOHgApI4P7C/aEM1MykbsDFCPgN60nL0jBdakgBS/RSWiilKgRjoplyJUWF46JrCFTm55brpVQCvTf2CELdy71L6q1aw33qQjUSPJigwqJB1yXWDAAmg3
FLEX|2024-12-08 21:20:46|3200/4/F/A|04.069|002064208|ALN|
FLEX: 2024-12-08 21:20:46 3200/4/A 04.069 [002064209] NUM 358
"""


@pytest.fixture
def sample_data():
    return '2024-09-23 12:38:00: POCSAG512: Address:  162202  Function: 0  Alpha:   @@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM<NUL>'


@pytest.fixture
def sample_json_data():
    return '{"demod_name":"POCSAG1200","address":1920312,"function":3,"alpha":"Time Critical Incident - Clear ASAP - or advise Comms of Time to Clear (Via Radio)"}'


@pytest.fixture(params=FLEX_LINES.splitlines())
def flex_lines(request):
    yield request.param


def test_POCSAG_parse_line(sample_data):
    parse_line = ParseLine()
    result, json_detected = parse_line.parse(sample_data)
    assert result.address == '1622020'
    assert result.timestamp == moment.date(2024, 9, 23, 12, 38, 00)
    assert (
        result.trim_message
        == '@@E24092310740 SIG2 BNSD7879 REQ1220 DSP1237 LOC 122 DAY ST BAIRNSDALE /VICTORIA ST :@BAIRNSDALE PUBLIC HOSPITAL SVVB SE 8501 E11 CC: IHTAIR2 - AIR AMBULANCE TRANSFER ACUITY: MEDIUM'
    )
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
    assert result.trim_message == None


@pytest.mark.skip(reason='Untestable for now')
def test_FLEX_parse_line(flex_lines):
    """Test for GitHub issue https://github.com/lingfish/mmng-ui/issues/3"""

    parse_line = ParseLine()
    # result, json_detected = parse_line.parse('FLEX|2024-12-08 21:18:46|3200/4/C/C|04.063|4294942723|ALN|nsult LOPEZ PEREZ 31373343 h/o spinal compression fx\'s MRI 12/7 subacute compression deformities, no evidence of cord compression. Pt neurologically intact. any acute surgical intervention? - Donald Thommes 6314176868 [68]3fL')
    result, json_detected = parse_line.parse(flex_lines)
    # assert result.address == '4294942723'
    # assert result.timestamp == moment.date(2024, 12, 8, 21, 18, 46)
    print(result)
    assert (
            result.trim_message
            == 'nsult LOPEZ PEREZ 31373343 h/o spinal compression fx\'s MRI 12/7 subacute compression deformities, no evidence of cord compression. Pt neurologically intact. any acute surgical intervention? - Donald Thommes 6314176868 [68]3fL'
    )
    assert json_detected is False

