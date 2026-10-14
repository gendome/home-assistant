"""Tests for localized remaining-time sensor formatting."""

from custom_components.gendome.duration import format_duration_minutes


def test_formats_simplified_chinese_duration() -> None:
    assert format_duration_minutes(1230, "zh-Hans") == "20小时30分钟"


def test_formats_english_and_uses_it_as_fallback() -> None:
    assert format_duration_minutes(1230, "en") == "20 hours 30 minutes"
    assert format_duration_minutes(61, "de") == "1 hour 1 minute"
    assert format_duration_minutes(1230, "zh-Hant") == "20 hours 30 minutes"


def test_formats_zero_and_rejects_invalid_duration() -> None:
    assert format_duration_minutes(0, "zh-Hans") == "0分钟"
    assert format_duration_minutes(None, "en") is None
    assert format_duration_minutes(-1, "en") is None
