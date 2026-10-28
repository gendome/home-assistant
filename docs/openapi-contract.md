# Gendome OpenAPI contract

All requests use HTTPS and `Authorization: Bearer <access_token>`. The Java
service returns an `ApiResult` envelope; the Python client unwraps `data` only
when `success` is true.

| Method | Path | Use |
| --- | --- | --- |
| GET | `/openapi/home-assistant/profile` | Account ID, region, scopes |
| GET | `/openapi/home-assistant/devices` | Account device discovery |
| GET | `/openapi/home-assistant/devices/states` | Batched semantic states |
| GET | `/openapi/home-assistant/devices/{deviceId}/state` | Single-device compensation/debugging |
| POST | `/openapi/home-assistant/devices/{deviceId}/commands` | Submit allow-listed command |
| GET | `/openapi/home-assistant/commands/{commandId}` | Poll command result |
| GET | `/openapi/home-assistant/devices/{deviceId}/schedule/charging` | Read existing plan |
| PUT | `/openapi/home-assistant/devices/{deviceId}/schedule/charging/enabled` | Enable/disable existing plan |

## State keys consumed by the integration

`batterySoc`, `remainingTime`, `chargeRemainingTime`, `dischargeRemainingTime`,
`inputTotalPower`,
`acInputPower`, `solarInputPower`, `windInputPower`, `outputTotalPower`,
`acOutputPower`, `dcOutputPower`, `acChargePowerSetting`, `online`, `charging`,
`discharging`, `acInputEnabled`, `acOutputEnabled`, `dcOutputEnabled`,
`buzzerEnabled`, `batteryProtectionLowerSoc`, `batteryProtectionUpperSoc`, and
`firmwareVersion`.

Remaining-time values use minutes. `remainingTime` is selected dynamically:
`chargeRemainingTime` when `charging` is true, otherwise
`dischargeRemainingTime` when `charging` is false or unavailable.
The API derives `charging` only from `inputTotalPower`: Gendome devices use
data point 165 and BeiYiTong GO1000/GO2000 devices use data point 131. Values
greater than zero are charging, while zero or negative values are not.
Charge-mode/status data points (including Gendome point 24 and BeiYiTong point
101) must not be interpreted as a boolean charging state.
If the device does not report `discharging`, the API derives it as the inverse
of charging and total power. When input and output total power are both zero,
the API reports standby (`charging=false`, `discharging=false`) while
`remainingTime` continues to use the discharge-side value.

## Command request

```json
{
  "commandType": "SET_AC_OUTPUT_ENABLED",
  "idempotencyKey": "f76d4f20d430467a923e82cd16b42f4d",
  "payload": {"enabled": true}
}
```

Terminal statuses are `SUCCESS`, `FAILED`, `TIMEOUT`, and `REJECTED`.
`ACCEPTED` and `SENT` are intermediate statuses. Commands that remain
intermediate for 30 seconds fail in Home Assistant instead of reporting an
optimistic success.

## OAuth endpoints

- Authorization: `/oauth/authorize`
- Token and refresh: `/oauth/token`
- Backend/App revocation: `/oauth/revokeToken`

The HACS integration uses the public client `gendome_home_assistant` with no
client secret. Authorization-code requests require S256 PKCE. The authorize
request carries `code_challenge` and `code_challenge_method=S256`; the token
request carries the matching `code_verifier`, `client_id`, code, and redirect
URI. Refresh requests also identify the public client without HTTP Basic or a
client secret.

When validating a release, verify access-token expiry, refresh-token expiry and rotation,
password-change behavior, PKCE rejection, revocation propagation, and the exact
redirect URI.
