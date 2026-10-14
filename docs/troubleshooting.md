# Troubleshooting

## Authorization expired or revoked (401)

Home Assistant starts a reauthentication flow. Open the Gendome integration,
choose **Reconfigure**, and sign in again. If reauthentication loops, confirm
the OAuth redirect URI and refresh-token policy on the backend.

## Missing permission (403)

Authorize the scope required by the entity:

- device state: `device:read`, `statistics:read`;
- AC/DC/buzzer switches: `device:control:switch`;
- power and battery settings: `device:control:setting`;
- schedule state/control: `scheduled_charging:read` and
  `scheduled_charging:write`.

## Rate limited (429)

The coordinator honors the backend `Retry-After` response. Avoid automations
that repeatedly write the same switch or number. The backend should also apply
token, device-command cooldown, and HA-instance limits.

## Device is unavailable

Check the Online binary sensor and the Gendome App. Other entities become
unavailable when the backend reports the device offline. Confirm that the
device belongs to the authorized App user and supports the requested state key.

## Command timeout or failure

The integration polls the returned `commandId` for up to 30 seconds. Export
diagnostics and correlate its masked identifier and error code with
`iot_home_assistant_command`. Check cloud-to-device delivery, device online
state, and whether the expected property was reported.

## State differs from the App

Press **Refresh state**, wait for the command result, then compare the batched
`/devices/states` response with the App. Confirm data-point mappings and units,
especially charge/discharge remaining time, charging/discharging, and firmware
fields.
