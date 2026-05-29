import json
from pathlib import Path

import pytest

from mmng_ui.capcode_db import CapcodeDB


@pytest.fixture
def sample_json_vicpagers():
    return {
        "data": [
            {"address": "1764858", "alias": "AV Bright", "agency": "AV", "color": None},
            {"address": "0163218", "alias": "Fire Dispatch", "agency": "FIRE", "color": "red"},
            {"address": "1234567", "alias": "Police HQ", "agency": "POLICE", "color": "blue"}
        ]
    }


@pytest.fixture
def sample_json_flat():
    return [
        {"address": "1764858", "alias": "AV Bright", "agency": "AV", "color": None},
        {"address": "0163218", "alias": "Fire Dispatch", "agency": "FIRE", "color": "red"},
        {"address": "1234567", "alias": "Police HQ", "agency": "POLICE", "color": "blue"}
    ]


@pytest.fixture
def sample_csv():
    return (
        "address,alias,agency,color\n"
        "1764858,AV Bright,AV,\n"
        "0163218,Fire Dispatch,FIRE,red\n"
        "1234567,Police HQ,POLICE,blue\n"
    )


def test_load_json_vicpagers_format(tmp_path, sample_json_vicpagers):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(sample_json_vicpagers))

    # Act
    db = CapcodeDB.load(file_path)

    # Assert
    assert len(db) == 3
    assert isinstance(db, CapcodeDB)


def test_load_json_flat_format(tmp_path, sample_json_flat):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(sample_json_flat))

    # Act
    db = CapcodeDB.load(file_path)

    # Assert
    assert len(db) == 3
    assert isinstance(db, CapcodeDB)


def test_load_csv_format(tmp_path, sample_csv):
    # Arrange
    file_path = tmp_path / "test.csv"
    file_path.write_text(sample_csv)

    # Act
    db = CapcodeDB.load(file_path)

    # Assert
    assert len(db) == 3
    assert isinstance(db, CapcodeDB)


def test_lookup_returns_correct_alias(tmp_path, sample_json_vicpagers):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(sample_json_vicpagers))
    db = CapcodeDB.load(file_path)

    # Act
    entry = db.lookup("1764858")

    # Assert
    assert entry is not None
    assert entry.alias == "AV Bright"
    assert entry.address == "1764858"
    assert entry.agency == "AV"
    assert entry.color is None


def test_lookup_with_leading_zero_variant(tmp_path, sample_json_vicpagers):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(sample_json_vicpagers))
    db = CapcodeDB.load(file_path)

    # Act & Assert
    # Lookup with leading zero should match the same entry
    entry1 = db.lookup("1764858")
    entry2 = db.lookup("01764858")  # Adding a leading zero
    assert entry1 is not None
    assert entry2 is not None
    assert entry1.alias == entry2.alias == "AV Bright"

    # Another example from the fixture: "0163218" should match "163218" (if we had that)
    # But in our fixture we have "0163218", so we test that looking up without leading zero works
    entry3 = db.lookup("163218")  # Removing the leading zero
    assert entry3 is not None
    assert entry3.alias == "Fire Dispatch"


def test_lookup_unknown_address_returns_none(tmp_path, sample_json_vicpagers):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(sample_json_vicpagers))
    db = CapcodeDB.load(file_path)

    # Act
    entry = db.lookup("0000000")

    # Assert
    assert entry is None


def test_file_not_found_raises_file_not_found_error():
    # Arrange
    non_existent_path = Path("/non/existent/file.json")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        CapcodeDB.load(non_existent_path)


def test_unsupported_extension_raises_value_error(tmp_path):
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("some content")

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported file extension"):
        CapcodeDB.load(file_path)


def test_empty_entries_list_in_json_works(tmp_path):
    # Arrange
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps({"data": []}))

    # Act
    db = CapcodeDB.load(file_path)

    # Assert
    assert len(db) == 0


def test_entry_with_icon(tmp_path):
    """Test icon field is captured from JSON data."""
    json_data = [
        {"address": "5555555", "alias": "Fire Station", "agency": "FIRE", "icon": "fire"},
        {"address": "6666666", "alias": "Ambulance", "agency": "AMB", "icon": "ambulance"},
        {"address": "7777777", "alias": "No Icon", "agency": "TEST"},
    ]
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(json_data))
    db = CapcodeDB.load(file_path)
    entry1 = db.lookup("5555555")
    assert entry1 is not None
    assert entry1.icon == "fire"
    entry2 = db.lookup("6666666")
    assert entry2 is not None
    assert entry2.icon == "ambulance"
    entry3 = db.lookup("7777777")
    assert entry3 is not None
    assert entry3.icon is None


def test_entries_with_missing_optional_fields(tmp_path):
    # Arrange
    json_data = [
        {"address": "1111111", "alias": "Test Entry"},  # missing agency and color
        {"address": "2222222", "alias": "Another", "agency": "TEST"}  # missing color
    ]
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(json_data))

    # Act
    db = CapcodeDB.load(file_path)

    # Assert
    assert len(db) == 2
    entry1 = db.lookup("1111111")
    entry2 = db.lookup("2222222")
    assert entry1 is not None
    assert entry1.alias == "Test Entry"
    assert entry1.agency is None
    assert entry1.color is None
    assert entry2 is not None
    assert entry2.alias == "Another"
    assert entry2.agency == "TEST"
    assert entry2.color is None
