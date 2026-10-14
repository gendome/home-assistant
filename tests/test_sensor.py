"""Tests for localized remaining-time sensor formatting."""

from custom_components.gendome.duration import (
    format_duration_minutes,
    remaining_time_name,
)
from custom_components.gendome.sensor import SENSORS


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


def test_remaining_time_name_follows_charging_state() -> None:
    assert remaining_time_name(True, "zh-Hans") == "充电剩余时长"
    assert remaining_time_name(False, "zh-Hans") == "放电剩余时长"
    assert remaining_time_name(None, "en") == "Discharge remaining time"


def test_only_one_remaining_time_sensor_is_created() -> None:
    keys = {description.key for description in SENSORS}

    assert "remaining_time" in keys
    assert "charge_remaining_time" not in keys
    assert "discharge_remaining_time" not in keys
