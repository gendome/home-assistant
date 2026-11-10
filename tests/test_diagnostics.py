"""Verify that diagnostics exclude account identifiers and API error details."""

from types import SimpleNamespace

from custom_components.gendome.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redact_account_and_error_details():
    endpoint = "https://api.example.com/devices/device-id"
    coordinator = SimpleNamespace(
        data=SimpleNamespace(
            devices={},
            profile=SimpleNamespace(
                user_id="42", username="abc", email=None, region="us", scopes=()
            ),
        ),
        last_update_success=False,
    )
    api = SimpleNamespace(
        last_error={
            "code": "ERROR",
            "message": f"Failed at {endpoint}",
            "endpoint": endpoint,
        },
    )
    entry = SimpleNamespace(
        data={"userId": "42"},
        runtime_data=SimpleNamespace(api=api, coordinator=coordinator),
    )

    diagnostics = await async_get_config_entry_diagnostics(None, entry)

    assert diagnostics["profile"]["username"] == "**REDACTED**"
    assert diagnostics["profile"]["user_id"] == "**REDACTED**"
    assert diagnostics["config_entry"]["userId"] == "**REDACTED**"
    assert diagnostics["last_error"] == {"code": "ERROR"}
