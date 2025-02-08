import pytest
from ticked.utils.time_utils import (
    convert_to_12hour,
    convert_to_24hour,
    generate_time_options,
)


def test_convert_to_12hour():
    assert convert_to_12hour("00:00") == "12:00 AM"
    assert convert_to_12hour("12:00") == "12:00 PM"
    assert convert_to_12hour("13:00") == "1:00 PM"
    assert convert_to_12hour("23:59") == "11:59 PM"
    assert convert_to_12hour("09:30") == "9:30 AM"
    assert convert_to_12hour("15:45") == "3:45 PM"


def test_convert_to_24hour():
    assert convert_to_24hour("12:00 AM") == "00:00"
    assert convert_to_24hour("12:00 PM") == "12:00"
    assert convert_to_24hour("1:00 PM") == "13:00"
    assert convert_to_24hour("11:59 PM") == "23:59"
    assert convert_to_24hour("9:30 AM") == "09:30"
    assert convert_to_24hour("3:45 PM") == "15:45"


def test_generate_time_options():
    options = generate_time_options()
    assert len(options) > 0
    assert ("12:00 AM", "00:00") in options
    assert ("11:59 PM", "23:59") in options

    # Test some regular time slots
    assert ("9:00 AM", "09:00") in options
    assert ("5:30 PM", "17:30") in options

    # Test that times are properly paired
    for display, value in options:
        assert convert_to_12hour(value) == display
