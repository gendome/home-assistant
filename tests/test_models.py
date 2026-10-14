"""Tests for API response models."""

from custom_components.gendome.models import (
    GendomeDevice,
    GendomeDeviceState,
    GendomeProfile,
)


def test_profile_converts_java_long_to_stable_string() -> None:
    profile = GendomeProfile.from_dict(
        {
            "userId": "9007199254740993",
            "username": "test-user",
            "region": "eu",
            "scopes": ["device:read"],
        }
    )

    assert profile.user_id == "9007199254740993"
    assert profile.region == "EU"
    assert profile.scopes == ("device:read",)


def test_state_merges_discovery_metadata_and_boolean_values() -> None:
    device = GendomeDevice.from_dict(
        {
            "deviceId": "42",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Garage battery",
            "model": "Home 3000",
            "wifiVersion": "1.2.3",
            "online": True,
        }
    )
    state = GendomeDeviceState.from_dict(
        {
            "deviceId": "42",
            "mac": "AA:BB:CC:DD:EE:FF",
            "online": 0,
            "states": {"acOutputEnabled": "1", "batterySoc": 82},
        },
        device,
    )

    assert state.device.name == "Garage battery"
    assert state.device.model == "Home 3000"
    assert state.device.online is False
    assert state.boolean("acOutputEnabled") is True
    assert state.value("batterySoc") == 82


def test_software_version_combines_wifi_and_mcu() -> None:
    device = GendomeDevice.from_dict(
        {
            "deviceId": "1",
            "mac": "001122334455",
            "wifiVersion": "2.0",
            "mcuVersion": "3.0",
        }
    )

    assert device.software_version == "Wi-Fi 2.0 / MCU 3.0"


def test_semantic_charging_is_not_overridden_by_raw_charge_mode() -> None:
    state = GendomeDeviceState.from_dict(
        {
            "deviceId": "1",
            "mac": "001122334455",
            "states": {"charging": True, "inputTotalPower": 488},
            "rawProperties": {"chargeStatus": 0, "24": 0},
        }
    )

    assert state.boolean("charging") is True
