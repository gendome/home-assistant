"""Validate GO number controls before sending a command."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.gendome.const import PRODUCT_KEY_GO_1000, PRODUCT_KEY_GO_2000
from custom_components.gendome.number import NUMBERS, GendomeNumber


def make_entity(key, product_key=PRODUCT_KEY_GO_1000):
    states = {
        "acChargePowerSetting": 102,
        "batteryProtectionLowerSoc": 10,
        "batteryProtectionUpperSoc": 98,
    }
    state = SimpleNamespace(
        states=states,
        value=states.get,
        device=SimpleNamespace(
            product_key=product_key,
            mac="123456",
            name="GO",
            manufacturer="Gendome",
            model="GO",
            software_version=None,
        ),
    )
    coordinator = SimpleNamespace(
        data=SimpleNamespace(devices={"device": state}),
        api=SimpleNamespace(async_send_and_wait=AsyncMock()),
        async_request_refresh=AsyncMock(),
    )
    description = next(item for item in NUMBERS if item.key == key)
    return GendomeNumber(coordinator, "device", description)


@pytest.mark.parametrize("product_key", [PRODUCT_KEY_GO_1000, PRODUCT_KEY_GO_2000])
async def test_go_power_accepts_integer_watts_and_refreshes(product_key):
    entity = make_entity("ac_charge_power_limit", product_key)
    assert entity.native_step == 1
    await entity.async_set_native_value(102)
    entity.coordinator.api.async_send_and_wait.assert_awaited_once_with(
        "device", "SET_AC_CHARGE_POWER", {"power": 102}
    )
    entity.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.parametrize("product_key", [PRODUCT_KEY_GO_1000, PRODUCT_KEY_GO_2000])
@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("battery_protection_upper_soc", 97, {"lowerSoc": 10, "upperSoc": 97}),
        ("battery_protection_lower_soc", 13, {"lowerSoc": 13, "upperSoc": 98}),
    ],
)
async def test_go_soc_accepts_one_percent_steps(product_key, key, value, expected):
    entity = make_entity(key, product_key)
    assert entity.native_step == 1
    await entity.async_set_native_value(value)
    entity.coordinator.api.async_send_and_wait.assert_awaited_once_with(
        "device", "SET_BATTERY_PROTECTION_RANGE", expected
    )


async def test_go_soc_rejects_out_of_range_value_before_sending():
    entity = make_entity("battery_protection_upper_soc")
    assert entity.native_value == 98
    with pytest.raises(HomeAssistantError) as error:
        await entity.async_set_native_value(49)
    assert error.value.translation_key == "number_out_of_range"
    entity.coordinator.api.async_send_and_wait.assert_not_awaited()


async def test_go_power_rejects_fractional_watts_without_truncating():
    entity = make_entity("ac_charge_power_limit")
    with pytest.raises(HomeAssistantError) as error:
        await entity.async_set_native_value(102.5)
    assert error.value.translation_key == "invalid_whole_number"
    entity.coordinator.api.async_send_and_wait.assert_not_awaited()
