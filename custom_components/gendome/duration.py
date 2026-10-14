"""设备上报时长值的本地化格式化。"""

from __future__ import annotations

import math
from typing import Any


def format_duration_minutes(value: Any, language: str | None) -> str | None:
    """使用 Home Assistant 实例语言格式化设备分钟数。"""
    total_minutes = duration_minutes(value)
    if total_minutes is None:
        return None

    hours, minutes = divmod(total_minutes, 60)
    normalized_language = (language or "en").lower()
    if normalized_language.startswith("zh-hans") or normalized_language in {
        "zh",
        "zh-cn",
        "zh-sg",
    }:
        return _format_chinese_duration(hours, minutes, "小时", "分钟")
    return _format_english_duration(hours, minutes)


def duration_minutes(value: Any) -> int | None:
    """返回安全、取整且非负的分钟数。"""
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(minutes) or minutes < 0:
        return None
    return int(round(minutes))


def _format_chinese_duration(
    hours: int,
    minutes: int,
    hour_unit: str,
    minute_unit: str,
) -> str:
    if hours and minutes:
        return f"{hours}{hour_unit}{minutes}{minute_unit}"
    if hours:
        return f"{hours}{hour_unit}"
    return f"{minutes}{minute_unit}"


def _format_english_duration(hours: int, minutes: int) -> str:
    parts = []
    if hours:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes or not parts:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    return " ".join(parts)
