from ticked.utils.time_utils import (
    convert_to_12hour,
    convert_to_24hour,
    generate_time_options,
)


def test_convert_to_12hour():
    assert convert_to_12hour("00:00") == "12:00 AM"
    assert convert_to_12hour("01:00") == "1:00 AM"
    assert convert_to_12hour("09:30") == "9:30 AM"
    assert convert_to_12hour("11:59") == "11:59 AM"
    assert convert_to_12hour("12:00") == "12:00 PM"
    assert convert_to_12hour("13:00") == "1:00 PM"
    assert convert_to_12hour("15:45") == "3:45 PM"
    assert convert_to_12hour("23:59") == "11:59 PM"

    assert convert_to_12hour("05:05") == "5:05 AM"
    assert convert_to_12hour("12:01") == "12:01 PM"
    assert convert_to_12hour("23:00") == "11:00 PM"

    assert convert_to_12hour("00:01") == "12:01 AM"
    assert convert_to_12hour("12:59") == "12:59 PM"


def test_convert_to_12hour_error_handling():
    assert convert_to_12hour("25:00") == "13:00 PM"
    assert convert_to_12hour("12:60") == "12:60 PM"
    assert convert_to_12hour("") == ""
    assert convert_to_12hour("not a time") == "not a time"
    assert convert_to_12hour("12-30") == "12-30"
    assert convert_to_12hour(None) is None


def test_convert_to_24hour():
    assert convert_to_24hour("12:00 AM") == "00:00"
    assert convert_to_24hour("1:00 AM") == "01:00"
    assert convert_to_24hour("9:30 AM") == "09:30"
    assert convert_to_24hour("11:59 AM") == "11:59"
    assert convert_to_24hour("12:00 PM") == "12:00"
    assert convert_to_24hour("1:00 PM") == "13:00"
    assert convert_to_24hour("3:45 PM") == "15:45"
    assert convert_to_24hour("11:59 PM") == "23:59"

    assert convert_to_24hour("5:05 AM") == "05:05"
    assert convert_to_24hour("12:01 PM") == "12:01"
    assert convert_to_24hour("11:00 PM") == "23:00"

    assert convert_to_24hour("12:01 AM") == "00:01"
    assert convert_to_24hour("12:59 PM") == "12:59"


def test_convert_to_24hour_error_handling():
    assert convert_to_24hour("13:00 PM") == "13:00"
    assert convert_to_24hour("12:60 AM") == "00:60"
    assert convert_to_24hour("") == ""
    assert convert_to_24hour("not a time") == "not a time"
    assert convert_to_24hour("12-30 PM") == "12-30 PM"
    assert convert_to_24hour(None) is None


def test_generate_time_options():
    options = generate_time_options()

    assert len(options) == 49

    assert options[0] == ("12:00 AM", "00:00")
    assert options[-1] == ("11:59 PM", "23:59")

    assert ("6:00 AM", "06:00") in options
    assert ("12:00 PM", "12:00") in options
    assert ("5:30 PM", "17:30") in options
    assert ("9:00 PM", "21:00") in options

    assert ("2:00 PM", "14:00") in options
    assert ("2:30 PM", "14:30") in options
    assert ("3:00 PM", "15:00") in options

    assert options.count(("12:00 AM", "00:00")) == 1

    for display, value in options:
        assert convert_to_12hour(value) == display

        assert len(value) == 5
        assert value[2] == ":"
        assert 0 <= int(value[:2]) <= 23
        assert 0 <= int(value[3:]) <= 59

        assert display.endswith("AM") or display.endswith("PM")
